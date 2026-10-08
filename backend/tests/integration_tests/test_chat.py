from contextlib import asynccontextmanager

from lad.helpers import chat as chat_module
from lad.helpers.messages import sse_event_for_message
from lad.schemas.config import conf


@asynccontextmanager
async def _fake_context(session):
    yield session


async def _collect(generator) -> list[str]:
    return [event async for event in generator]


async def test_create_and_get_chat_round_trip(db_session):
    created = await chat_module.create_chat(db_session, title="Integration Chat")
    await db_session.commit()
    db_session.expunge_all()

    fetched = await chat_module.get_chat(db_session, chat_id=created.id)

    assert fetched is not None
    assert fetched.title == "Integration Chat"
    assert fetched.id == created.id
    assert fetched.created_at is not None


async def test_get_chats_orders_by_created_at(db_session):
    first = await chat_module.create_chat(db_session, title="First")
    second = await chat_module.create_chat(db_session, title="Second")
    await db_session.commit()

    result = await chat_module.get_chats(db_session)

    assert [c.id for c in result][:2] == [first.id, second.id]


async def test_create_message_and_get_chat_messages_ordering(db_session):
    chat = await chat_module.create_chat(db_session, title="Chat")

    await chat_module.create_message(
        db_session, chat_id=chat.id, role="user", content="first"
    )
    await chat_module.create_message(
        db_session, chat_id=chat.id, role="assistant", content="second"
    )
    await db_session.commit()

    messages = await chat_module.get_chat_messages(db_session, chat_id=chat.id)

    assert [m.content for m in messages] == ["first", "second"]


async def test_update_chat_title_persists(db_session):
    chat = await chat_module.create_chat(db_session, title="Old")
    await db_session.commit()

    await chat_module.update_chat_title(db_session, chat_id=chat.id, title="New")
    await db_session.commit()
    db_session.expunge_all()

    fetched = await chat_module.get_chat(db_session, chat_id=chat.id)

    assert fetched is not None
    assert fetched.title == "New"


async def test_delete_chat_cascades_to_messages_and_summary(db_session):
    chat = await chat_module.create_chat(db_session, title="To delete")
    message = await chat_module.create_message(
        db_session, chat_id=chat.id, role="user", content="hi"
    )
    await chat_module.save_chat_summary(
        db_session, chat_id=chat.id, content="summary", last_message_id=message.id
    )
    await db_session.commit()

    chat_id = chat.id
    deleted = await chat_module.delete_chat(db_session, chat_id=chat_id)
    await db_session.commit()
    db_session.expunge_all()

    assert deleted is True
    assert await chat_module.get_chat(db_session, chat_id=chat_id) is None
    assert await chat_module.get_chat_messages(db_session, chat_id=chat_id) == []
    assert await chat_module.get_chat_summary(db_session, chat_id=chat_id) is None


async def test_get_messages_after_summary_excludes_summarized_messages(db_session):
    chat = await chat_module.create_chat(db_session, title="Chat")

    await chat_module.create_message(
        db_session, chat_id=chat.id, role="user", content="one"
    )
    m2 = await chat_module.create_message(
        db_session, chat_id=chat.id, role="assistant", content="two"
    )
    m3 = await chat_module.create_message(
        db_session, chat_id=chat.id, role="user", content="three"
    )
    await db_session.commit()

    await chat_module.save_chat_summary(
        db_session, chat_id=chat.id, content="condensed", last_message_id=m2.id
    )
    await db_session.commit()

    remaining = await chat_module.get_messages_after_summary(
        db_session, chat_id=chat.id, last_message_id=m2.id
    )

    assert [m.id for m in remaining] == [m3.id]


async def test_get_messages_after_summary_without_last_id_returns_everything(
    db_session,
):
    chat = await chat_module.create_chat(db_session, title="Chat")

    m1 = await chat_module.create_message(
        db_session, chat_id=chat.id, role="user", content="one"
    )
    m2 = await chat_module.create_message(
        db_session, chat_id=chat.id, role="assistant", content="two"
    )
    await db_session.commit()

    result = await chat_module.get_messages_after_summary(
        db_session, chat_id=chat.id, last_message_id=None
    )

    assert [m.id for m in result] == [m1.id, m2.id]


async def test_save_chat_summary_upserts_existing_summary(db_session):
    chat = await chat_module.create_chat(db_session, title="Chat")
    message = await chat_module.create_message(
        db_session, chat_id=chat.id, role="user", content="hi"
    )
    await db_session.commit()

    first = await chat_module.save_chat_summary(
        db_session,
        chat_id=chat.id,
        content="first version",
        last_message_id=message.id,
    )
    await db_session.commit()

    second = await chat_module.save_chat_summary(
        db_session,
        chat_id=chat.id,
        content="second version",
        last_message_id=message.id,
    )
    await db_session.commit()
    db_session.expunge_all()

    assert first.id == second.id

    fetched = await chat_module.get_chat_summary(db_session, chat_id=chat.id)

    assert fetched is not None
    assert fetched.content == "second version"


