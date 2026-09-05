import os
import warnings

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("DB_HOST", "localhost")

warnings.filterwarnings("ignore", category=DeprecationWarning, module="testcontainers")


@pytest.fixture(scope="session")
def postgres_container():
    from testcontainers.community.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine", driver="psycopg") as container:
        yield container


@pytest.fixture(scope="session")
def postgres_engine(postgres_container):
    from lad.models.db import Base

    engine = create_engine(postgres_container.get_connection_url())
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
