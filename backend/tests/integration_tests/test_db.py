import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from lad.core import db as db_module


class TrackedSession(Session):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.close_calls = 0

    def close(self):
        self.close_calls += 1
        super().close()


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


def test_init_db_connects_and_sets_up_session_factory(monkeypatch, postgres_container):
    _point_conf_at_container(monkeypatch, postgres_container)
    monkeypatch.setattr(db_module, "engine", None)
    monkeypatch.setattr(db_module, "SessionLocal", None)

    db_module.init_db()

    try:
        assert db_module.engine is not None
        assert db_module.SessionLocal is not None

        session = db_module.SessionLocal()
        try:
            assert session.execute(text("SELECT 1")).scalar() == 1
        finally:
            session.close()
    finally:
        if db_module.engine is not None:
            db_module.engine.dispose()


def test_init_db_retries_on_failure_then_succeeds(monkeypatch, postgres_container):
    _point_conf_at_container(monkeypatch, postgres_container)
    monkeypatch.setattr(db_module, "engine", None)
    monkeypatch.setattr(db_module, "SessionLocal", None)

    sleep_calls = []
    monkeypatch.setattr(
        db_module.time, "sleep", lambda seconds: sleep_calls.append(seconds)
    )

    real_create_engine = db_module.create_engine
    attempts = {"count": 0}

    def flaky_create_engine(url, echo=False):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise SQLAlchemyError("simulated connection failure")
        return real_create_engine(url, echo=echo)

    monkeypatch.setattr(db_module, "create_engine", flaky_create_engine)

    db_module.init_db()

    try:
        assert attempts["count"] == 2
        assert sleep_calls == [30]
        assert db_module.engine is not None
        assert db_module.SessionLocal is not None
    finally:
        if db_module.engine is not None:
            db_module.engine.dispose()


def test_get_db_raises_when_uninitialized(monkeypatch):
    monkeypatch.setattr(db_module, "SessionLocal", None)

    generator = db_module.get_db()

    with pytest.raises(RuntimeError, match="not initialized"):
        next(generator)


def test_get_db_yields_a_working_session_and_closes_it(monkeypatch, postgres_engine):
    monkeypatch.setattr(
        db_module,
        "SessionLocal",
        sessionmaker(bind=postgres_engine, class_=TrackedSession),
    )

    generator = db_module.get_db()
    session = next(generator)

    assert session.execute(text("SELECT 1")).scalar() == 1
    assert session.close_calls == 0

    with pytest.raises(StopIteration):
        next(generator)

    assert session.close_calls == 1


def test_get_db_closes_the_session_even_if_the_caller_raises(
    monkeypatch, postgres_engine
):
    monkeypatch.setattr(
        db_module,
        "SessionLocal",
        sessionmaker(bind=postgres_engine, class_=TrackedSession),
    )

    generator = db_module.get_db()
    session = next(generator)

    with pytest.raises(ValueError):
        generator.throw(ValueError("simulated route error"))

    assert session.close_calls == 1


def test_get_db_session_raises_when_uninitialized(monkeypatch):
    monkeypatch.setattr(db_module, "SessionLocal", None)

    with (
        pytest.raises(RuntimeError, match="not initialized"),
        db_module.get_db_session(),
    ):
        pass


def test_get_db_session_yields_a_working_session_and_closes_it(
    monkeypatch, postgres_engine
):
    monkeypatch.setattr(
        db_module,
        "SessionLocal",
        sessionmaker(bind=postgres_engine, class_=TrackedSession),
    )

    with db_module.get_db_session() as session:
        assert session.execute(text("SELECT 1")).scalar() == 1
        assert session.close_calls == 0

    assert session.close_calls == 1


def test_get_db_session_closes_even_when_the_body_raises(monkeypatch, postgres_engine):
    monkeypatch.setattr(
        db_module,
        "SessionLocal",
        sessionmaker(bind=postgres_engine, class_=TrackedSession),
    )

    captured = {}

    with pytest.raises(ValueError), db_module.get_db_session() as session:
        captured["session"] = session
        raise ValueError("boom")

    assert captured["session"].close_calls == 1
