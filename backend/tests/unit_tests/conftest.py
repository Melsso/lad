import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("MCP_SERVERS", "[]")


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def chat_factory():
    from lad.models.db import Chat

    def _factory(chat_id=1, title="Test Chat", mode="chat", created_at=None):
        return Chat(
            id=chat_id,
            title=title,
            mode=mode,
            created_at=created_at or datetime.now(UTC),
        )

    return _factory


@pytest.fixture
def message_factory():
    from lad.models.db import Messages

    def _factory(
        message_id,
        chat_id=1,
        role="user",
        content="hello",
        created_at=None,
        tool_call_id=None,
        tool_name=None,
        tool_arguments=None,
        attached_files=None,
    ):
        return Messages(
            id=message_id,
            chat_id=chat_id,
            role=role,
            content=content,
            created_at=created_at or datetime.now(UTC),
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            tool_arguments=tool_arguments,
            attached_files=attached_files,
        )

    return _factory


@pytest.fixture
def summary_factory():
    from lad.models.db import ConversationSummary

    def _factory(chat_id=1, content="summary", last_message_id=1):
        return ConversationSummary(
            id=1,
            chat_id=chat_id,
            content=content,
            last_message_id=last_message_id,
            created_at=datetime.now(UTC),
        )

    return _factory


@pytest.fixture
def patch_db_session(monkeypatch):
    from lad.helpers import chat as chat_module

    @asynccontextmanager
    async def _fake_context(session):
        yield session

    def _patch(session):
        monkeypatch.setattr(
            chat_module, "get_db_session", lambda: _fake_context(session)
        )

    return _patch


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from lad.core.app import create_app
    from lad.core.db import get_db

    app = create_app()
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    return TestClient(app)
