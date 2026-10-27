"""Prepare, optimize, and transactionally replace saved routes (US-06)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Booking, BookingStatus, Route, RouteStop, User, UserRole, Vehicle
from app.services.route_planner import (
    RouteJob,
    RoutePlan,
    RoutePlanner,
    RoutePlannerError,
    RouteProblem,
    RouteVehicle,
)
from app.services.settings_service import load_business_settings

ROUTE_COLORS = (
    "#247BA0",
    "#F25F5C",
    "#70C1B3",
    "#50514F",
    "#9B5DE5",
    "#F18F01",
    "#2D6A4F",
    "#D1495B",
)
ACTIVE_ROUTE_STOP_STATUSES = {BookingStatus.COMPLETED, BookingStatus.MISSED}


class RouteGenerationError(RuntimeError):
    """Raised when route generation cannot safely proceed."""


class RouteGenerationConflictError(RouteGenerationError):
    """Raised when routes already include completed or missed stops."""


class RouteRequestValidationError(ValueError):
    """Raised when assignments or selected resources are invalid."""


@dataclass(frozen=True)
class DriverVehicleAssignment:
    """An Admin's selected driver/vehicle pair."""

    driver_id: int
    vehicle_id: int


@dataclass(frozen=True)
class RouteGenerationResult:
    """Persisted routes plus bookings that remain Approved and unassigned."""

    routes: tuple[Route, ...]
    unassigned_bookings: tuple[Booking, ...]


def route_status(route: Route) -> str:
    """Derive route lifecycle status from stop statuses rather than storing duplicate state."""
    statuses = [stop.status for stop in route.stops]
    if statuses and all(status in ACTIVE_ROUTE_STOP_STATUSES for status in statuses):
        return "done"
    if any(status in ACTIVE_ROUTE_STOP_STATUSES for status in statuses):
        return "in_progress"
    return "planned"


def _load_existing_routes(db: Session, pickup_date: date) -> list[Route]:
    """Load the date's previous plans and stops in bounded queries."""
    statement = (
        select(Route)
        .where(Route.pickup_date == pickup_date)
        .options(
            selectinload(Route.stops).selectinload(RouteStop.booking).selectinload(Booking.categories),
            selectinload(Route.driver),
            selectinload(Route.vehicle),
        )
    )
    return list(db.scalars(statement).all())


def _candidate_bookings(
    db: Session, pickup_date: date, existing_routes: list[Route]
) -> list[Booking]:
    """Use Approved bookings plus old Scheduled stops when replacing an untouched plan."""
    candidates = list(
        db.scalars(
            select(Booking)
            .where(
                Booking.pickup_date == pickup_date,
                Booking.status == BookingStatus.APPROVED,
            )
            .options(selectinload(Booking.categories))
            .order_by(Booking.id)
        ).all()
    )
    known_ids = {booking.id for booking in candidates}
    for route in existing_routes:
        for stop in route.stops:
            booking = stop.booking
            if booking.id not in known_ids and stop.status == BookingStatus.SCHEDULED:
                candidates.append(booking)
                known_ids.add(booking.id)
    return candidates


def _validate_assignments(
    db: Session, assignments: tuple[DriverVehicleAssignment, ...]
) -> tuple[list[User], list[Vehicle]]:
    """Require unique active drivers and vehicles with one-to-one assignment pairing."""
    if not assignments:
        raise RouteRequestValidationError("Choose at least one driver and vehicle.")
    driver_ids = [assignment.driver_id for assignment in assignments]
    vehicle_ids = [assignment.vehicle_id for assignment in assignments]
    if len(set(driver_ids)) != len(driver_ids):
        raise RouteRequestValidationError("Each driver can only be assigned one vehicle.")
    if len(set(vehicle_ids)) != len(vehicle_ids):
        raise RouteRequestValidationError("Each vehicle can only be assigned to one driver.")

    drivers = list(
        db.scalars(
            select(User).where(
                User.id.in_(driver_ids),
                User.role == UserRole.DRIVER,
                User.is_active.is_(True),
            )
        ).all()
    )
    vehicles = list(
        db.scalars(
            select(Vehicle).where(
                Vehicle.id.in_(vehicle_ids),
                Vehicle.is_active.is_(True),
            )
        ).all()
    )
    if len(drivers) != len(set(driver_ids)):
        raise RouteRequestValidationError("Choose active driver accounts only.")
    if len(vehicles) != len(set(vehicle_ids)):
        raise RouteRequestValidationError("Choose active vehicles only.")
    driver_by_id = {driver.id: driver for driver in drivers}
    vehicle_by_id = {vehicle.id: vehicle for vehicle in vehicles}
    return (
        [driver_by_id[item.driver_id] for item in assignments],
        [vehicle_by_id[item.vehicle_id] for item in assignments],
    )


def _assert_plan_is_valid(plan: RoutePlan, job_ids: set[int], vehicle_ids: set[int]) -> None:
    """Reject malformed ORS output before touching the database transaction."""
    assigned: list[int] = []
    for route in plan.routes:
        if route.vehicle_id not in vehicle_ids:
            raise RoutePlannerError("Route optimization returned an unknown vehicle.")
        if not route.geometry:
            raise RoutePlannerError("Route optimization returned a route without geometry.")
        assigned.extend(route.job_ids)
    unassigned = list(plan.unassigned_job_ids)
    if len(set(assigned)) != len(assigned) or len(set(unassigned)) != len(unassigned):
        raise RoutePlannerError("Route optimization returned duplicate booking assignments.")
    if set(assigned).intersection(unassigned) or set(assigned).union(unassigned) != job_ids:
        raise RoutePlannerError("Route optimization returned an incomplete assignment result.")


