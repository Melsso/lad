import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from lad.core.sse import format_sse_event
from lad.helpers import chat as chat_module
from lad.schemas.config import conf


async def _collect(generator) -> list[str]:
    return [event async for event in generator]


def _session_returning(items):
    session = AsyncMock()
    session.add = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    result.scalars.return_value.first.return_value = items[0] if items else None
    session.execute.return_value = result
    return session


def _set_last_message(session, message):
    result = MagicMock()
    result.scalars.return_value.first.return_value = message
    session.execute = AsyncMock(return_value=result)


@pytest.fixture
def wire(monkeypatch, patch_db_session, mock_session):
    def _wire(chat, messages=None, summary=None):
        patch_db_session(mock_session)
        monkeypatch.setattr(chat_module, "get_chat", AsyncMock(return_value=chat))
        monkeypatch.setattr(chat_module, "create_message", AsyncMock())
        monkeypatch.setattr(
            chat_module, "get_chat_summary", AsyncMock(return_value=summary)
        )
        monkeypatch.setattr(
            chat_module,
            "get_messages_after_summary",
            AsyncMock(return_value=messages or []),
        )
        return mock_session

    return _wire


def test_format_sse_event_shape():
    result = format_sse_event("chunk", {"text": "hello"})

    assert result == 'event: chunk\ndata: {"text": "hello"}\n\n'


def test_format_sse_event_ends_with_double_newline():
    result = format_sse_event("done", {"id": 1})

    assert result.endswith("\n\n")


def test_format_sse_event_data_is_valid_json():
    payload = {"id": 1, "role": "assistant", "nested": {"a": 1}}

    result = format_sse_event("done", payload)
    data_line = result.split("\n")[1]

    assert data_line.startswith("data: ")
    assert json.loads(data_line[len("data: ") :]) == payload


async def test_get_chats_maps_rows_in_query_order(chat_factory):
    session = _session_returning([chat_factory(1, "First"), chat_factory(2, "Second")])

    result = await chat_module.get_chats(session)

    assert [c.title for c in result] == ["First", "Second"]


async def test_get_chat_messages_maps_rows_in_query_order(message_factory):
    session = _session_returning(
        [message_factory(1, content="hi"), message_factory(2, content="bye")]
    )

    result = await chat_module.get_chat_messages(session, chat_id=1)

    assert [m.content for m in result] == ["hi", "bye"]


async def test_get_chat_returns_chat_when_found(mock_session, chat_factory):
    chat = chat_factory(5)
    mock_session.get.return_value = chat

    assert await chat_module.get_chat(mock_session, chat_id=5) is chat


async def test_get_chat_returns_none_when_missing(mock_session):
    mock_session.get.return_value = None

    assert await chat_module.get_chat(mock_session, chat_id=999) is None


async def test_create_chat_adds_and_flushes(mock_session):
    chat = await chat_module.create_chat(mock_session, title="New Chat")

    assert chat.title == "New Chat"
    assert chat.mode == "chat"
    mock_session.add.assert_called_once_with(chat)
    mock_session.flush.assert_awaited_once()


async def test_create_chat_persists_agent_mode_when_requested(mock_session):
    chat = await chat_module.create_chat(mock_session, title="New Chat", mode="agent")

    assert chat.mode == "agent"


def test_generate_temporary_chat_title_collapses_whitespace():
    assert (
        chat_module.generate_temporary_chat_title("  hello   world  ") == "hello world"
    )


def test_generate_temporary_chat_title_defaults_when_empty():
    assert chat_module.generate_temporary_chat_title("") == "New Chat"
    assert chat_module.generate_temporary_chat_title("   ") == "New Chat"


def test_generate_temporary_chat_title_truncates_long_input():
    result = chat_module.generate_temporary_chat_title("x" * 80)

    assert len(result) == 50
    assert result.endswith("...")


async def test_update_chat_title_updates_when_found(
    monkeypatch, mock_session, chat_factory
):
    chat = chat_factory(1, title="Old Title")
    monkeypatch.setattr(chat_module, "get_chat", AsyncMock(return_value=chat))

    result = await chat_module.update_chat_title(
        mock_session, chat_id=1, title="  New Title  "
    )

    assert result is not None
    assert result.title == "New Title"
    mock_session.flush.assert_awaited_once()


