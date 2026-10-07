import json

from sqlalchemy.ext.asyncio import AsyncSession

from lad.core.sse import format_sse_event
from lad.models.db import Messages
from lad.schemas.chat import ChatMessageResponse


async def create_message(
    db: AsyncSession,
    chat_id: int,
    role: str,
    content: str,
    *,
    tool_call_id: str | None = None,
    tool_name: str | None = None,
    tool_arguments: str | None = None,
    attached_files: list[str] | None = None,
) -> Messages:
    message = Messages(
        chat_id=chat_id,
        role=role,
        content=content,
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        tool_arguments=tool_arguments,
        attached_files=json.dumps(attached_files) if attached_files else None,
    )

    db.add(message)
    await db.flush()

    return message


async def create_tool_call_message(
    db: AsyncSession, chat_id: int, call_id: str, tool_name: str, arguments: dict
) -> Messages:
    return await create_message(
        db=db,
        chat_id=chat_id,
        role="tool_call",
        content="",
        tool_call_id=call_id,
        tool_name=tool_name,
        tool_arguments=json.dumps(arguments),
    )


async def create_tool_result_message(
    db: AsyncSession, chat_id: int, call_id: str, tool_name: str, content: str
) -> Messages:
    return await create_message(
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
