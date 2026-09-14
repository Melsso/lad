import os
import warnings

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("MCP_SERVERS", "[]")

warnings.filterwarnings("ignore", category=DeprecationWarning, module="testcontainers")


@pytest.fixture(scope="session")
def postgres_container():
    from testcontainers.community.postgres import PostgresContainer

    with PostgresContainer("pgvector/pgvector:pg16", driver="psycopg") as container:
        yield container


@pytest.fixture(scope="session")
def postgres_engine(postgres_container):
    from lad.models.db import Base

    engine = create_engine(postgres_container.get_connection_url())

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    Base.metadata.create_all(engine)

    yield engine

    engine.dispose()


@pytest.fixture()
def db_session(postgres_engine):
    connection = postgres_engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(
        bind=connection, join_transaction_mode="create_savepoint"
    )
    session = session_factory()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(autouse=True)
def _fake_embeddings(monkeypatch):
    from lad.helpers import chat as chat_module
    from lad.schemas.config import conf

    def fake_embed_texts(texts):
        return [[0.0] * conf.EMBEDDING_DIM for _ in texts]

    monkeypatch.setattr(chat_module, "embed_texts", fake_embed_texts)
