import os
import warnings

import pytest
import pytest_asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

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
def database_url(postgres_container) -> str:
    from lad.models.db import Base

    url = postgres_container.get_connection_url()

    sync_engine = create_engine(url)
    with sync_engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    return url


@pytest_asyncio.fixture
async def db_session(database_url):
    engine = create_async_engine(database_url, poolclass=NullPool)

    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )

        yield session

        await session.close()
        await transaction.rollback()

    await engine.dispose()


@pytest.fixture(autouse=True)
def _fake_embeddings(monkeypatch):
    from lad.helpers import chat as chat_module
    from lad.schemas.config import conf

    async def fake_embed_texts(texts):
        return [[0.0] * conf.EMBEDDING_DIM for _ in texts]

    monkeypatch.setattr(chat_module, "embed_texts", fake_embed_texts)
