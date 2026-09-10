from unittest.mock import MagicMock

import pytest

from lad.core import web_search


def test_search_web_raises_a_clear_error_when_api_key_missing(monkeypatch):
    monkeypatch.setattr(web_search.conf, "TAVILY_API_KEY", "")

    with pytest.raises(RuntimeError, match="TAVILY_API_KEY is not set"):
        web_search.search_web("what is the capital of France")


def test_search_web_sends_query_and_max_results(monkeypatch):
    monkeypatch.setattr(web_search.conf, "TAVILY_API_KEY", "tvly-test-key")

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"results": []}

    mock_post = MagicMock(return_value=mock_response)
    monkeypatch.setattr(web_search.httpx, "post", mock_post)

    web_search.search_web("latest ollama release", max_results=7)

    _, kwargs = mock_post.call_args
    assert kwargs["json"]["query"] == "latest ollama release"
    assert kwargs["json"]["max_results"] == 7
    assert kwargs["headers"]["Authorization"] == "Bearer tvly-test-key"


def test_search_web_returns_the_results_list(monkeypatch):
    monkeypatch.setattr(web_search.conf, "TAVILY_API_KEY", "tvly-test-key")

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "results": [
            {"title": "Ollama Releases", "url": "https://example.com", "content": "..."}
        ]
    }

    monkeypatch.setattr(web_search.httpx, "post", MagicMock(return_value=mock_response))

    results = web_search.search_web("latest ollama release")

    assert results == [
        {"title": "Ollama Releases", "url": "https://example.com", "content": "..."}
    ]


def test_search_web_returns_empty_list_when_results_key_missing(monkeypatch):
    monkeypatch.setattr(web_search.conf, "TAVILY_API_KEY", "tvly-test-key")

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {}

    monkeypatch.setattr(web_search.httpx, "post", MagicMock(return_value=mock_response))

    assert web_search.search_web("anything") == []
