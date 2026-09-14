import json

from lad.core.sse import format_sse_event
from lad.helpers import chat as chat_module


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


def test_get_chats_returns_ordered_chats(mock_session, chat_factory):
    chats = [chat_factory(1, "First"), chat_factory(2, "Second")]
    mock_session.query.return_value.order_by.return_value.all.return_value = chats

    result = chat_module.get_chats(mock_session)

    assert [c.title for c in result] == ["First", "Second"]


def test_get_chat_messages_returns_ordered_messages(mock_session, message_factory):
    messages = [message_factory(1, content="hi"), message_factory(2, content="bye")]
    mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = messages

    result = chat_module.get_chat_messages(mock_session, chat_id=1)

    assert [m.content for m in result] == ["hi", "bye"]


def test_get_chat_returns_chat_when_found(mock_session, chat_factory):
    chat = chat_factory(5)
    mock_session.query.return_value.filter.return_value.first.return_value = chat

    result = chat_module.get_chat(mock_session, chat_id=5)

    assert result is chat


def test_get_chat_returns_none_when_missing(mock_session):
    mock_session.query.return_value.filter.return_value.first.return_value = None

    result = chat_module.get_chat(mock_session, chat_id=999)

    assert result is None


def test_create_chat_adds_and_flushes(mock_session):
    chat = chat_module.create_chat(mock_session, title="New Chat")

    assert chat.title == "New Chat"
    assert chat.mode == "chat"
    mock_session.add.assert_called_once_with(chat)
    mock_session.flush.assert_called_once()


def test_create_chat_persists_agent_mode_when_requested(mock_session):
    chat = chat_module.create_chat(mock_session, title="New Chat", mode="agent")

    assert chat.mode == "agent"


def test_stream_chat_msg_uses_plain_reply_for_chat_mode(
    monkeypatch, session_builder, patch_db_session, chat_factory, message_factory
):
    chat = chat_factory(1, mode="chat")
    session = session_builder(chat=chat, messages=[], summary=None)
    patch_db_session(session)

    plain_reply_called = {"value": False}
    agent_turn_called = {"value": False}

    def fake_stream_plain_reply(db, chat_id, summary, active_messages):
        plain_reply_called["value"] = True
        yield format_sse_event("chunk", {"text": "hi"})

    def fake_run_agent_turn(db, chat_id, summary, active_messages):
        agent_turn_called["value"] = True
        yield format_sse_event("chunk", {"text": "should not run"})

    monkeypatch.setattr(chat_module, "_stream_plain_reply", fake_stream_plain_reply)
    monkeypatch.setattr(chat_module, "run_agent_turn", fake_run_agent_turn)

    list(chat_module.stream_chat_msg(chat_id=1, msg="hi"))

    assert plain_reply_called["value"] is True
    assert agent_turn_called["value"] is False


def test_stream_chat_msg_uses_agent_turn_for_agent_mode(
    monkeypatch, session_builder, patch_db_session, chat_factory, message_factory
):
    chat = chat_factory(1, mode="agent")
    session = session_builder(chat=chat, messages=[], summary=None)
    patch_db_session(session)

    plain_reply_called = {"value": False}
    agent_turn_called = {"value": False}

    def fake_stream_plain_reply(db, chat_id, summary, active_messages):
        plain_reply_called["value"] = True
        yield format_sse_event("chunk", {"text": "should not run"})

    def fake_run_agent_turn(db, chat_id, summary, active_messages):
        agent_turn_called["value"] = True
        yield format_sse_event("chunk", {"text": "hi"})

    monkeypatch.setattr(chat_module, "_stream_plain_reply", fake_stream_plain_reply)
    monkeypatch.setattr(chat_module, "run_agent_turn", fake_run_agent_turn)

    list(chat_module.stream_chat_msg(chat_id=1, msg="hi"))

    assert agent_turn_called["value"] is True
    assert plain_reply_called["value"] is False


def test_generate_temporary_chat_title_collapses_whitespace():
    assert (
        chat_module.generate_temporary_chat_title("  hello   world  ") == "hello world"
    )


def test_generate_temporary_chat_title_defaults_when_empty():
    assert chat_module.generate_temporary_chat_title("") == "New Chat"
    assert chat_module.generate_temporary_chat_title("   ") == "New Chat"


def test_generate_temporary_chat_title_truncates_long_input():
    raw = "x" * 80
    result = chat_module.generate_temporary_chat_title(raw)

    assert len(result) == 50
    assert result.endswith("...")


def test_update_chat_title_updates_when_found(monkeypatch, mock_session, chat_factory):
    chat = chat_factory(1, title="Old Title")
    monkeypatch.setattr(chat_module, "get_chat", lambda db, chat_id: chat)

    result = chat_module.update_chat_title(
        mock_session, chat_id=1, title="  New Title  "
    )

    assert result is not None
    assert result.title == "New Title"
    mock_session.flush.assert_called_once()


