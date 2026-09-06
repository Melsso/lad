import httpx

from lad.core.llm import raise_for_ollama_status
from lad.schemas.config import conf


def embed_texts(texts: list[str]) -> list[list[float]]:
    response = httpx.post(
        f"{conf.OLLAMA_HOST}/api/embed",
        json={"model": conf.OLLAMA_EMBED_MODEL, "input": texts},
        timeout=conf.OLLAMA_TIMEOUT,
    )
    raise_for_ollama_status(response, conf.OLLAMA_EMBED_MODEL)

    return response.json()["embeddings"]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
