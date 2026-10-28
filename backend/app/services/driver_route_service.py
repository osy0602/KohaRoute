"""Ownership-limited driver route reads and stop updates (US-10, US-11)."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Booking, BookingStatus, Photo, Route, RouteStop, User
from app.services.route_generation_service import route_status
from app.timeutil import utc_now_naive


class DriverRouteNotFoundError(LookupError):
    """Raised when no route or stop exists for the requested resource."""


class DriverRouteForbiddenError(PermissionError):
    """Raised when a driver attempts to access another driver's route or stop."""


class DriverStopTransitionError(RuntimeError):
    """Raised when a stop is no longer eligible for a driver update."""


def list_driver_routes(db: Session, driver: User, pickup_date: date) -> list[Route]:
    """Return only this driver's routes for a date, with all stop details preloaded."""
    statement = (
        select(Route)
        .where(Route.driver_id == driver.id, Route.pickup_date == pickup_date)
        .options(
            selectinload(Route.stops)
            .selectinload(RouteStop.booking)
            .selectinload(Booking.categories),
            selectinload(Route.stops)
            .selectinload(RouteStop.booking)
            .selectinload(Booking.photos),
        )
        .order_by(Route.id)
    )
    return list(db.scalars(statement).all())


def _route_and_stop_for_driver(
    db: Session, driver: User, route_id: int, booking_id: int
) -> tuple[Route, RouteStop]:
    """Verify route ownership before returning a stop or its photo metadata."""
    route = db.get(Route, route_id)
    if route is None:
        raise DriverRouteNotFoundError("Route not found")
    if route.driver_id != driver.id:
        raise DriverRouteForbiddenError("You do not have access to this route.")
    stop = db.scalar(
        select(RouteStop)
        .where(RouteStop.route_id == route_id, RouteStop.booking_id == booking_id)
        .options(
            selectinload(RouteStop.booking).selectinload(Booking.categories),
            selectinload(RouteStop.booking).selectinload(Booking.photos),
        )
    )
    if stop is None:
        raise DriverRouteNotFoundError("Stop not found on this route")
    return route, stop


def update_driver_stop(
    db: Session,
    driver: User,
    route_id: int,
    booking_id: int,
    new_status: BookingStatus,
    remark: str | None,
) -> RouteStop:
    """Update one owned Scheduled stop exactly once, recording remark, time, and driver."""
    route, stop = _route_and_stop_for_driver(db, driver, route_id, booking_id)
    if stop.status != BookingStatus.SCHEDULED:
        raise DriverStopTransitionError("This stop has already been updated and cannot be changed.")
    normalized_remark = remark.strip() if remark else ""
    if new_status == BookingStatus.MISSED and not normalized_remark:
        raise ValueError("A remark is required when marking a pickup Missed.")
    if len(normalized_remark) > 1000:
        raise ValueError("Remark must be no more than 1000 characters.")

    updated_at = utc_now_naive()
    stop.status = new_status
    stop.remark = normalized_remark or None
    stop.completed_at = updated_at
    stop.updated_by_user_id = driver.id
    stop.booking.status = new_status
    db.commit()
    return _route_and_stop_for_driver(db, driver, route.id, booking_id)[1]


def get_driver_photo(
    db: Session, driver: User, route_id: int, booking_id: int, photo_id: int
) -> Photo:
    """Return photo metadata only after proving the driver owns the route and stop."""
    _route, stop = _route_and_stop_for_driver(db, driver, route_id, booking_id)
    photo = db.get(Photo, photo_id)
    if photo is None or photo.booking_id != stop.booking_id:
        raise DriverRouteNotFoundError("Photo not found")
    return photo


def driver_route_status(route: Route) -> str:
    """Expose the same derived route lifecycle status used by Admin maps."""
    return route_status(route)