def test_update_chat_title_returns_none_when_missing(monkeypatch, mock_session):
    monkeypatch.setattr(chat_module, "get_chat", lambda db, chat_id: None)

    result = chat_module.update_chat_title(mock_session, chat_id=1, title="New Title")

    assert result is None
    mock_session.flush.assert_not_called()


def test_delete_chat_deletes_when_found(monkeypatch, mock_session, chat_factory):
    chat = chat_factory(1)
    monkeypatch.setattr(chat_module, "get_chat", lambda db, chat_id: chat)

    result = chat_module.delete_chat(mock_session, chat_id=1)

    assert result is True
    mock_session.delete.assert_called_once_with(chat)
    mock_session.flush.assert_called_once()


def test_delete_chat_returns_false_when_missing(monkeypatch, mock_session):
    monkeypatch.setattr(chat_module, "get_chat", lambda db, chat_id: None)

    result = chat_module.delete_chat(mock_session, chat_id=1)

    assert result is False
    mock_session.delete.assert_not_called()


def test_get_messages_after_summary_without_last_id(mock_session, message_factory):
    messages = [message_factory(1), message_factory(2)]
    mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = messages

    result = chat_module.get_messages_after_summary(
        mock_session, chat_id=1, last_message_id=None
    )

    assert result == messages
    mock_session.query.return_value.filter.assert_called_once()


def test_get_messages_after_summary_with_last_id_filters_twice(
    mock_session, message_factory
):
    messages = [message_factory(3)]
    filter_mock = mock_session.query.return_value.filter.return_value
    filter_mock.filter.return_value.order_by.return_value.all.return_value = messages

    result = chat_module.get_messages_after_summary(
        mock_session, chat_id=1, last_message_id=2
    )

    assert result == messages
    filter_mock.filter.assert_called_once()


def test_save_chat_summary_creates_when_missing(monkeypatch, mock_session):
    monkeypatch.setattr(chat_module, "get_chat_summary", lambda db, chat_id: None)
    monkeypatch.setattr(chat_module, "embed_texts", lambda texts: [[0.1, 0.2, 0.3]])

    result = chat_module.save_chat_summary(
        mock_session, chat_id=1, content="new content", last_message_id=5
    )

    assert result.content == "new content"
    assert result.last_message_id == 5
    assert result.embedding == [0.1, 0.2, 0.3]
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()


def test_save_chat_summary_updates_when_existing(
    monkeypatch, mock_session, summary_factory
):
    existing = summary_factory(chat_id=1, content="old", last_message_id=1)
    monkeypatch.setattr(chat_module, "get_chat_summary", lambda db, chat_id: existing)
    monkeypatch.setattr(chat_module, "embed_texts", lambda texts: [[0.4, 0.5, 0.6]])

    result = chat_module.save_chat_summary(
        mock_session, chat_id=1, content="updated", last_message_id=9
    )

    assert result is existing
    assert result.content == "updated"
    assert result.last_message_id == 9
    assert result.embedding == [0.4, 0.5, 0.6]
    mock_session.add.assert_not_called()
    mock_session.flush.assert_called_once()


def test_save_chat_summary_embeds_the_summary_content_not_something_else(
    monkeypatch, mock_session
):
    monkeypatch.setattr(chat_module, "get_chat_summary", lambda db, chat_id: None)

    captured_texts = []

    def fake_embed_texts(texts):
        captured_texts.extend(texts)
        return [[0.1, 0.2, 0.3]]

    monkeypatch.setattr(chat_module, "embed_texts", fake_embed_texts)

    chat_module.save_chat_summary(
        mock_session, chat_id=1, content="summary text", last_message_id=5
    )

    assert captured_texts == ["summary text"]


def test_stream_chat_msg_yields_error_when_chat_missing(
    session_builder, patch_db_session
):
    session = session_builder(chat=None)
    patch_db_session(session)

    events = list(chat_module.stream_chat_msg(chat_id=1, msg="hi"))

    assert len(events) == 1
    assert "event: error" in events[0]
    assert "does not exist" in events[0]
    session.commit.assert_not_called()


def test_stream_chat_msg_success_streams_and_persists(
    monkeypatch, session_builder, patch_db_session, chat_factory, message_factory
):
    chat = chat_factory(1)
    session = session_builder(chat=chat, messages=[], summary=None)
    patch_db_session(session)

    def fake_generate_response_stream(*, summary, messages):
        yield "Hel"
        yield "lo"

    def fake_create_message(db, chat_id, role, content, attached_files=None):
        return message_factory(99, chat_id=chat_id, role=role, content=content)

    monkeypatch.setattr(
        chat_module, "generate_response_stream", fake_generate_response_stream
    )
    monkeypatch.setattr(chat_module, "create_message", fake_create_message)

    events = list(chat_module.stream_chat_msg(chat_id=1, msg="hi"))

    assert any("event: chunk" in e and '"text": "Hel"' in e for e in events)
    assert any("event: chunk" in e and '"text": "lo"' in e for e in events)
    assert any("event: done" in e for e in events)
    assert session.commit.call_count >= 2


