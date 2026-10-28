"""Database engine, session factory and the declarative base class.

Only SQLite is supported in the MVP, so SQLite-specific options are set here and nowhere else.
"""

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, event, inspect
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


def create_tables(target_engine: Engine | None = None) -> None:
    """Create every table that does not exist yet (safe to run repeatedly).

    Args:
        target_engine: Engine to create the tables in. Defaults to the application engine.
    """
    # Imported here, not at the top: the models import ``Base`` from this module, so a
    # top-level import would be circular. Importing them is what registers their tables.
    from app import models  # noqa: F401

    selected_engine = target_engine or engine
    Base.metadata.create_all(bind=selected_engine)
    _allow_rescheduled_bookings_in_routes(selected_engine)


def _allow_rescheduled_bookings_in_routes(target_engine: Engine) -> None:
    """Migrate the earlier route-stop uniqueness rule without dropping saved stop data.

    Part 7 initially allowed each booking only one RouteStop ever. A Missed booking can be
    rescheduled and routed again, so historical stops must be allowed while each route still
    prevents duplicate stops for the same booking.
    """
    inspector = inspect(target_engine)
    if "route_stops" not in inspector.get_table_names():
        return
    unique_constraints = inspector.get_unique_constraints("route_stops")
    has_legacy_unique_booking = any(
        set(constraint.get("column_names") or ()) == {"booking_id"}
        for constraint in unique_constraints
    )
    if not has_legacy_unique_booking:
        return

    from app.models.route_stop import RouteStop

    table = RouteStop.__table__
    column_names = [column.name for column in table.columns]
    quoted_columns = ", ".join(
        target_engine.dialect.identifier_preparer.quote(name) for name in column_names
    )
    with target_engine.begin() as connection:
        connection.exec_driver_sql("ALTER TABLE route_stops RENAME TO route_stops_legacy")
        table.create(connection)
        connection.exec_driver_sql(
            f"INSERT INTO route_stops ({quoted_columns}) "
            f"SELECT {quoted_columns} FROM route_stops_legacy"
        )
        connection.exec_driver_sql("DROP TABLE route_stops_legacy")


def drop_tables(target_engine: Engine | None = None) -> None:
    """Delete every table and all its data (used only by ``python -m app.seed --reset``).

    Args:
        target_engine: Engine to drop the tables from. Defaults to the application engine.
    """
    from app import models  # noqa: F401

    Base.metadata.drop_all(bind=target_engine or engine)
