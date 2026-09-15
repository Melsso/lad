from contextlib import contextmanager

from lad.helpers import chat as chat_module
from lad.helpers.messages import sse_event_for_message


@contextmanager
def _fake_context(session):
    yield session


def test_create_and_get_chat_round_trip(db_session):
    created = chat_module.create_chat(db_session, title="Integration Chat")
    db_session.commit()

    fetched = chat_module.get_chat(db_session, chat_id=created.id)

    assert fetched is not None
    assert fetched.title == "Integration Chat"
    assert fetched.id == created.id
    assert fetched.created_at is not None


def test_get_chats_orders_by_created_at(db_session):
    first = chat_module.create_chat(db_session, title="First")
    second = chat_module.create_chat(db_session, title="Second")
    db_session.commit()

    result = chat_module.get_chats(db_session)

    assert [c.id for c in result][:2] == [first.id, second.id]


def test_create_message_and_get_chat_messages_ordering(db_session):
    chat = chat_module.create_chat(db_session, title="Chat")
    db_session.flush()

    chat_module.create_message(
        db_session, chat_id=chat.id, role="user", content="first"
    )
    chat_module.create_message(
        db_session, chat_id=chat.id, role="assistant", content="second"
    )
    db_session.commit()

    messages = chat_module.get_chat_messages(db_session, chat_id=chat.id)

    assert [m.content for m in messages] == ["first", "second"]


def test_update_chat_title_persists(db_session):
    chat = chat_module.create_chat(db_session, title="Old")
    db_session.commit()

    chat_module.update_chat_title(db_session, chat_id=chat.id, title="New")
    db_session.commit()

    fetched = chat_module.get_chat(db_session, chat_id=chat.id)

    assert fetched is not None
    assert fetched.title == "New"


def test_delete_chat_cascades_to_messages_and_summary(db_session):
    chat = chat_module.create_chat(db_session, title="To delete")
    db_session.flush()

    message = chat_module.create_message(
        db_session, chat_id=chat.id, role="user", content="hi"
    )
    db_session.flush()

    chat_module.save_chat_summary(
        db_session, chat_id=chat.id, content="summary", last_message_id=message.id
    )
    db_session.commit()

    deleted = chat_module.delete_chat(db_session, chat_id=chat.id)
    db_session.commit()

    assert deleted is True
    assert chat_module.get_chat(db_session, chat_id=chat.id) is None
    assert chat_module.get_chat_messages(db_session, chat_id=chat.id) == []
    assert chat_module.get_chat_summary(db_session, chat_id=chat.id) is None


def test_get_messages_after_summary_excludes_summarized_messages(db_session):
    chat = chat_module.create_chat(db_session, title="Chat")
    db_session.flush()

    chat_module.create_message(db_session, chat_id=chat.id, role="user", content="one")
    db_session.flush()
    m2 = chat_module.create_message(
        db_session, chat_id=chat.id, role="assistant", content="two"
    )
    db_session.flush()
    m3 = chat_module.create_message(
        db_session, chat_id=chat.id, role="user", content="three"
    )
    db_session.commit()

    chat_module.save_chat_summary(
        db_session, chat_id=chat.id, content="condensed", last_message_id=m2.id
    )
    db_session.commit()

    remaining = chat_module.get_messages_after_summary(
        db_session, chat_id=chat.id, last_message_id=m2.id
    )

    assert [m.id for m in remaining] == [m3.id]


def test_save_chat_summary_upserts_existing_summary(db_session):
    chat = chat_module.create_chat(db_session, title="Chat")
    db_session.flush()
    message = chat_module.create_message(
        db_session, chat_id=chat.id, role="user", content="hi"
    )
    db_session.commit()

    first = chat_module.save_chat_summary(
        db_session, chat_id=chat.id, content="first version", last_message_id=message.id
    )
    db_session.commit()

    second = chat_module.save_chat_summary(
        db_session,
        chat_id=chat.id,
        content="second version",
        last_message_id=message.id,
    )
    db_session.commit()

    assert first.id == second.id

    fetched = chat_module.get_chat_summary(db_session, chat_id=chat.id)

    assert fetched is not None
    assert fetched.content == "second version"