async def test_update_chat_title_returns_none_when_missing(monkeypatch, mock_session):
    monkeypatch.setattr(chat_module, "get_chat", AsyncMock(return_value=None))

    result = await chat_module.update_chat_title(
        mock_session, chat_id=1, title="New Title"
    )

    assert result is None
    mock_session.flush.assert_not_awaited()


async def test_delete_chat_deletes_when_found(monkeypatch, mock_session, chat_factory):
    chat = chat_factory(1)
    monkeypatch.setattr(chat_module, "get_chat", AsyncMock(return_value=chat))

    result = await chat_module.delete_chat(mock_session, chat_id=1)

    assert result is True
    mock_session.delete.assert_awaited_once_with(chat)
    mock_session.flush.assert_awaited_once()


async def test_delete_chat_returns_false_when_missing(monkeypatch, mock_session):
    monkeypatch.setattr(chat_module, "get_chat", AsyncMock(return_value=None))

    result = await chat_module.delete_chat(mock_session, chat_id=1)

    assert result is False
    mock_session.delete.assert_not_awaited()


async def test_save_chat_summary_creates_when_missing(monkeypatch, mock_session):
    monkeypatch.setattr(chat_module, "get_chat_summary", AsyncMock(return_value=None))
    monkeypatch.setattr(
        chat_module, "embed_texts", AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    )

    result = await chat_module.save_chat_summary(
        mock_session, chat_id=1, content="new content", last_message_id=5
    )

    assert result.content == "new content"
    assert result.last_message_id == 5
    assert result.embedding == [0.1, 0.2, 0.3]
    mock_session.add.assert_called_once()
    mock_session.flush.assert_awaited_once()


async def test_save_chat_summary_updates_when_existing(
    monkeypatch, mock_session, summary_factory
):
    existing = summary_factory(chat_id=1, content="old", last_message_id=1)
    monkeypatch.setattr(
        chat_module, "get_chat_summary", AsyncMock(return_value=existing)
    )
    monkeypatch.setattr(
        chat_module, "embed_texts", AsyncMock(return_value=[[0.4, 0.5, 0.6]])
    )

    result = await chat_module.save_chat_summary(
        mock_session, chat_id=1, content="updated", last_message_id=9
    )

    assert result is existing
    assert result.content == "updated"
    assert result.last_message_id == 9
    assert result.embedding == [0.4, 0.5, 0.6]
    mock_session.add.assert_not_called()
    mock_session.flush.assert_awaited_once()


async def test_save_chat_summary_embeds_the_summary_content(monkeypatch, mock_session):
    monkeypatch.setattr(chat_module, "get_chat_summary", AsyncMock(return_value=None))
    embed = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    monkeypatch.setattr(chat_module, "embed_texts", embed)

    await chat_module.save_chat_summary(
        mock_session, chat_id=1, content="summary text", last_message_id=5
    )

    embed.assert_awaited_once_with(["summary text"])


async def test_stream_chat_msg_yields_error_when_chat_missing(wire):
    session = wire(None)

    events = await _collect(chat_module.stream_chat_msg(chat_id=1, msg="hi"))

    assert len(events) == 1
    assert "event: error" in events[0]
    assert "does not exist" in events[0]
    session.commit.assert_not_awaited()


async def test_stream_chat_msg_uses_chat_turn_for_chat_mode(
    monkeypatch, wire, chat_factory
):
    wire(chat_factory(1, mode="chat"))
    called = {"chat": False, "agent": False}

    async def fake_run_chat_turn(db, chat_id, summary, active_messages):
        called["chat"] = True
        yield format_sse_event("chunk", {"text": "hi"})

    async def fake_run_agent_turn(db, chat_id, summary, active_messages):
        called["agent"] = True
        yield format_sse_event("chunk", {"text": "should not run"})

    monkeypatch.setattr(chat_module, "run_chat_turn", fake_run_chat_turn)
    monkeypatch.setattr(chat_module, "run_agent_turn", fake_run_agent_turn)

    await _collect(chat_module.stream_chat_msg(chat_id=1, msg="hi"))

    assert called == {"chat": True, "agent": False}


