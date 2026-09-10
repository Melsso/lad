from typing import Any

import httpx

from lad.schemas.config import conf

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


def search_web(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    if not conf.TAVILY_API_KEY:
        raise RuntimeError(
            "TAVILY_API_KEY is not set. Get a free key at https://tavily.com "
            "and add it to backend/.env"
        )

    response = httpx.post(
        TAVILY_SEARCH_URL,
        headers={"Authorization": f"Bearer {conf.TAVILY_API_KEY}"},
        json={
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
        },
        timeout=20.0,
    )
    response.raise_for_status()

    return response.json().get("results", [])
