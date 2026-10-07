import asyncio
import logging
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from lad.models.db import Base
from lad.schemas.config import conf

logger = logging.getLogger("Lad")

RETRY_DELAY_SECONDS = 30

engine: AsyncEngine | None = None
SessionLocal: async_sessionmaker[AsyncSession] | None = None


def _build_database_url() -> str:
    return (
        f"postgresql+psycopg://{conf.DB_USER}:{conf.DB_PASSWORD}"
        f"@{conf.DB_HOST}:{conf.DB_PORT}/{conf.DB_NAME}"
    )


def _build_engine() -> AsyncEngine:
    return create_async_engine(_build_database_url(), echo=False)


def _build_session_factory(db_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)


def connect_db() -> None:
    global engine, SessionLocal

    engine = _build_engine()
    SessionLocal = _build_session_factory(engine)


async def _prepare_schema(db_engine: AsyncEngine) -> None:
    async with db_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)


async def init_db() -> None:
    global engine, SessionLocal

    while True:
        candidate = _build_engine()

        logger.info(
            "lad_event",
            extra={
                "event": "db_init",
                "status": "starting",
                "context": {"location": "init_db"},
            },
        )

        try:
            await _prepare_schema(candidate)
        except SQLAlchemyError as exc:
            logger.error(
                "lad_event",
                extra={
                    "event": "db_init",
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "context": {"location": "init_db"},
                },
            )
            await candidate.dispose()
            await asyncio.sleep(RETRY_DELAY_SECONDS)
            continue

        engine = candidate
        SessionLocal = _build_session_factory(candidate)

        logger.info(
            "lad_event",
            extra={
                "event": "db_init",
                "status": "success",
                "context": {"location": "init_db"},
            },
        )
        return


async def dispose_db() -> None:
    if engine is not None:
        await engine.dispose()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    if SessionLocal is None:
        raise RuntimeError("DB not initialized yet")

    async with SessionLocal() as db:
        yield db


@asynccontextmanager
async def get_db_session() -> AsyncIterator[AsyncSession]:
    if SessionLocal is None:
        raise RuntimeError("DB not initialized yet")

    async with SessionLocal() as db:
        yield db
