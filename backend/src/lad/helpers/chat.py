import logging
from collections.abc import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lad.core.db import get_db_session
from lad.core.embeddings import embed_texts
from lad.core.sse import format_sse_event
from lad.helpers.agent import run_agent_turn, run_chat_turn
from lad.helpers.llm import generate_summary
from lad.helpers.messages import create_message
from lad.models.db import Chat, ConversationSummary, Messages
from lad.schemas.chat import ChatMessageResponse, ChatResponse
from lad.schemas.config import conf

logger = logging.getLogger("Lad")


async def get_chats(db: AsyncSession) -> list[ChatResponse]:
    result = await db.execute(select(Chat).order_by(Chat.created_at))

    return [ChatResponse.model_validate(chat) for chat in result.scalars().all()]


async def get_chat_messages(
    db: AsyncSession, chat_id: int
) -> list[ChatMessageResponse]:
    result = await db.execute(
        select(Messages)
        .where(Messages.chat_id == chat_id)
        .order_by(Messages.created_at)
    )

    return [ChatMessageResponse.model_validate(msg) for msg in result.scalars().all()]


async def get_chat(db: AsyncSession, chat_id: int) -> Chat | None:
    return await db.get(Chat, chat_id)


async def create_chat(db: AsyncSession, title: str, mode: str = "chat") -> Chat:
    chat = Chat(title=title, mode=mode)

    db.add(chat)
    await db.flush()

    return chat


def generate_temporary_chat_title(msg: str) -> str:
    title = " ".join(msg.strip().split())

    if not title:
        return "New Chat"

    max_length = 50

    if len(title) <= max_length:
        return title

    return title[: max_length - 3].rstrip() + "..."


async def update_chat_title(db: AsyncSession, chat_id: int, title: str) -> Chat | None:
    chat = await get_chat(db, chat_id)

    if chat is None:
        return None

    chat.title = title.strip()
    await db.flush()

    return chat


async def delete_chat(db: AsyncSession, chat_id: int) -> bool:
    chat = await get_chat(db, chat_id)

    if chat is None:
        return False

    await db.delete(chat)
    await db.flush()

    return True


async def get_chat_summary(
    db: AsyncSession, chat_id: int
) -> ConversationSummary | None:
    result = await db.execute(
        select(ConversationSummary).where(ConversationSummary.chat_id == chat_id)
    )

    return result.scalars().first()


async def get_messages_after_summary(
    db: AsyncSession, chat_id: int, last_message_id: int | None
) -> list[Messages]:
    statement = select(Messages).where(Messages.chat_id == chat_id)

    if last_message_id is not None:
        statement = statement.where(Messages.id > last_message_id)

    result = await db.execute(statement.order_by(Messages.created_at))

    return list(result.scalars().all())


async def save_chat_summary(
    db: AsyncSession, chat_id: int, content: str, last_message_id: int
) -> ConversationSummary:
    summary = await get_chat_summary(db, chat_id)
    embedding = (await embed_texts([content]))[0]

    if summary is None:
        summary = ConversationSummary(
            chat_id=chat_id,
            content=content,
            last_message_id=last_message_id,
            embedding=embedding,
        )
        db.add(summary)
    else:
        summary.content = content
        summary.last_message_id = last_message_id
        summary.embedding = embedding

    await db.flush()

    return summary


def _split_for_summary(
    messages: list[Messages], keep: int
) -> tuple[list[Messages], list[Messages]]:
    """Split into (to_summarize, to_keep) without separating a tool result
    from the tool call that produced it."""
    split = max(len(messages) - keep, 0)

    while 0 < split < len(messages) and messages[split].role == "tool_result":
        split -= 1

    return messages[:split], messages[split:]


async def _stream_and_persist_reply(db: AsyncSession, chat: Chat) -> AsyncIterator[str]:
    chat_id = chat.id

    summary = await get_chat_summary(db=db, chat_id=chat_id)
    active_messages = await get_messages_after_summary(
        db=db,
        chat_id=chat_id,
        last_message_id=summary.last_message_id if summary else None,
    )

    await db.commit()

    if len(active_messages) >= conf.SUMMARY_THRESHOLD:
        messages_to_summarize, recent_messages = _split_for_summary(
            active_messages, conf.RECENT_MESSAGES_TO_KEEP
        )
        if messages_to_summarize:
            new_summary = await generate_summary(
                existing_summary=(summary.content if summary else None),
                messages=messages_to_summarize,
                model=conf.OLLAMA_AGENT_MODEL if chat.mode == "agent" else None,
            )

            summary = await save_chat_summary(
                db=db,
                chat_id=chat_id,
                content=new_summary,
                last_message_id=messages_to_summarize[-1].id,
            )
            active_messages = recent_messages
            await db.commit()

    summary_content = summary.content if summary else None

    run_turn = run_agent_turn if chat.mode == "agent" else run_chat_turn

    async for event in run_turn(db, chat_id, summary_content, active_messages):
        yield event


def _log_stream_error(location: str, chat_id: int, exc: Exception) -> None:
    logger.exception(
        "lad_event",
        extra={
            "event": "chat_stream",
            "status": "internal_error",
            "context": {
                "location": location,
                "chat_id": chat_id,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
        },
    )


async def stream_chat_msg(
    chat_id: int, msg: str, attached_filenames: list[str] | None = None
) -> AsyncIterator[str]:
    async with get_db_session() as db:
        try:
            chat = await get_chat(db=db, chat_id=chat_id)

            if chat is None:
                yield format_sse_event(
                    "error", {"detail": f"Chat {chat_id} does not exist"}
                )
                return

            await create_message(
                db=db,
                chat_id=chat_id,
                role="user",
                content=msg,
                attached_files=attached_filenames,
            )
            await db.commit()

            async for event in _stream_and_persist_reply(db, chat):
                yield event

        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            _log_stream_error("stream_chat_msg", chat_id, exc)

            yield format_sse_event("error", {"detail": "Failed to generate a response"})


async def stream_chat_retry(chat_id: int) -> AsyncIterator[str]:
    async with get_db_session() as db:
        try:
            chat = await get_chat(db=db, chat_id=chat_id)

            if chat is None:
                yield format_sse_event(
                    "error", {"detail": f"Chat {chat_id} does not exist"}
                )
                return

            result = await db.execute(
                select(Messages)
                .where(Messages.chat_id == chat_id)
                .order_by(Messages.created_at.desc())
                .limit(1)
            )
            last_message = result.scalars().first()

            if last_message is None or last_message.role == "assistant":
                yield format_sse_event("error", {"detail": "Nothing to retry"})
                return

            async for event in _stream_and_persist_reply(db, chat):
                yield event

        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            _log_stream_error("stream_chat_retry", chat_id, exc)

            yield format_sse_event("error", {"detail": "Failed to generate a response"})