async def test_stream_chat_msg_persists_user_and_assistant_messages(
    monkeypatch, db_session
):
    chat = await chat_module.create_chat(db_session, title="Chat")
    await db_session.commit()

    monkeypatch.setattr(
        chat_module, "get_db_session", lambda: _fake_context(db_session)
    )

    async def fake_run_chat_turn(db, chat_id, summary, active_messages):
        assistant_message = await chat_module.create_message(
            db=db, chat_id=chat_id, role="assistant", content="Hello there"
        )
        await db.commit()
        yield sse_event_for_message("done", assistant_message)

    monkeypatch.setattr(chat_module, "run_chat_turn", fake_run_chat_turn)

    events = await _collect(chat_module.stream_chat_msg(chat_id=chat.id, msg="hi"))

    assert any("event: done" in e for e in events)

    messages = await chat_module.get_chat_messages(db_session, chat_id=chat.id)

    assert [m.role for m in messages] == ["user", "assistant"]
    assert messages[0].content == "hi"
    assert messages[1].content == "Hello there"


async def test_stream_chat_msg_keeps_user_message_when_llm_fails(
    monkeypatch, db_session
):
    chat = await chat_module.create_chat(db_session, title="Chat")
    await db_session.commit()

    monkeypatch.setattr(
        chat_module, "get_db_session", lambda: _fake_context(db_session)
    )

    async def broken_turn(db, chat_id, summary, active_messages):
        raise RuntimeError("503 UNAVAILABLE")
        yield  # pragma: no cover

    monkeypatch.setattr(chat_module, "run_chat_turn", broken_turn)

    events = await _collect(
        chat_module.stream_chat_msg(chat_id=chat.id, msg="unanswered")
    )

    assert any("event: error" in e for e in events)

    messages = await chat_module.get_chat_messages(db_session, chat_id=chat.id)

    assert len(messages) == 1
    assert messages[0].role == "user"
    assert messages[0].content == "unanswered"


async def test_stream_chat_retry_generates_reply_for_dangling_user_message(
    monkeypatch, db_session
):
    chat = await chat_module.create_chat(db_session, title="Chat")
    await chat_module.create_message(
        db_session, chat_id=chat.id, role="user", content="unanswered"
    )
    await db_session.commit()

    monkeypatch.setattr(
        chat_module, "get_db_session", lambda: _fake_context(db_session)
    )

    async def fake_run_chat_turn(db, chat_id, summary, active_messages):
        assistant_message = await chat_module.create_message(
            db=db, chat_id=chat_id, role="assistant", content="a reply"
        )
        await db.commit()
        yield sse_event_for_message("done", assistant_message)

    monkeypatch.setattr(chat_module, "run_chat_turn", fake_run_chat_turn)

    events = await _collect(chat_module.stream_chat_retry(chat_id=chat.id))

    assert any("event: done" in e for e in events)

    messages = await chat_module.get_chat_messages(db_session, chat_id=chat.id)

    assert len(messages) == 2
    assert messages[1].role == "assistant"
    assert messages[1].content == "a reply"


async def test_stream_chat_msg_triggers_real_summarization(monkeypatch, db_session):
    threshold = conf.SUMMARY_THRESHOLD
    keep = conf.RECENT_MESSAGES_TO_KEEP

    chat = await chat_module.create_chat(db_session, title="Chat")

    for i in range(threshold):
        await chat_module.create_message(
            db_session, chat_id=chat.id, role="user", content=f"msg-{i}"
        )

    await db_session.commit()

    monkeypatch.setattr(
        chat_module, "get_db_session", lambda: _fake_context(db_session)
    )

    async def fake_generate_summary(*, existing_summary, messages, model=None):
        assert len(messages) == threshold + 1 - keep
        return "condensed summary"

    async def fake_run_chat_turn(db, chat_id, summary, active_messages):
        assert summary == "condensed summary"
        assert len(active_messages) == keep
        assistant_message = await chat_module.create_message(
            db=db, chat_id=chat_id, role="assistant", content="ok"
        )
        await db.commit()
        yield sse_event_for_message("done", assistant_message)

    monkeypatch.setattr(chat_module, "generate_summary", fake_generate_summary)
    monkeypatch.setattr(chat_module, "run_chat_turn", fake_run_chat_turn)

    events = await _collect(
        chat_module.stream_chat_msg(chat_id=chat.id, msg="one more")
    )

    assert any("event: done" in e for e in events)

    summary = await chat_module.get_chat_summary(db_session, chat_id=chat.id)

    assert summary is not None
    assert summary.content == "condensed summary"
