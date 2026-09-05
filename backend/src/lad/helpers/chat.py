import json
import logging
from collections.abc import Iterator

from sqlalchemy.orm import Session

from lad.core.db import get_db_session
from lad.core.sse import format_sse_event
from lad.helpers.llm import generate_response_stream, generate_summary
from lad.models.db import Chat, ConversationSummary, Messages
from lad.schemas.chat import ChatMessageResponse, ChatResponse
from lad.schemas.config import conf

logger = logging.getLogger("Lad")


def get_chats(db: Session) -> list[ChatResponse]:
    chats = db.query(Chat).order_by(Chat.created_at).all()

    return [ChatResponse.model_validate(chat) for chat in chats]


def get_chat_messages(db: Session, chat_id: int) -> list[ChatMessageResponse]:
    chat_msgs = (
        db.query(Messages)
        .filter(Messages.chat_id == chat_id)
        .order_by(Messages.created_at)
        .all()
    )

    return [ChatMessageResponse.model_validate(msg) for msg in chat_msgs]


def get_chat(db: Session, chat_id: int) -> Chat | None:
    return db.query(Chat).filter(Chat.id == chat_id).first()


def create_chat(db: Session, title: str) -> Chat:
    chat = Chat(title=title)

    db.add(chat)
    db.flush()

    return chat


def generate_temporary_chat_title(msg: str) -> str:
    title = " ".join(msg.strip().split())

    if not title:
        return "New Chat"

    max_length = 50

    if len(title) <= max_length:
        return title

    return title[: max_length - 3].rstrip() + "..."


def update_chat_title(db: Session, chat_id: int, title: str) -> Chat | None:
    chat = get_chat(db, chat_id)

    if chat is None:
        return None

    chat.title = title.strip()
    db.flush()

    return chat


def delete_chat(db: Session, chat_id: int) -> bool:
    chat = get_chat(db, chat_id)

    if chat is None:
        return False

    db.delete(chat)
    db.flush()

    return True


def get_chat_summary(db: Session, chat_id: int) -> ConversationSummary | None:
    return (
        db.query(ConversationSummary)
        .filter(ConversationSummary.chat_id == chat_id)
        .first()
    )


def get_messages_after_summary(
    db: Session, chat_id: int, last_message_id: int | None
) -> list[Messages]:
    query = db.query(Messages).filter(Messages.chat_id == chat_id)

    if last_message_id is not None:
        query = query.filter(Messages.id > last_message_id)

    return query.order_by(Messages.created_at).all()


def create_message(
    db: Session,
    chat_id: int,
    role: str,
    content: str,
    *,
    tool_call_id: str | None = None,
    tool_name: str | None = None,
    tool_arguments: str | None = None,
) -> Messages:
    message = Messages(
        chat_id=chat_id,
        role=role,
        content=content,
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        tool_arguments=tool_arguments,
    )

    db.add(message)
    db.flush()

    return message


def create_tool_call_message(
    db: Session, chat_id: int, call_id: str, tool_name: str, arguments: dict
) -> Messages:
    return create_message(
        db=db,
        chat_id=chat_id,
        role="tool_call",
        content="",
        tool_call_id=call_id,
        tool_name=tool_name,
        tool_arguments=json.dumps(arguments),
    )


def create_tool_result_message(
    db: Session, chat_id: int, call_id: str, tool_name: str, content: str
) -> Messages:
    return create_message(
        db=db,
        chat_id=chat_id,
        role="tool_result",
        content=content,
        tool_call_id=call_id,
        tool_name=tool_name,
    )


def sse_event_for_message(event: str, message: Messages) -> str:
    payload = ChatMessageResponse.model_validate(message).model_dump(mode="json")

    return format_sse_event(event, payload)


def save_chat_summary(
    db: Session, chat_id: int, content: str, last_message_id: int
) -> ConversationSummary:
    summary = get_chat_summary(db, chat_id)

    if summary is None:
        summary = ConversationSummary(
            chat_id=chat_id,
            content=content,
            last_message_id=last_message_id,
        )
        db.add(summary)
    else:
        summary.content = content
        summary.last_message_id = last_message_id

    db.flush()

    return summary


def _stream_and_persist_reply(db: Session, chat_id: int) -> Iterator[str]:
    summary = get_chat_summary(db=db, chat_id=chat_id)
    active_messages = get_messages_after_summary(
        db=db,
        chat_id=chat_id,
        last_message_id=summary.last_message_id if summary else None,
    )

    if len(active_messages) >= conf.SUMMARY_THRESHOLD:
        messages_to_summarize = active_messages[: -conf.RECENT_MESSAGES_TO_KEEP]
        if messages_to_summarize:
            new_summary = generate_summary(
                existing_summary=(summary.content if summary else None),
                messages=messages_to_summarize,
            )

            summary = save_chat_summary(
                db=db,
                chat_id=chat_id,
                content=new_summary,
                last_message_id=messages_to_summarize[-1].id,
            )
            active_messages = active_messages[-conf.RECENT_MESSAGES_TO_KEEP :]
            db.commit()

    full_response = ""

    for chunk in generate_response_stream(
        summary=summary.content if summary else None,
        messages=active_messages,
    ):
        full_response += chunk
        yield format_sse_event("chunk", {"text": chunk})

    full_response = full_response.strip()

    if not full_response:
        raise RuntimeError("LLM returned an empty response")

    assistant_message = create_message(
        db=db,
        chat_id=chat_id,
        role="assistant",
        content=full_response,
    )
    db.commit()

    yield sse_event_for_message("done", assistant_message)


def stream_chat_msg(chat_id: int, msg: str) -> Iterator[str]:
    with get_db_session() as db:
        try:
            chat = get_chat(db=db, chat_id=chat_id)

            if chat is None:
                yield format_sse_event(
                    "error", {"detail": f"Chat {chat_id} does not exist"}
                )
                return

            create_message(
                db=db,
                chat_id=chat_id,
                role="user",
                content=msg,
            )
            db.commit()

            yield from _stream_and_persist_reply(db, chat_id)

        except Exception as exc:
            db.rollback()

            logger.exception(
                "lad_event",
                extra={
                    "event": "chat_stream",
                    "status": "internal_error",
                    "context": {
                        "location": "stream_chat_msg",
                        "chat_id": chat_id,
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    },
                },
            )

            yield format_sse_event("error", {"detail": "Failed to generate a response"})


def stream_chat_retry(chat_id: int) -> Iterator[str]:
    with get_db_session() as db:
        try:
            chat = get_chat(db=db, chat_id=chat_id)

            if chat is None:
                yield format_sse_event(
                    "error", {"detail": f"Chat {chat_id} does not exist"}
                )
                return

            last_message = (
                db.query(Messages)
                .filter(Messages.chat_id == chat_id)
                .order_by(Messages.created_at.desc())
                .first()
            )

            if last_message is None or last_message.role != "user":
                yield format_sse_event("error", {"detail": "Nothing to retry"})
                return

            yield from _stream_and_persist_reply(db, chat_id)

        except Exception as exc:
            db.rollback()

            logger.exception(
                "lad_event",
                extra={
                    "event": "chat_stream",
                    "status": "internal_error",
                    "context": {
                        "location": "stream_chat_retry",
                        "chat_id": chat_id,
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    },
                },
            )

            yield format_sse_event("error", {"detail": "Failed to generate a response"})
