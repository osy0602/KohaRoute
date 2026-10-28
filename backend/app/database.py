"""Database engine, session factory and the declarative base class.

Only SQLite is supported in the MVP, so SQLite-specific options are set here and nowhere else.
"""

import logging
from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, event, inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_config

logger = logging.getLogger(__name__)

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
    _recover_stranded_route_stops(selected_engine)


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
        # pysqlite does not open a transaction before DDL, so without this explicit BEGIN the
        # rename and CREATE TABLE below are committed one by one and a later failure cannot
        # be rolled back, leaving every saved stop stranded in route_stops_legacy.
        connection.exec_driver_sql("BEGIN")
        connection.exec_driver_sql("ALTER TABLE route_stops RENAME TO route_stops_legacy")
        # A renamed table keeps its indexes under their old names, which would make
        # table.create() fail with "index ix_route_stops_booking_id already exists".
        connection.exec_driver_sql("DROP INDEX IF EXISTS ix_route_stops_booking_id")
        table.create(connection)
        connection.exec_driver_sql(
            f"INSERT INTO route_stops ({quoted_columns}) "
            f"SELECT {quoted_columns} FROM route_stops_legacy"
        )
        connection.exec_driver_sql("DROP TABLE route_stops_legacy")


# A legacy stop is recoverable when its route and booking still exist and the live table does
# not already hold a stop for that route and booking.
_LEGACY_STOP_IS_RECOVERABLE = (
    "EXISTS (SELECT 1 FROM routes r WHERE r.id = l.route_id) "
    "AND EXISTS (SELECT 1 FROM bookings b WHERE b.id = l.booking_id) "
    "AND NOT EXISTS (SELECT 1 FROM route_stops s "
    "WHERE s.route_id = l.route_id AND s.booking_id = l.booking_id)"
)
_LEGACY_UPDATER_OR_NULL = (
    "CASE WHEN EXISTS (SELECT 1 FROM users u WHERE u.id = l.updated_by_user_id) "
    "THEN l.updated_by_user_id END"
)


def _recovery_sql(copy_columns: list[str], quote) -> str:
    """Build the INSERT that copies recoverable stops out of route_stops_legacy.

    ``id`` is left out so the live table assigns fresh ids (nothing references a stop id),
    which avoids clashes with stops created since the failed migration.
    """
    targets = ", ".join(quote(name) for name in copy_columns)
    values = ", ".join(
        _LEGACY_UPDATER_OR_NULL if name == "updated_by_user_id" else f"l.{quote(name)}"
        for name in copy_columns
    )
    return (
        f"INSERT OR IGNORE INTO route_stops ({targets}) "
        f"SELECT {values} FROM route_stops_legacy l "
        f"WHERE {_LEGACY_STOP_IS_RECOVERABLE} ORDER BY l.route_id, l.sequence"
    )


def _recover_stranded_route_stops(target_engine: Engine) -> None:
    """Put stops back that an interrupted route_stops migration left in route_stops_legacy.

    Earlier versions renamed route_stops, created a new one, then failed creating its index
    and could not roll back. Drivers then saw routes with no stops. This copies those stops
    back, restores the index, and drops the legacy table only once nothing recoverable is
    left in it. It does nothing on a healthy database.
    """
    inspector = inspect(target_engine)
    tables = set(inspector.get_table_names())
    if not {"route_stops", "route_stops_legacy", "routes", "bookings", "users"} <= tables:
        return

    from app.models.route_stop import RouteStop

    legacy_columns = {column["name"] for column in inspector.get_columns("route_stops_legacy")}
    copy_columns = [
        column.name
        for column in RouteStop.__table__.columns
        if column.name != "id" and column.name in legacy_columns
    ]
    if not {"route_id", "booking_id", "sequence", "status", "created_at"} <= set(copy_columns):
        logger.warning("route_stops_legacy is missing required columns; leaving it untouched.")
        return

    quote = target_engine.dialect.identifier_preparer.quote
    with target_engine.begin() as connection:
        connection.exec_driver_sql("BEGIN")
        # The legacy table may still own this index name (and would take it with it when
        # dropped), so release it before creating the live table's own index.
        connection.exec_driver_sql("DROP INDEX IF EXISTS ix_route_stops_booking_id")
        connection.exec_driver_sql(
            "CREATE INDEX ix_route_stops_booking_id ON route_stops (booking_id)"
        )
        connection.exec_driver_sql(_recovery_sql(copy_columns, quote))
        left_behind = connection.exec_driver_sql(
            f"SELECT COUNT(*) FROM route_stops_legacy l WHERE {_LEGACY_STOP_IS_RECOVERABLE}"
        ).scalar()
        if left_behind:
            logger.warning(
                "%s stop(s) in route_stops_legacy could not be restored; table kept.", left_behind
            )
            return
        connection.exec_driver_sql("DROP TABLE route_stops_legacy")
    logger.info("Recovered route stops from route_stops_legacy.")


def drop_tables(target_engine: Engine | None = None) -> None:
    """Delete every table and all its data (used only by ``python -m app.seed --reset``).

    Args:
        target_engine: Engine to drop the tables from. Defaults to the application engine.
    """
    from app import models  # noqa: F401

    Base.metadata.drop_all(bind=target_engine or engine)
