from sqlalchemy.orm import Session

from lad.helpers.llm import generate_response, generate_summary
from lad.models.db import Chat, ConversationSummary, Messages
from lad.schemas.chat import ChatMessageResponse, ChatResponse
from lad.schemas.config import conf


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


def create_message(db: Session, chat_id: int, role: str, content: str) -> Messages:
    message = Messages(
        chat_id=chat_id,
        role=role,
        content=content,
    )

    db.add(message)
    db.flush()

    return message


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


def process_chat_msg(db: Session, chat_id: int, msg: str) -> ChatMessageResponse:
    chat = db.query(Chat).filter(Chat.id == chat_id).first()

    if chat is None:
        raise ValueError(f"Chat {chat_id} does not exist")
    try:
        create_message(
            db=db,
            chat_id=chat_id,
            role="user",
            content=msg,
        )
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

        response_text = generate_response(
            summary=summary.content if summary else None,
            messages=active_messages,
        )
        assistant_message = create_message(
            db=db,
            chat_id=chat_id,
            role="assistant",
            content=response_text,
        )
        db.commit()
        return ChatMessageResponse.model_validate(assistant_message)
    except Exception:
        db.rollback()
        raise
