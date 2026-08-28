import logging
import time
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from lad.models.db import Base
from lad.schemas.config import conf

logger = logging.getLogger("Lad")

engine = None
SessionLocal = None


def init_db():
    global engine, SessionLocal

    while True:
        try:
            logger.info(
                "lad_event",
                extra={
                    "event": "db_init",
                    "status": "starting",
                    "context": {"location": "init_db"},
                },
            )
            DATABASE_URL = (
                f"postgresql+psycopg://{conf.DB_USER}:{conf.DB_PASSWORD}"
                f"@{conf.DB_HOST}:{conf.DB_PORT}/{conf.DB_NAME}"
            )
            engine = create_engine(DATABASE_URL, echo=False)

            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            Base.metadata.create_all(bind=engine)
            SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

            logger.info(
                "lad_event",
                extra={
                    "event": "db_init",
                    "status": "success",
                    "context": {"location": "init_db"},
                },
            )
            break

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
            time.sleep(30)


def get_db():
    if SessionLocal is None:
        raise RuntimeError("DB not initialized yet")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session():
    if SessionLocal is None:
        raise RuntimeError("DB not initialized yet")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