async def test_stream_chat_msg_uses_agent_turn_for_agent_mode(
    monkeypatch, wire, chat_factory
):
    wire(chat_factory(1, mode="agent"))
    called = {"chat": False, "agent": False}

    async def fake_run_chat_turn(db, chat_id, summary, active_messages):
        called["chat"] = True
        yield format_sse_event("chunk", {"text": "should not run"})

    async def fake_run_agent_turn(db, chat_id, summary, active_messages):
        called["agent"] = True
        yield format_sse_event("chunk", {"text": "hi"})

    monkeypatch.setattr(chat_module, "run_chat_turn", fake_run_chat_turn)
    monkeypatch.setattr(chat_module, "run_agent_turn", fake_run_agent_turn)

    await _collect(chat_module.stream_chat_msg(chat_id=1, msg="hi"))

    assert called == {"chat": False, "agent": True}


async def test_stream_chat_msg_success_streams_and_persists(
    monkeypatch, wire, chat_factory
):
    session = wire(chat_factory(1, mode="chat"))

    async def fake_run_chat_turn(db, chat_id, summary, active_messages):
        yield format_sse_event("chunk", {"text": "Hel"})
        yield format_sse_event("chunk", {"text": "lo"})
        await session.commit()
        yield format_sse_event("done", {"id": 99, "content": "Hello"})

    monkeypatch.setattr(chat_module, "run_chat_turn", fake_run_chat_turn)

    events = await _collect(chat_module.stream_chat_msg(chat_id=1, msg="hi"))

    assert any("event: chunk" in e and '"text": "Hel"' in e for e in events)
    assert any("event: chunk" in e and '"text": "lo"' in e for e in events)
    assert any("event: done" in e for e in events)
    assert session.commit.await_count >= 2


async def test_stream_chat_msg_handles_llm_failure(monkeypatch, wire, chat_factory):
    session = wire(chat_factory(1, mode="chat"))

    async def broken_turn(db, chat_id, summary, active_messages):
        raise RuntimeError("503 UNAVAILABLE")
        yield  # pragma: no cover

    monkeypatch.setattr(chat_module, "run_chat_turn", broken_turn)

    events = await _collect(chat_module.stream_chat_msg(chat_id=1, msg="hi"))

    assert len(events) == 1
    assert "event: error" in events[0]
    assert "Failed to generate a response" in events[0]
    session.rollback.assert_awaited_once()


async def test_stream_chat_msg_triggers_summarization(
    monkeypatch, wire, chat_factory, message_factory
):
    threshold = conf.SUMMARY_THRESHOLD
    keep = conf.RECENT_MESSAGES_TO_KEEP

    messages = [message_factory(i, content=f"msg-{i}") for i in range(threshold)]
    wire(chat_factory(1, mode="chat"), messages=messages)

    summarize_calls = []

    async def fake_generate_summary(*, existing_summary, messages, model=None):
        summarize_calls.append(messages)
        return "condensed summary"

    async def fake_run_chat_turn(db, chat_id, summary, active_messages):
        assert summary == "condensed summary"
        assert len(active_messages) == keep
        yield format_sse_event("done", {"id": 99, "content": "ok"})

    monkeypatch.setattr(chat_module, "generate_summary", fake_generate_summary)
    monkeypatch.setattr(
        chat_module,
        "save_chat_summary",
        AsyncMock(return_value=SimpleNamespace(content="condensed summary")),
    )
    monkeypatch.setattr(chat_module, "run_chat_turn", fake_run_chat_turn)

    events = await _collect(chat_module.stream_chat_msg(chat_id=1, msg="hi"))

    assert len(summarize_calls) == 1
    assert len(summarize_calls[0]) == threshold - keep
    assert any("event: done" in e for e in events)


async def test_stream_chat_retry_errors_when_chat_missing(wire):
    wire(None)

    events = await _collect(chat_module.stream_chat_retry(chat_id=1))

    assert len(events) == 1
    assert "event: error" in events[0]
    assert "does not exist" in events[0]


async def test_stream_chat_retry_errors_when_nothing_to_retry(
    wire, chat_factory, message_factory
):
    session = wire(chat_factory(1))
    _set_last_message(
        session, message_factory(1, role="assistant", content="already answered")
    )

    events = await _collect(chat_module.stream_chat_retry(chat_id=1))

    assert len(events) == 1
    assert "event: error" in events[0]
    assert "Nothing to retry" in events[0]