def test_stream_chat_msg_handles_llm_failure(
    monkeypatch, session_builder, patch_db_session, chat_factory
):
    chat = chat_factory(1)
    session = session_builder(chat=chat, messages=[], summary=None)
    patch_db_session(session)

    def broken_stream(*, summary, messages):
        raise RuntimeError("503 UNAVAILABLE")
        yield  # pragma: no cover

    monkeypatch.setattr(chat_module, "generate_response_stream", broken_stream)

    events = list(chat_module.stream_chat_msg(chat_id=1, msg="hi"))

    assert len(events) == 1
    assert "event: error" in events[0]
    assert "Failed to generate a response" in events[0]
    session.rollback.assert_called_once()


def test_stream_chat_msg_handles_empty_llm_response(
    monkeypatch, session_builder, patch_db_session, chat_factory
):
    chat = chat_factory(1)
    session = session_builder(chat=chat, messages=[], summary=None)
    patch_db_session(session)

    def empty_stream(*, summary, messages):
        yield "   "

    monkeypatch.setattr(chat_module, "generate_response_stream", empty_stream)

    events = list(chat_module.stream_chat_msg(chat_id=1, msg="hi"))

    assert any("event: error" in e for e in events)
    assert not any("event: done" in e for e in events)
    session.rollback.assert_called_once()


def test_stream_chat_msg_triggers_summarization(
    monkeypatch, session_builder, patch_db_session, chat_factory, message_factory
):
    chat = chat_factory(1)
    messages = [message_factory(i, content=f"msg-{i}") for i in range(20)]
    session = session_builder(chat=chat, messages=messages, summary=None)
    patch_db_session(session)

    summarize_calls = []

    def fake_generate_summary(*, existing_summary, messages):
        summarize_calls.append(messages)
        return "condensed summary"

    def fake_generate_response_stream(*, summary, messages):
        assert summary == "condensed summary"
        assert len(messages) == 8
        yield "ok"

    def fake_create_message(db, chat_id, role, content, attached_files=None):
        return message_factory(99, chat_id=chat_id, role=role, content=content)

    monkeypatch.setattr(chat_module, "generate_summary", fake_generate_summary)
    monkeypatch.setattr(
        chat_module, "generate_response_stream", fake_generate_response_stream
    )
    monkeypatch.setattr(chat_module, "create_message", fake_create_message)
    monkeypatch.setattr(chat_module, "embed_texts", lambda texts: [[0.1, 0.2, 0.3]])

    events = list(chat_module.stream_chat_msg(chat_id=1, msg="hi"))

    assert len(summarize_calls) == 1
    assert len(summarize_calls[0]) == 12
    assert any("event: done" in e for e in events)


def test_stream_chat_retry_errors_when_chat_missing(session_builder, patch_db_session):
    session = session_builder(chat=None)
    patch_db_session(session)

    events = list(chat_module.stream_chat_retry(chat_id=1))

    assert len(events) == 1
    assert "event: error" in events[0]
    assert "does not exist" in events[0]


def test_stream_chat_retry_errors_when_nothing_to_retry(
    session_builder, patch_db_session, chat_factory, message_factory
):
    chat = chat_factory(1)
    messages = [message_factory(1, role="assistant", content="already answered")]
    session = session_builder(chat=chat, messages=messages)
    patch_db_session(session)

    events = list(chat_module.stream_chat_retry(chat_id=1))

    assert len(events) == 1
    assert "event: error" in events[0]
    assert "Nothing to retry" in events[0]


def test_stream_chat_retry_success_does_not_create_user_message(
    monkeypatch, session_builder, patch_db_session, chat_factory, message_factory
):
    chat = chat_factory(1)
    messages = [message_factory(1, role="user", content="unanswered")]
    session = session_builder(chat=chat, messages=messages, summary=None)
    patch_db_session(session)

    create_message_calls = []

    def tracking_create_message(db, chat_id, role, content):
        create_message_calls.append(role)
        return message_factory(2, role=role, content=content)

    def fake_generate_response_stream(*, summary, messages):
        yield "a reply"

    monkeypatch.setattr(chat_module, "create_message", tracking_create_message)
    monkeypatch.setattr(
        chat_module, "generate_response_stream", fake_generate_response_stream
    )

    events = list(chat_module.stream_chat_retry(chat_id=1))

    assert create_message_calls == ["assistant"]
    assert any("event: done" in e for e in events)


def test_stream_chat_retry_handles_llm_failure(
    monkeypatch, session_builder, patch_db_session, chat_factory, message_factory
):
    chat = chat_factory(1)
    messages = [message_factory(1, role="user", content="unanswered")]
    session = session_builder(chat=chat, messages=messages, summary=None)
    patch_db_session(session)

    def broken_stream(*, summary, messages):
        raise RuntimeError("503 UNAVAILABLE")
        yield  # pragma: no cover

    monkeypatch.setattr(chat_module, "generate_response_stream", broken_stream)

    events = list(chat_module.stream_chat_retry(chat_id=1))

    assert len(events) == 1
    assert "event: error" in events[0]
    assert "Failed to generate a response" in events[0]
    session.rollback.assert_called_once()