async def generate_routes(
    db: Session,
    planner: RoutePlanner,
    pickup_date: date,
    assignments: tuple[DriverVehicleAssignment, ...],
) -> RouteGenerationResult:
    """Call the planner first, then atomically replace the date's untouched route plan."""
    existing_routes = _load_existing_routes(db, pickup_date)
    if any(
        stop.status in ACTIVE_ROUTE_STOP_STATUSES
        for route in existing_routes
        for stop in route.stops
    ):
        raise RouteGenerationConflictError("Routes for this date are already in progress")

    candidates = _candidate_bookings(db, pickup_date, existing_routes)
    if not candidates:
        raise RouteRequestValidationError("No Approved bookings for this date.")

    drivers, vehicles = _validate_assignments(db, assignments)
    settings = load_business_settings(db)
    task_limit = math.ceil(len(candidates) / len(assignments))
    depot = (settings.depot.longitude, settings.depot.latitude)
    first_planner_vehicle_id = max((booking.id for booking in candidates), default=0) + 1
    planner_vehicle_ids = {
        vehicle.id: first_planner_vehicle_id + index for index, vehicle in enumerate(vehicles)
    }
    problem = RouteProblem(
        jobs=tuple(
            RouteJob(
                id=booking.id,
                location=(booking.longitude, booking.latitude),
                weight_kg=booking.estimated_weight_kg,
                volume_l=booking.estimated_volume_l,
            )
            for booking in candidates
        ),
        vehicles=tuple(
            RouteVehicle(
                id=planner_vehicle_ids[vehicle.id],
                start=depot,
                end=depot,
                capacity_kg=vehicle.capacity_kg,
                capacity_litres=vehicle.capacity_litres,
                max_tasks=task_limit,
            )
            for vehicle in vehicles
        ),
    )

    # No ORM writes occur before this call completes successfully.
    try:
        plan = await planner.plan(problem)
    except RoutePlannerError as error:
        raise RouteGenerationError(str(error)) from error
    _assert_plan_is_valid(
        plan,
        {booking.id for booking in candidates},
        set(planner_vehicle_ids.values()),
    )

    booking_by_id = {booking.id: booking for booking in candidates}
    driver_by_vehicle = {
        vehicle.id: driver for driver, vehicle in zip(drivers, vehicles, strict=True)
    }
    vehicle_by_planner_id = {
        planner_vehicle_ids[vehicle.id]: vehicle for vehicle in vehicles
    }
    assigned_ids = {job_id for route in plan.routes for job_id in route.job_ids}
    unassigned = tuple(booking_by_id[item] for item in plan.unassigned_job_ids)
    saved_routes: list[Route] = []

    try:
        for old_route in existing_routes:
            for old_stop in old_route.stops:
                if old_stop.booking.status == BookingStatus.SCHEDULED:
                    old_stop.booking.status = BookingStatus.APPROVED
            db.delete(old_route)
        db.flush()

        for route_index, planned_route in enumerate(plan.routes):
            vehicle = vehicle_by_planner_id[planned_route.vehicle_id]
            driver = driver_by_vehicle[vehicle.id]
            route_bookings = [booking_by_id[item] for item in planned_route.job_ids]
            route = Route(
                pickup_date=pickup_date,
                driver_id=driver.id,
                vehicle_id=vehicle.id,
                vehicle_name=vehicle.name,
                vehicle_plate_number=vehicle.plate_number,
                vehicle_capacity_kg=vehicle.capacity_kg,
                vehicle_capacity_litres=vehicle.capacity_litres,
                total_distance_m=planned_route.distance_m,
                total_duration_s=planned_route.duration_s,
                planned_weight_kg=sum(item.estimated_weight_kg for item in route_bookings),
                planned_volume_l=sum(item.estimated_volume_l for item in route_bookings),
                geometry=planned_route.geometry,
                color=ROUTE_COLORS[route_index % len(ROUTE_COLORS)],
            )
            for sequence, booking in enumerate(route_bookings, start=1):
                booking.status = BookingStatus.SCHEDULED
                route.stops.append(
                    RouteStop(
                        booking=booking,
                        sequence=sequence,
                        status=BookingStatus.SCHEDULED,
                    )
                )
            db.add(route)
            saved_routes.append(route)

        for booking in unassigned:
            booking.status = BookingStatus.APPROVED
        db.commit()
    except Exception:
        db.rollback()
        raise

    route_ids = [route.id for route in saved_routes]
    if not route_ids:
        return RouteGenerationResult((), unassigned)
    persisted = list(
        db.scalars(
            select(Route)
            .where(Route.id.in_(route_ids))
            .options(
                selectinload(Route.stops).selectinload(RouteStop.booking).selectinload(Booking.categories),
                selectinload(Route.driver),
                selectinload(Route.vehicle),
            )
            .order_by(Route.id)
        ).all()
    )
    return RouteGenerationResult(tuple(persisted), unassigned)