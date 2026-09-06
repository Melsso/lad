import json
from collections.abc import Iterator
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


def _build_options(*, temperature: float | None) -> dict[str, float]:
    options: dict[str, float] = {}

    if temperature is not None:
        options["temperature"] = temperature

    return options


def generate_content(
    *,
    contents: str,
    system_instruction: str | None = None,
    temperature: float | None = None,
) -> str:
    response = httpx.post(
        f"{conf.OLLAMA_HOST}/api/chat",
        json={
            "model": conf.OLLAMA_MODEL,
            "messages": _build_messages(
                contents=contents, system_instruction=system_instruction
            ),
            "stream": False,
            "options": _build_options(temperature=temperature),
        },
        timeout=conf.OLLAMA_TIMEOUT,
    )
    raise_for_ollama_status(response, conf.OLLAMA_MODEL)

    text = response.json().get("message", {}).get("content", "")

    if not text:
        raise RuntimeError("LLM returned an empty response")

    return text.strip()


def stream_content(
    *,
    contents: str,
    system_instruction: str | None = None,
    temperature: float | None = None,
) -> Iterator[str]:
    with httpx.stream(
        "POST",
        f"{conf.OLLAMA_HOST}/api/chat",
        json={
            "model": conf.OLLAMA_MODEL,
            "messages": _build_messages(
                contents=contents, system_instruction=system_instruction
            ),
            "stream": True,
            "options": _build_options(temperature=temperature),
        },
        timeout=conf.OLLAMA_TIMEOUT,
    ) as response:
        raise_for_ollama_status(response, conf.OLLAMA_MODEL)

        for line in response.iter_lines():
            if not line:
                continue

            chunk = json.loads(line)

            text = chunk.get("message", {}).get("content")
            if text:
                yield text

            if chunk.get("done"):
                break


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


def generate_turn(
    *,
    messages: list[dict[str, Any]],
    tools: list[ToolDefinition] | None = None,
    temperature: float | None = None,
) -> LLMTurn:
    payload: dict[str, Any] = {
        "model": conf.OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": _build_options(temperature=temperature),
    }

    if tools:
        payload["tools"] = _build_tools(tools)

    response = httpx.post(
        f"{conf.OLLAMA_HOST}/api/chat",
        json=payload,
        timeout=conf.OLLAMA_TIMEOUT,
    )
    raise_for_ollama_status(response, conf.OLLAMA_MODEL)

    message = response.json().get("message", {})

    return LLMTurn(
        content=message.get("content", "").strip(),
        tool_calls=_parse_tool_calls(message.get("tool_calls", [])),
    )
