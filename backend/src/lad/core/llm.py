import json
from typing import Any

import httpx

from lad.schemas.config import conf
from lad.schemas.llm import LLMTurn, ToolCall, ToolDefinition


def raise_for_ollama_status(response: httpx.Response, model: str) -> None:
    if response.status_code == 404:
        raise RuntimeError(
            f"Ollama model '{model}' was not found. "
            f"Pull it first with: ollama pull {model}"
        )

    response.raise_for_status()


def _build_messages(
    *, contents: str, system_instruction: str | None
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []

    if system_instruction is not None:
        messages.append({"role": "system", "content": system_instruction})

    messages.append({"role": "user", "content": contents})

    return messages


def _build_options(
    *, temperature: float | None, num_ctx: int | None = None
) -> dict[str, float | int]:
    options: dict[str, float | int] = {}

    if temperature is not None:
        options["temperature"] = temperature

    if num_ctx is not None:
        options["num_ctx"] = num_ctx

    return options


async def generate_content(
    *,
    contents: str,
    system_instruction: str | None = None,
    temperature: float | None = None,
    model: str | None = None,
) -> str:
    resolved_model = model or conf.OLLAMA_MODEL

    body = await _chat(
        {
            "model": resolved_model,
            "messages": _build_messages(
                contents=contents, system_instruction=system_instruction
            ),
            "stream": False,
            "options": _build_options(
                temperature=temperature, num_ctx=conf.OLLAMA_NUM_CTX
            ),
        },
        resolved_model,
    )

    text = body.get("message", {}).get("content", "")

    if not text:
        raise RuntimeError("LLM returned an empty response")

    return text.strip()


def _build_tools(tools: list[ToolDefinition]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in tools
    ]


def _parse_arguments(raw_arguments: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(raw_arguments, str):
        return json.loads(raw_arguments)

    return raw_arguments


def _parse_tool_calls(raw_tool_calls: list[dict[str, Any]]) -> list[ToolCall]:
    return [
        ToolCall(
            call_id=f"call_{index}",
            name=raw_call["function"]["name"],
            arguments=_parse_arguments(raw_call["function"].get("arguments", {})),
        )
        for index, raw_call in enumerate(raw_tool_calls)
    ]


def build_assistant_tool_call_message(turn: LLMTurn) -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": turn.content,
        "tool_calls": [
            {"function": {"name": call.name, "arguments": call.arguments}}
            for call in turn.tool_calls
        ],
    }


def build_tool_result_message(tool_name: str, content: str) -> dict[str, Any]:
    return {"role": "tool", "tool_name": tool_name, "content": content}


async def generate_turn(
    *,
    messages: list[dict[str, Any]],
    tools: list[ToolDefinition] | None = None,
    temperature: float | None = None,
    model: str | None = None,
) -> LLMTurn:
    resolved_model = model or conf.OLLAMA_MODEL

    payload: dict[str, Any] = {
        "model": resolved_model,
        "messages": messages,
        "stream": False,
        "options": _build_options(temperature=temperature, num_ctx=conf.OLLAMA_NUM_CTX),
    }

    if tools:
        payload["tools"] = _build_tools(tools)

    body = await _chat(payload, resolved_model)
    message = body.get("message", {})

    return LLMTurn(
        content=message.get("content", "").strip(),
        tool_calls=_parse_tool_calls(message.get("tool_calls", [])),
    )


async def _chat(payload: dict[str, Any], model: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=conf.OLLAMA_TIMEOUT) as client:
        response = await client.post(f"{conf.OLLAMA_HOST}/api/chat", json=payload)

    raise_for_ollama_status(response, model)

    return response.json()
