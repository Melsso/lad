import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from lad.core import db as db_module


class TrackedSession(AsyncSession):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.close_calls = 0

    async def close(self):
        self.close_calls += 1
        await super().close()


def _close_calls(session) -> int:
    return session.close_calls


@pytest_asyncio.fixture
async def async_engine(database_url):
    engine = create_async_engine(database_url, poolclass=NullPool)

    yield engine

    await engine.dispose()


def _tracked_factory(engine):
    return async_sessionmaker(bind=engine, class_=TrackedSession)


def _point_conf_at_container(monkeypatch, postgres_container):
    monkeypatch.setattr(db_module.conf, "DB_USER", postgres_container.username)
    monkeypatch.setattr(db_module.conf, "DB_PASSWORD", postgres_container.password)
    monkeypatch.setattr(db_module.conf, "DB_NAME", postgres_container.dbname)
    monkeypatch.setattr(
        db_module.conf, "DB_HOST", postgres_container.get_container_host_ip()
    )
    monkeypatch.setattr(
        db_module.conf,
        "DB_PORT",
        int(postgres_container.get_exposed_port(postgres_container.port)),
    )


async def test_init_db_connects_and_sets_up_session_factory(
    monkeypatch, postgres_container
):
    _point_conf_at_container(monkeypatch, postgres_container)
    monkeypatch.setattr(db_module, "engine", None)
    monkeypatch.setattr(db_module, "SessionLocal", None)

    await db_module.init_db()

    try:
        assert db_module.engine is not None
        assert db_module.SessionLocal is not None

        async with db_module.SessionLocal() as session:
            assert (await session.execute(text("SELECT 1"))).scalar() == 1
    finally:
        await db_module.dispose_db()


async def test_init_db_retries_on_failure_then_succeeds(
    monkeypatch, postgres_container
):
    _point_conf_at_container(monkeypatch, postgres_container)
    monkeypatch.setattr(db_module, "engine", None)
    monkeypatch.setattr(db_module, "SessionLocal", None)
    monkeypatch.setattr(db_module, "RETRY_DELAY_SECONDS", 0)

    real_prepare_schema = db_module._prepare_schema
    attempts = {"count": 0}

    async def flaky_prepare_schema(db_engine):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise SQLAlchemyError("simulated connection failure")
        await real_prepare_schema(db_engine)

    monkeypatch.setattr(db_module, "_prepare_schema", flaky_prepare_schema)

    await db_module.init_db()

    try:
        assert attempts["count"] == 2
        assert db_module.engine is not None
        assert db_module.SessionLocal is not None
    finally:
        await db_module.dispose_db()


async def test_session_factory_stays_unset_until_init_succeeds(
    monkeypatch, postgres_container
):
    _point_conf_at_container(monkeypatch, postgres_container)
    monkeypatch.setattr(db_module, "engine", None)
    monkeypatch.setattr(db_module, "SessionLocal", None)
    monkeypatch.setattr(db_module, "RETRY_DELAY_SECONDS", 0)

    observed = []
    real_prepare_schema = db_module._prepare_schema

    async def observing_prepare_schema(db_engine):
        observed.append(db_module.SessionLocal)
        await real_prepare_schema(db_engine)

    monkeypatch.setattr(db_module, "_prepare_schema", observing_prepare_schema)

    await db_module.init_db()

    try:
        assert observed == [None]
        assert db_module.SessionLocal is not None
    finally:
        await db_module.dispose_db()


async def test_get_db_raises_when_uninitialized(monkeypatch):
    monkeypatch.setattr(db_module, "SessionLocal", None)

    generator = db_module.get_db()

    with pytest.raises(HTTPException) as exc_info:
        await anext(generator)

    assert exc_info.value.status_code == 503


async def test_get_db_yields_a_working_session_and_closes_it(monkeypatch, async_engine):
    monkeypatch.setattr(db_module, "SessionLocal", _tracked_factory(async_engine))

    generator = db_module.get_db()
    session = await anext(generator)

    assert (await session.execute(text("SELECT 1"))).scalar() == 1
    assert _close_calls(session) == 0

    with pytest.raises(StopAsyncIteration):
        await anext(generator)

    assert _close_calls(session) == 1


async def test_get_db_closes_the_session_even_if_the_caller_raises(
    monkeypatch, async_engine
):
    monkeypatch.setattr(db_module, "SessionLocal", _tracked_factory(async_engine))

    generator = db_module.get_db()
    session = await anext(generator)

    with pytest.raises(ValueError):
        await generator.athrow(ValueError("simulated route error"))

    assert _close_calls(session) == 1


async def test_get_db_session_raises_when_uninitialized(monkeypatch):
    monkeypatch.setattr(db_module, "SessionLocal", None)

    with pytest.raises(RuntimeError, match="not initialized"):
        async with db_module.get_db_session():
            pass


async def test_get_db_session_yields_a_working_session_and_closes_it(
    monkeypatch, async_engine
):
    monkeypatch.setattr(db_module, "SessionLocal", _tracked_factory(async_engine))

    async with db_module.get_db_session() as session:
        assert (await session.execute(text("SELECT 1"))).scalar() == 1
        assert _close_calls(session) == 0

    assert _close_calls(session) == 1


async def test_get_db_session_closes_even_when_the_body_raises(
    monkeypatch, async_engine
):
    monkeypatch.setattr(db_module, "SessionLocal", _tracked_factory(async_engine))

    captured = {}

    with pytest.raises(ValueError):
        async with db_module.get_db_session() as session:
            captured["session"] = session
            raise ValueError("boom")

    assert _close_calls(captured["session"]) == 1
