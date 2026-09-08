from unittest.mock import MagicMock

from lad.tools import rag_server


def test_search_docs_clamps_top_k_below_minimum(monkeypatch):
    monkeypatch.setattr(rag_server, "embed_query", lambda query: [0.1, 0.2, 0.3])

    mock_query = MagicMock()
    mock_query.order_by.return_value.limit.return_value.all.return_value = []

    mock_session = MagicMock()
    mock_session.query.return_value = mock_query

    class _SessionContext:
        def __enter__(self):
            return mock_session

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(rag_server, "get_db_session", lambda: _SessionContext())

    rag_server.search_docs("how does the agent loop stop", top_k=1)

    mock_query.order_by.return_value.limit.assert_called_once_with(5)


def test_search_docs_does_not_lower_a_top_k_already_above_minimum(monkeypatch):
    monkeypatch.setattr(rag_server, "embed_query", lambda query: [0.1, 0.2, 0.3])

    mock_query = MagicMock()
    mock_query.order_by.return_value.limit.return_value.all.return_value = []

    mock_session = MagicMock()
    mock_session.query.return_value = mock_query

    class _SessionContext:
        def __enter__(self):
            return mock_session

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(rag_server, "get_db_session", lambda: _SessionContext())

    rag_server.search_docs("how does the agent loop stop", top_k=10)

    mock_query.order_by.return_value.limit.assert_called_once_with(10)


def test_search_docs_returns_message_when_nothing_found(monkeypatch):
    monkeypatch.setattr(rag_server, "embed_query", lambda query: [0.1, 0.2, 0.3])

    mock_query = MagicMock()
    mock_query.order_by.return_value.limit.return_value.all.return_value = []

    mock_session = MagicMock()
    mock_session.query.return_value = mock_query

    class _SessionContext:
        def __enter__(self):
            return mock_session

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(rag_server, "get_db_session", lambda: _SessionContext())

    result = rag_server.search_docs("anything")

    assert result == "No relevant documents found."
