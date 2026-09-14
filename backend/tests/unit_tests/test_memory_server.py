from unittest.mock import MagicMock

from lad.tools import memory_server


class _SessionContext:
    def __init__(self, session):
        self._session = session

    def __enter__(self):
        return self._session

    def __exit__(self, *args):
        return False


def _patch_session(monkeypatch, results):
    mock_query = MagicMock()
    mock_query.join.return_value.filter.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = results
    mock_query.join.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = results

    mock_session = MagicMock()
    mock_session.query.return_value = mock_query

    monkeypatch.setattr(
        memory_server, "get_db_session", lambda: _SessionContext(mock_session)
    )

    return mock_query


def test_recall_memory_clamps_top_k_below_minimum(monkeypatch):
    monkeypatch.setattr(memory_server, "embed_query", lambda query: [0.1, 0.2, 0.3])
    monkeypatch.delenv("LAD_CHAT_ID", raising=False)
    mock_query = _patch_session(monkeypatch, [])

    memory_server.recall_memory("what did we decide", top_k=1)

    limit_call = (
        mock_query.join.return_value.filter.return_value.order_by.return_value.limit
    )
    limit_call.assert_called_once_with(3)


def test_recall_memory_returns_message_when_nothing_found(monkeypatch):
    monkeypatch.setattr(memory_server, "embed_query", lambda query: [0.1, 0.2, 0.3])
    monkeypatch.delenv("LAD_CHAT_ID", raising=False)
    _patch_session(monkeypatch, [])

    result = memory_server.recall_memory("anything")

    assert result == "No relevant past conversations found."


def test_recall_memory_excludes_the_current_chat_when_env_var_set(monkeypatch):
    monkeypatch.setattr(memory_server, "embed_query", lambda query: [0.1, 0.2, 0.3])
    monkeypatch.setenv("LAD_CHAT_ID", "7")
    mock_query = _patch_session(monkeypatch, [])

    memory_server.recall_memory("anything")

    mock_query.join.return_value.filter.assert_called_once()
    filter_arg = mock_query.join.return_value.filter.call_args
    second_filter = mock_query.join.return_value.filter.return_value.filter
    second_filter.assert_called_once()
    assert filter_arg is not None


def test_recall_memory_does_not_filter_by_chat_when_env_var_unset(monkeypatch):
    monkeypatch.setattr(memory_server, "embed_query", lambda query: [0.1, 0.2, 0.3])
    monkeypatch.delenv("LAD_CHAT_ID", raising=False)
    mock_query = _patch_session(monkeypatch, [])

    memory_server.recall_memory("anything")

    mock_query.join.return_value.filter.return_value.filter.assert_not_called()


def test_recall_memory_formats_results_with_chat_title_and_date(monkeypatch):
    from datetime import UTC, datetime

    from lad.models.db import Chat, ConversationSummary

    monkeypatch.setattr(memory_server, "embed_query", lambda query: [0.1, 0.2, 0.3])
    monkeypatch.delenv("LAD_CHAT_ID", raising=False)

    chat = Chat(id=3, title="Deployment plan", mode="chat")
    chat.created_at = datetime(2026, 1, 15, tzinfo=UTC)
    summary = ConversationSummary(
        id=1, chat_id=3, content="Decided to use Docker Compose.", last_message_id=1
    )

    _patch_session(monkeypatch, [(summary, chat)])

    result = memory_server.recall_memory("deployment")

    assert result == (
        "# Deployment plan (chat 3, 2026-01-15)\nDecided to use Docker Compose."
    )
