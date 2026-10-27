"""Vehicle CRUD and capacity/business-rule validation (US-05)."""

import re
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Vehicle

_NZ_PLATE = re.compile(r"^[A-Z0-9]{1,6}$")
ACTIVE_ROUTE_STATUSES = frozenset({"planned", "in_progress"})


class VehicleNotFoundError(LookupError):
    """Raised when an Admin requests a vehicle that does not exist."""


class DuplicateVehiclePlateError(ValueError):
    """Raised when a plate number is already assigned to a vehicle."""


class VehicleInUseError(RuntimeError):
    """Raised when a vehicle cannot be deactivated because a route is active."""


def normalize_plate_number(value: str) -> str:
    """Normalize an NZ plate number to uppercase and validate its allowed characters."""
    plate = value.strip().upper()
    if not _NZ_PLATE.fullmatch(plate):
        raise ValueError("Plate number must contain 1 to 6 letters and numbers.")
    return plate


def validate_capacity(capacity_kg: int, capacity_litres: int) -> None:
    """Reject missing, non-integer, zero, or negative capacities."""
    if isinstance(capacity_kg, bool) or not isinstance(capacity_kg, int) or capacity_kg <= 0:
        raise ValueError("Capacity in kg must be a positive whole number.")
    if (
        isinstance(capacity_litres, bool)
        or not isinstance(capacity_litres, int)
        or capacity_litres <= 0
    ):
        raise ValueError("Capacity in litres must be a positive whole number.")


def ensure_vehicle_not_on_active_route(route_statuses: Iterable[str]) -> None:
    """Raise if route statuses include Planned or In progress.

    Part 7 will provide the vehicle's persisted route statuses when the route model exists.
    Keeping the transition rule here makes vehicle deactivation share the same rule once routes
    are introduced.
    """
    if ACTIVE_ROUTE_STATUSES.intersection(status.casefold() for status in route_statuses):
        raise VehicleInUseError("This vehicle is on a Planned or In progress route.")


def list_vehicles(db: Session) -> list[Vehicle]:
    """Return vehicles ordered by active state, then name and plate."""
    statement = select(Vehicle).order_by(
        Vehicle.is_active.desc(), Vehicle.name, Vehicle.plate_number
    )
    return list(db.scalars(statement).all())


def get_vehicle(db: Session, vehicle_id: int) -> Vehicle:
    """Return one vehicle or raise a domain-specific not-found error."""
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise VehicleNotFoundError("Vehicle not found")
    return vehicle


def _ensure_plate_available(db: Session, plate_number: str, exclude_id: int | None = None) -> None:
    """Check plate uniqueness before writing for a clear conflict response."""
    statement = select(Vehicle.id).where(Vehicle.plate_number == plate_number)
    if exclude_id is not None:
        statement = statement.where(Vehicle.id != exclude_id)
    if db.scalar(statement) is not None:
        raise DuplicateVehiclePlateError("That plate number is already assigned to a vehicle.")


def create_vehicle(
    db: Session,
    name: str,
    plate_number: str,
    capacity_kg: int,
    capacity_litres: int,
) -> Vehicle:
    """Create an active vehicle after validating name, plate, and positive capacities."""
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("Vehicle name is required.")
    plate = normalize_plate_number(plate_number)
    validate_capacity(capacity_kg, capacity_litres)
    _ensure_plate_available(db, plate)
    vehicle = Vehicle(
        name=normalized_name,
        plate_number=plate,
        capacity_kg=capacity_kg,
        capacity_litres=capacity_litres,
        is_active=True,
    )
    db.add(vehicle)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise DuplicateVehiclePlateError(
            "That plate number is already assigned to a vehicle."
        ) from error
    db.refresh(vehicle)
    return vehicle


def update_vehicle(
    db: Session,
    vehicle_id: int,
    name: str,
    plate_number: str,
    capacity_kg: int,
    capacity_litres: int,
) -> Vehicle:
    """Update vehicle fields without changing capacity snapshots in existing routes."""
    vehicle = get_vehicle(db, vehicle_id)
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("Vehicle name is required.")
    plate = normalize_plate_number(plate_number)
    validate_capacity(capacity_kg, capacity_litres)
    _ensure_plate_available(db, plate, exclude_id=vehicle_id)
    vehicle.name = normalized_name
    vehicle.plate_number = plate
    vehicle.capacity_kg = capacity_kg
    vehicle.capacity_litres = capacity_litres
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise DuplicateVehiclePlateError(
            "That plate number is already assigned to a vehicle."
        ) from error
    db.refresh(vehicle)
    return vehicle


def deactivate_vehicle(db: Session, vehicle_id: int) -> Vehicle:
    """Deactivate a vehicle after checking route status when route data is available."""
    vehicle = get_vehicle(db, vehicle_id)
    # Routes are introduced in Part 7. At that point, pass persisted statuses into the shared
    # ensure_vehicle_not_on_active_route rule before changing this flag.
    ensure_vehicle_not_on_active_route(())
    vehicle.is_active = False
    db.commit()
    db.refresh(vehicle)
    return vehicle