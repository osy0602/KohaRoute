"""Saved route stops must survive the route_stops schema migration (US-06, US-10).

An earlier migration renamed route_stops, then failed creating the index (the old table kept
the index name) and could not roll back. Routes were left with no stops, so the driver page
showed a route line on the map but no stops. These tests lock in the fix and the recovery.
"""

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import sessionmaker

from app.database import Base, create_db_engine, create_tables
from app.models import Booking, BookingStatus, Route, User, UserRole, Vehicle
from app.timeutil import today_nz

# The route_stops table as it was before "one stop per booking ever" was relaxed.
OLD_ROUTE_STOPS_DDL = """
CREATE TABLE {name} (
    id INTEGER NOT NULL,
    route_id INTEGER NOT NULL,
    booking_id INTEGER NOT NULL,
    sequence INTEGER NOT NULL,
    status VARCHAR(16) NOT NULL,
    remark TEXT,
    completed_at DATETIME,
    updated_by_user_id INTEGER,
    created_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_route_stops_route_sequence UNIQUE (route_id, sequence),
    CONSTRAINT uq_route_stops_booking UNIQUE (booking_id),
    FOREIGN KEY(route_id) REFERENCES routes (id) ON DELETE CASCADE,
    FOREIGN KEY(booking_id) REFERENCES bookings (id) ON DELETE RESTRICT,
    FOREIGN KEY(updated_by_user_id) REFERENCES users (id) ON DELETE SET NULL
)
"""
INSERT_STOP = (
    "INSERT INTO {table} (route_id, booking_id, sequence, status, created_at) "
    "VALUES (?, ?, ?, 'scheduled', '2026-10-15 20:00:00')"
)


@pytest.fixture()
def database(tmp_path):
    """A file database with the current schema plus one driver, one route and two bookings."""
    engine = create_db_engine(f"sqlite:///{tmp_path / 'koha.db'}")
    Base.metadata.create_all(bind=engine)
    with sessionmaker(bind=engine, expire_on_commit=False)() as session:
        driver = User(
            email="driver@koha.nz",
            password_hash="unused",
            full_name="Driver",
            role=UserRole.DRIVER,
            is_active=True,
        )
        vehicle = Vehicle(
            name="Van", plate_number="KOHA01", capacity_kg=600, capacity_litres=3000, is_active=True
        )
        session.add_all([driver, vehicle])
        session.flush()
        bookings = [
            Booking(
                reference=f"KR-MIG-00{number}",
                donor_name=f"Donor {number}",
                contact_number="021 555 000" + str(number),
                address_text=f"{number} Sample Road, Auckland",
                latitude=-36.8,
                longitude=174.6,
                pickup_date=today_nz(),
                size="Medium",
                quantity=1,
                estimated_weight_kg=10,
                estimated_volume_l=20,
                status=BookingStatus.SCHEDULED,
            )
            for number in (1, 2)
        ]
        session.add_all(bookings)
        route = Route(
            pickup_date=today_nz(),
            driver_id=driver.id,
            vehicle_id=vehicle.id,
            vehicle_name="Van",
            vehicle_plate_number="KOHA01",
            vehicle_capacity_kg=600,
            vehicle_capacity_litres=3000,
            total_distance_m=1000,
            total_duration_s=600,
            planned_weight_kg=20,
            planned_volume_l=40,
            geometry="",
            color="#247BA0",
        )
        session.add(route)
        session.commit()
        ids = {"route": route.id, "bookings": [booking.id for booking in bookings]}
    yield engine, ids
    engine.dispose()


def _add_stops(engine, table, route_id, booking_ids_with_sequence):
    with engine.begin() as connection:
        for booking_id, sequence in booking_ids_with_sequence:
            connection.exec_driver_sql(
                INSERT_STOP.format(table=table), (route_id, booking_id, sequence)
            )


def _live_stops(engine):
    with engine.connect() as connection:
        rows = connection.exec_driver_sql(
            "SELECT route_id, booking_id, sequence FROM route_stops ORDER BY route_id, sequence"
        ).fetchall()
    return [tuple(row) for row in rows]


def _use_old_route_stops_schema(engine):
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE route_stops")
        connection.exec_driver_sql(OLD_ROUTE_STOPS_DDL.format(name="route_stops"))
        connection.exec_driver_sql(
            "CREATE INDEX ix_route_stops_booking_id ON route_stops (booking_id)"
        )


def _index_names(engine, table):
    return {index["name"] for index in inspect(engine).get_indexes(table)}


def test_migrating_the_old_schema_keeps_every_saved_stop(database):
    """The uniqueness migration must not lose stops, and must restore the index."""
    engine, ids = database
    first, second = ids["bookings"]
    _use_old_route_stops_schema(engine)
    _add_stops(engine, "route_stops", ids["route"], [(first, 1), (second, 2)])

    create_tables(engine)

    assert _live_stops(engine) == [(ids["route"], first, 1), (ids["route"], second, 2)]
    assert "route_stops_legacy" not in inspect(engine).get_table_names()
    assert "ix_route_stops_booking_id" in _index_names(engine, "route_stops")
    booking_only = [
        constraint
        for constraint in inspect(engine).get_unique_constraints("route_stops")
        if set(constraint["column_names"]) == {"booking_id"}
    ]
    assert booking_only == []


def test_running_startup_again_changes_nothing(database):
    """A healthy database is left alone by every start-up."""
    engine, ids = database
    first, second = ids["bookings"]
    _add_stops(engine, "route_stops", ids["route"], [(first, 1), (second, 2)])

    create_tables(engine)
    create_tables(engine)

    assert _live_stops(engine) == [(ids["route"], first, 1), (ids["route"], second, 2)]


def test_stops_stranded_in_legacy_table_are_recovered(database):
    """Reproduces the broken state: stops left in route_stops_legacy, live table empty."""
    engine, ids = database
    first, second = ids["bookings"]
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP INDEX IF EXISTS ix_route_stops_booking_id")
        connection.exec_driver_sql(OLD_ROUTE_STOPS_DDL.format(name="route_stops_legacy"))
        # As in the real broken database: the legacy table still owns the index name and the
        # live table has no such index.
        connection.exec_driver_sql(
            "CREATE INDEX ix_route_stops_booking_id ON route_stops_legacy (booking_id)"
        )
    _add_stops(engine, "route_stops_legacy", ids["route"], [(first, 1), (second, 2)])
    assert _live_stops(engine) == []

    create_tables(engine)

    assert _live_stops(engine) == [(ids["route"], first, 1), (ids["route"], second, 2)]
    assert "route_stops_legacy" not in inspect(engine).get_table_names()
    assert "ix_route_stops_booking_id" in _index_names(engine, "route_stops")


def test_recovery_does_not_duplicate_stops_already_in_the_live_table(database):
    """Only the missing stops are copied back; nothing is doubled."""
    engine, ids = database
    first, second = ids["bookings"]
    with engine.begin() as connection:
        connection.exec_driver_sql(OLD_ROUTE_STOPS_DDL.format(name="route_stops_legacy"))
    _add_stops(engine, "route_stops_legacy", ids["route"], [(first, 1), (second, 2)])
    _add_stops(engine, "route_stops", ids["route"], [(second, 2)])

    create_tables(engine)

    assert _live_stops(engine) == [(ids["route"], first, 1), (ids["route"], second, 2)]
    assert "route_stops_legacy" not in inspect(engine).get_table_names()
