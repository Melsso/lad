from unittest.mock import MagicMock

import pytest

from lad.core import embeddings


def test_embed_texts_raises_a_clear_error_when_model_not_found(monkeypatch):
    mock_response = MagicMock()
    mock_response.status_code = 404

    monkeypatch.setattr(embeddings.httpx, "post", MagicMock(return_value=mock_response))

    with pytest.raises(RuntimeError, match="ollama pull embeddinggemma"):
        embeddings.embed_texts(["hello"])


def test_embed_texts_posts_model_and_input_and_returns_embeddings(monkeypatch):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "model": "embeddinggemma",
        "embeddings": [[0.1, 0.2], [0.3, 0.4]],
    }

    mock_post = MagicMock(return_value=mock_response)
    monkeypatch.setattr(embeddings.httpx, "post", mock_post)

    result = embeddings.embed_texts(["a", "b"])

    assert result == [[0.1, 0.2], [0.3, 0.4]]
    _, kwargs = mock_post.call_args
    assert kwargs["json"]["input"] == ["a", "b"]
    assert kwargs["json"]["model"] == "embeddinggemma"


def test_embed_query_returns_the_first_vector(monkeypatch):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"embeddings": [[0.5, 0.6]]}

    monkeypatch.setattr(embeddings.httpx, "post", MagicMock(return_value=mock_response))

    assert embeddings.embed_query("hello") == [0.5, 0.6]
