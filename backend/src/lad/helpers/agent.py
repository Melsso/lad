import json
import logging
from collections.abc import Iterator
from typing import Any

from sqlalchemy.orm import Session

from lad.core.llm import (
    build_assistant_tool_call_message,
    build_tool_result_message,
    generate_turn,
)
from lad.core.mcp import mcp_client
from lad.core.sse import format_sse_event
from lad.helpers.llm import AGENT_SYSTEM_PROMPT
from lad.helpers.messages import (
    create_message,
    create_tool_call_message,
    create_tool_result_message,
    sse_event_for_message,
)
from lad.models.db import Messages
from lad.schemas.config import conf
from lad.schemas.llm import LLMTurn, ToolCall

logger = logging.getLogger("Lad")

CHUNK_SIZE = 40


def _chunk_text(text: str) -> Iterator[str]:
    for start in range(0, len(text), CHUNK_SIZE):
        yield text[start : start + CHUNK_SIZE]


def _call_tool(name: str, arguments: dict[str, Any]) -> str:
    try:
        return mcp_client.call_tool(name, arguments)
    except Exception as exc:
        logger.exception(
            "lad_event",
            extra={
                "event": "agent_tool_call",
                "status": "failed",
                "context": {"tool_name": name},
            },
        )
        return f"Error calling {name}: {exc}"


def _message_to_turn(message: Messages) -> dict[str, Any]:
    if message.role == "tool_call":
        arguments = json.loads(message.tool_arguments) if message.tool_arguments else {}
        turn = LLMTurn(
            content="",
            tool_calls=[
                ToolCall(
                    call_id=message.tool_call_id or "",
                    name=message.tool_name or "",
                    arguments=arguments,
                )
            ],
        )
        return build_assistant_tool_call_message(turn)

    if message.role == "tool_result":
        return build_tool_result_message(message.tool_name or "", message.content)

    return {"role": message.role, "content": message.content}


def run_agent_turn(
    db: Session,
    chat_id: int,
    summary: str | None,
    history: list[Messages],
) -> Iterator[str]:
    tools = mcp_client.list_tools()

    conversation: list[dict[str, Any]] = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT}
    ]

    if summary:
        conversation.append(
            {
                "role": "system",
                "content": f"Summary of earlier conversation:\n\n{summary}",
            }
        )

    conversation.extend(_message_to_turn(message) for message in history)

    for iteration in range(conf.MAX_TOOL_ITERATIONS):
        is_last_iteration = iteration == conf.MAX_TOOL_ITERATIONS - 1

        turn = generate_turn(
            messages=conversation,
            tools=None if is_last_iteration else tools,
            model=conf.OLLAMA_AGENT_MODEL,
        )

        if not turn.tool_calls:
            for chunk in _chunk_text(turn.content):
                yield format_sse_event("chunk", {"text": chunk})

            assistant_message = create_message(
                db=db, chat_id=chat_id, role="assistant", content=turn.content
            )
            db.commit()

            yield sse_event_for_message("done", assistant_message)
            return

        conversation.append(build_assistant_tool_call_message(turn))

        for call in turn.tool_calls:
            tool_call_row = create_tool_call_message(
                db=db,
                chat_id=chat_id,
                call_id=call.call_id,
                tool_name=call.name,
                arguments=call.arguments,
            )
            db.commit()
            yield sse_event_for_message("tool_call", tool_call_row)

            result_content = _call_tool(call.name, call.arguments)

            tool_result_row = create_tool_result_message(
                db=db,
                chat_id=chat_id,
                call_id=call.call_id,
                tool_name=call.name,
                content=result_content,
            )
            db.commit()
            yield sse_event_for_message("tool_result", tool_result_row)

            conversation.append(build_tool_result_message(call.name, result_content))
