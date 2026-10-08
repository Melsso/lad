from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from lad.models.db import Chat, ConversationSummary
from lad.tools import memory_server


class _SessionContext:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *args):
        return False


def _patch_session(monkeypatch, rows):
    result = MagicMock()
    result.all.return_value = rows

    session = AsyncMock()
    session.execute.return_value = result

    monkeypatch.setattr(
        memory_server, "get_db_session", lambda: _SessionContext(session)
    )
    monkeypatch.setattr(
        memory_server, "embed_query", AsyncMock(return_value=[0.1, 0.2, 0.3])
    )

    return session


def _executed_params(session) -> dict:
    statement = session.execute.call_args.args[0]

    return statement.compile().params


async def test_recall_memory_clamps_top_k_below_minimum(monkeypatch):
    monkeypatch.delenv("LAD_CHAT_ID", raising=False)
    session = _patch_session(monkeypatch, [])

    await memory_server.recall_memory("what did we decide", top_k=1)

    assert 3 in _executed_params(session).values()


async def test_recall_memory_returns_message_when_nothing_found(monkeypatch):
    monkeypatch.delenv("LAD_CHAT_ID", raising=False)
    _patch_session(monkeypatch, [])

    result = await memory_server.recall_memory("anything")

    assert result == "No relevant past conversations found."


async def test_recall_memory_excludes_the_current_chat_when_env_var_set(monkeypatch):
    monkeypatch.setenv("LAD_CHAT_ID", "7")
    session = _patch_session(monkeypatch, [])

    await memory_server.recall_memory("anything")

    assert 7 in _executed_params(session).values()


async def test_recall_memory_does_not_filter_by_chat_when_env_var_unset(monkeypatch):
    monkeypatch.delenv("LAD_CHAT_ID", raising=False)
    session = _patch_session(monkeypatch, [])

    await memory_server.recall_memory("anything")

    params = _executed_params(session)
    assert not any(key.startswith("chat_id") for key in params)


async def test_recall_memory_formats_results_with_chat_title_and_date(monkeypatch):
    monkeypatch.delenv("LAD_CHAT_ID", raising=False)

    chat = Chat(id=3, title="Deployment plan", mode="chat")
    chat.created_at = datetime(2026, 1, 15, tzinfo=UTC)
    summary = ConversationSummary(
        id=1, chat_id=3, content="Decided to use Docker Compose.", last_message_id=1
    )

    _patch_session(monkeypatch, [(summary, chat)])

    result = await memory_server.recall_memory("deployment")

    assert result == (
        "# Deployment plan (chat 3, 2026-01-15)\nDecided to use Docker Compose."
    )


async def test_recall_memory_clamps_top_k_above_maximum(monkeypatch):
    monkeypatch.delenv("LAD_CHAT_ID", raising=False)
    session = _patch_session(monkeypatch, [])

    await memory_server.recall_memory("anything", top_k=500)

    assert memory_server.MAX_TOP_K in _executed_params(session).values()
