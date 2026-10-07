import httpx

from lad.core.llm import raise_for_ollama_status
from lad.schemas.config import conf


async def embed_texts(texts: list[str]) -> list[list[float]]:
    async with httpx.AsyncClient(timeout=conf.OLLAMA_TIMEOUT) as client:
        response = await client.post(
            f"{conf.OLLAMA_HOST}/api/embed",
            json={"model": conf.OLLAMA_EMBED_MODEL, "input": texts},
        )

    raise_for_ollama_status(response, conf.OLLAMA_EMBED_MODEL)

    return response.json()["embeddings"]


async def embed_query(text: str) -> list[float]:
    return (await embed_texts([text]))[0]