async def test_stream_chat_retry_treats_trailing_tool_result_as_retryable(
    monkeypatch, wire, chat_factory, message_factory
):
    session = wire(chat_factory(1, mode="agent"))
    _set_last_message(
        session,
        message_factory(
            3,
            role="tool_result",
            content="extracted",
            tool_call_id="call_0",
            tool_name="run_command",
        ),
    )

    async def fake_run_agent_turn(db, chat_id, summary, active_messages):
        yield format_sse_event("done", {"id": 4, "content": "it's a zip of scripts"})

    monkeypatch.setattr(chat_module, "run_agent_turn", fake_run_agent_turn)

    events = await _collect(chat_module.stream_chat_retry(chat_id=1))

    assert not any("Nothing to retry" in e for e in events)
    assert any("event: done" in e for e in events)


async def test_stream_chat_retry_success_does_not_create_user_message(
    monkeypatch, wire, chat_factory, message_factory
):
    session = wire(chat_factory(1, mode="chat"))
    _set_last_message(session, message_factory(1, role="user", content="unanswered"))

    create_message = AsyncMock()
    monkeypatch.setattr(chat_module, "create_message", create_message)

    async def fake_run_chat_turn(db, chat_id, summary, active_messages):
        yield format_sse_event("done", {"id": 2, "content": "a reply"})

    monkeypatch.setattr(chat_module, "run_chat_turn", fake_run_chat_turn)

    events = await _collect(chat_module.stream_chat_retry(chat_id=1))

    create_message.assert_not_awaited()
    assert any("event: done" in e for e in events)


async def test_stream_chat_retry_handles_llm_failure(
    monkeypatch, wire, chat_factory, message_factory
):
    session = wire(chat_factory(1, mode="chat"))
    _set_last_message(session, message_factory(1, role="user", content="unanswered"))

    async def broken_turn(db, chat_id, summary, active_messages):
        raise RuntimeError("503 UNAVAILABLE")
        yield  # pragma: no cover

    monkeypatch.setattr(chat_module, "run_chat_turn", broken_turn)

    events = await _collect(chat_module.stream_chat_retry(chat_id=1))

    assert len(events) == 1
    assert "event: error" in events[0]
    assert "Failed to generate a response" in events[0]
    session.rollback.assert_awaited_once()


def test_split_for_summary_keeps_the_most_recent_messages(message_factory):
    messages = [message_factory(i) for i in range(10)]

    old, recent = chat_module._split_for_summary(messages, keep=4)

    assert [m.id for m in old] == [0, 1, 2, 3, 4, 5]
    assert [m.id for m in recent] == [6, 7, 8, 9]


def test_split_for_summary_does_not_orphan_a_tool_result(message_factory):
    messages = [
        message_factory(0, role="user"),
        message_factory(1, role="assistant"),
        message_factory(2, role="tool_call"),
        message_factory(3, role="tool_result"),
        message_factory(4, role="assistant"),
    ]

    old, recent = chat_module._split_for_summary(messages, keep=2)

    assert [m.id for m in old] == [0, 1]
    assert [m.id for m in recent] == [2, 3, 4]


def test_split_for_summary_with_nothing_to_summarize(message_factory):
    messages = [
        message_factory(0, role="tool_call"),
        message_factory(1, role="tool_result"),
    ]

    old, recent = chat_module._split_for_summary(messages, keep=1)

    assert old == []
    assert [m.id for m in recent] == [0, 1]


@pytest.mark.parametrize(
    ("mode", "expected_model"),
    [("agent", conf.OLLAMA_AGENT_MODEL), ("chat", None)],
)
async def test_summarization_uses_the_matching_model(
    monkeypatch, wire, chat_factory, message_factory, mode, expected_model
):
    messages = [message_factory(i) for i in range(conf.SUMMARY_THRESHOLD)]
    wire(chat_factory(1, mode=mode), messages=messages)

    captured = {}

    async def fake_generate_summary(*, existing_summary, messages, model=None):
        captured["model"] = model
        return "condensed"

    async def fake_turn(db, chat_id, summary, active_messages):
        yield format_sse_event("done", {"id": 1, "content": "ok"})

    monkeypatch.setattr(chat_module, "generate_summary", fake_generate_summary)
    monkeypatch.setattr(
        chat_module,
        "save_chat_summary",
        AsyncMock(return_value=SimpleNamespace(content="condensed")),
    )
    monkeypatch.setattr(chat_module, "run_chat_turn", fake_turn)
    monkeypatch.setattr(chat_module, "run_agent_turn", fake_turn)

    await _collect(chat_module.stream_chat_msg(chat_id=1, msg="hi"))

    assert captured["model"] == expected_model
