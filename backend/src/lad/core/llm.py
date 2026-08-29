from collections.abc import Iterator

from google import genai
from google.genai import types

from lad.schemas.config import conf

client = genai.Client(
    api_key=conf.GEMINI_API_KEY,
)


def generate_content(
    *,
    contents: str,
    system_instruction: str | None = None,
    temperature: float | None = None,
) -> str:
    config = types.GenerateContentConfig()

    if system_instruction is not None:
        config.system_instruction = system_instruction

    if temperature is not None:
        config.temperature = temperature

    response = client.models.generate_content(
        model=conf.GEMINI_MODEL,
        contents=contents,
        config=config,
    )

    if not response.text:
        raise RuntimeError("LLM returned an empty response")

    return response.text.strip()


def stream_content(
    *,
    contents: str,
    system_instruction: str | None = None,
    temperature: float | None = None,
) -> Iterator[str]:
    config = types.GenerateContentConfig()

    if system_instruction is not None:
        config.system_instruction = system_instruction

    if temperature is not None:
        config.temperature = temperature

    stream = client.models.generate_content_stream(
        model=conf.GEMINI_MODEL,
        contents=contents,
        config=config,
    )

    for chunk in stream:
        if chunk.text:
            yield chunk.text