def test_stream_chat_msg_persists_user_and_assistant_messages(monkeypatch, db_session):
    chat = chat_module.create_chat(db_session, title="Chat")
    db_session.commit()

    monkeypatch.setattr(
        chat_module, "get_db_session", lambda: _fake_context(db_session)
    )

    def fake_run_chat_turn(db, chat_id, summary, active_messages):
        assistant_message = chat_module.create_message(
            db=db, chat_id=chat_id, role="assistant", content="Hello there"
        )
        db.commit()
        yield sse_event_for_message("done", assistant_message)

    monkeypatch.setattr(chat_module, "run_chat_turn", fake_run_chat_turn)

    events = list(chat_module.stream_chat_msg(chat_id=chat.id, msg="hi"))

    assert any("event: done" in e for e in events)

    messages = chat_module.get_chat_messages(db_session, chat_id=chat.id)

    assert [m.role for m in messages] == ["user", "assistant"]
    assert messages[0].content == "hi"
    assert messages[1].content == "Hello there"


def test_stream_chat_msg_keeps_user_message_when_llm_fails(monkeypatch, db_session):
    chat = chat_module.create_chat(db_session, title="Chat")
    db_session.commit()

    monkeypatch.setattr(
        chat_module, "get_db_session", lambda: _fake_context(db_session)
    )

    def broken_turn(db, chat_id, summary, active_messages):
        raise RuntimeError("503 UNAVAILABLE")
        yield  # pragma: no cover

    monkeypatch.setattr(chat_module, "run_chat_turn", broken_turn)

    events = list(chat_module.stream_chat_msg(chat_id=chat.id, msg="unanswered"))

    assert any("event: error" in e for e in events)

    messages = chat_module.get_chat_messages(db_session, chat_id=chat.id)

    assert len(messages) == 1
    assert messages[0].role == "user"
    assert messages[0].content == "unanswered"


def test_stream_chat_retry_generates_reply_for_dangling_user_message(
    monkeypatch, db_session
):
    chat = chat_module.create_chat(db_session, title="Chat")
    db_session.flush()
    chat_module.create_message(
        db_session, chat_id=chat.id, role="user", content="unanswered"
    )
    db_session.commit()

    monkeypatch.setattr(
        chat_module, "get_db_session", lambda: _fake_context(db_session)
    )

    def fake_run_chat_turn(db, chat_id, summary, active_messages):
        assistant_message = chat_module.create_message(
            db=db, chat_id=chat_id, role="assistant", content="a reply"
        )
        db.commit()
        yield sse_event_for_message("done", assistant_message)

    monkeypatch.setattr(chat_module, "run_chat_turn", fake_run_chat_turn)

    events = list(chat_module.stream_chat_retry(chat_id=chat.id))

    assert any("event: done" in e for e in events)

    messages = chat_module.get_chat_messages(db_session, chat_id=chat.id)

    assert len(messages) == 2
    assert messages[1].role == "assistant"
    assert messages[1].content == "a reply"


def test_stream_chat_msg_triggers_real_summarization(monkeypatch, db_session):
    chat = chat_module.create_chat(db_session, title="Chat")
    db_session.flush()

    for i in range(20):
        chat_module.create_message(
            db_session, chat_id=chat.id, role="user", content=f"msg-{i}"
        )
        db_session.flush()

    db_session.commit()

    monkeypatch.setattr(
        chat_module, "get_db_session", lambda: _fake_context(db_session)
    )

    def fake_generate_summary(*, existing_summary, messages):
        assert len(messages) == 13
        return "condensed summary"

    def fake_run_chat_turn(db, chat_id, summary, active_messages):
        assert summary == "condensed summary"
        assert len(active_messages) == 8
        assistant_message = chat_module.create_message(
            db=db, chat_id=chat_id, role="assistant", content="ok"
        )
        db.commit()
        yield sse_event_for_message("done", assistant_message)

    monkeypatch.setattr(chat_module, "generate_summary", fake_generate_summary)
    monkeypatch.setattr(chat_module, "run_chat_turn", fake_run_chat_turn)

    events = list(chat_module.stream_chat_msg(chat_id=chat.id, msg="one more"))

    assert any("event: done" in e for e in events)

    summary = chat_module.get_chat_summary(db_session, chat_id=chat.id)

    assert summary is not None
    assert summary.content == "condensed summary"
