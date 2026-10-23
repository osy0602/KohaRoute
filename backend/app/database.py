"""Database engine, session factory and the declarative base class.

Only SQLite is supported in the MVP, so SQLite-specific options are set here and nowhere else.
"""

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_config

IN_MEMORY_URLS = ("sqlite://", "sqlite:///:memory:")


class Base(DeclarativeBase):
    """Parent class of every ORM model (the models themselves arrive in Part 1)."""


def _configure_sqlite_connection(dbapi_connection, _connection_record) -> None:
    """Apply per-connection SQLite settings.

    SQLite ignores foreign keys unless switched on for each connection. Write-ahead logging
    lets the live map read while a driver's update is being written.
    """
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
    finally:
        cursor.close()


def create_db_engine(database_url: str) -> Engine:
    """Build a SQLAlchemy engine for a SQLite URL.

    Args:
        database_url: A ``sqlite:///...`` URL, or ``sqlite://`` for a throwaway in-memory
            database (used by tests).

    Returns:
        A configured engine. An in-memory database gets a single shared connection,
        otherwise each new connection would see its own empty database.
    """
    engine_options: dict = {"connect_args": {"check_same_thread": False}}
    if database_url in IN_MEMORY_URLS:
        engine_options["poolclass"] = StaticPool
    engine = create_engine(database_url, **engine_options)
    event.listen(engine, "connect", _configure_sqlite_connection)
    return engine


engine = create_db_engine(get_config().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency that gives each request its own session and always closes it.

    Yields:
        A database session bound to the application engine.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
