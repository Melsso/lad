import json

from sqlalchemy.orm import Session

from lad.core.sse import format_sse_event
from lad.models.db import Messages
from lad.schemas.chat import ChatMessageResponse


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
