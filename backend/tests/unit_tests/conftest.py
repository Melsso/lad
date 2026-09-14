import os
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("MCP_SERVERS", "[]")


@pytest.fixture
def mock_session():
    return MagicMock()


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
def session_builder():
    from lad.models.db import Chat, ConversationSummary, Messages

    def _build(chat=None, messages=None, summary=None):
        session = MagicMock()

        chat_query = MagicMock()
        chat_query.filter.return_value.first.return_value = chat

        messages_query = MagicMock()
        messages_query.filter.return_value.filter.return_value = (
            messages_query.filter.return_value
        )
        messages_query.filter.return_value.order_by.return_value.all.return_value = (
            messages or []
        )
        messages_query.filter.return_value.order_by.return_value.first.return_value = (
            messages[-1] if messages else None
        )

        summary_query = MagicMock()
        summary_query.filter.return_value.first.return_value = summary

        def query_side_effect(model):
            if model is Chat:
                return chat_query
            if model is Messages:
                return messages_query
            if model is ConversationSummary:
                return summary_query
            return MagicMock()

        session.query.side_effect = query_side_effect
        return session

    return _build


@pytest.fixture
def patch_db_session(monkeypatch):
    from lad.helpers import chat as chat_module

    @contextmanager
    def _fake_context(session):
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
    app.dependency_overrides[get_db] = lambda: MagicMock()

    return TestClient(app)
