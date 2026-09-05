import json
from collections.abc import Iterator

import httpx

from lad.schemas.config import conf


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
    response.raise_for_status()

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
        response.raise_for_status()

        for line in response.iter_lines():
            if not line:
                continue

            chunk = json.loads(line)

            text = chunk.get("message", {}).get("content")
            if text:
                yield text

            if chunk.get("done"):
                break
