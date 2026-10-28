"""Driver-only route viewing, private photos, and stop updates (US-10, US-11)."""

from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_driver
from app.config import get_config
from app.database import get_db
from app.models import BookingStatus, Route, RouteStop, User
from app.schemas.driver_routes import (
    DriverPhotoOut,
    DriverRouteOut,
    DriverStopOut,
    DriverStopUpdate,
)
from app.services.driver_route_service import (
    DriverRouteForbiddenError,
    DriverRouteNotFoundError,
    DriverStopTransitionError,
    driver_route_status,
    get_driver_photo,
    list_driver_routes,
    update_driver_stop,
)
from app.timeutil import today_nz

router = APIRouter(
    prefix="/api/driver/routes",
    tags=["driver-routes"],
    dependencies=[Depends(require_driver)],
)


def _stop_out(stop: RouteStop) -> DriverStopOut:
    """Build one stop response: the single place that decides what a driver may see."""
    booking = stop.booking
    return DriverStopOut(
        booking_id=stop.booking_id,
        reference=booking.reference,
        sequence=stop.sequence,
        status=stop.status.value,
        address_text=booking.address_text,
        latitude=booking.latitude,
        longitude=booking.longitude,
        donor_name=booking.donor_name,
        contact_number=booking.contact_number,
        category_names=[category.name for category in booking.categories],
        estimated_weight_kg=booking.estimated_weight_kg,
        estimated_volume_l=booking.estimated_volume_l,
        description=booking.description,
        remark=stop.remark,
        completed_at=stop.completed_at.isoformat() if stop.completed_at else None,
        updated_by_user_id=stop.updated_by_user_id,
        photos=[
            DriverPhotoOut(id=photo.id, content_type=photo.content_type)
            for photo in booking.photos
        ],
    )


def _route_out(route: Route) -> DriverRouteOut:
    """Build a route response containing only details relevant to its assigned driver.

    The route line is the geometry saved by US-06, so no routing service is called here.
    """
    return DriverRouteOut(
        id=route.id,
        pickup_date=route.pickup_date,
        status=driver_route_status(route),
        vehicle_name=route.vehicle_name,
        vehicle_plate_number=route.vehicle_plate_number,
        geometry=route.geometry,
        total_distance_m=route.total_distance_m,
        total_duration_s=route.total_duration_s,
        planned_weight_kg=route.planned_weight_kg,
        planned_volume_l=route.planned_volume_l,
        stops=[_stop_out(stop) for stop in sorted(route.stops, key=lambda item: item.sequence)],
    )


def _translate_access_error(error: Exception) -> HTTPException:
    """Map route ownership and not-found failures to clear HTTP responses."""
    if isinstance(error, DriverRouteForbiddenError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))
    if isinstance(error, DriverRouteNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, DriverStopTransitionError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error))


@router.get("", response_model=list[DriverRouteOut])
def read_my_routes(
    driver: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    pickup_date: date | None = Query(default=None),
) -> list[DriverRouteOut]:
    """Return only the current driver's routes, for NZ today by default."""
    selected_date = pickup_date or today_nz()
    return [_route_out(route) for route in list_driver_routes(db, driver, selected_date)]


@router.patch("/{route_id}/stops/{booking_id}", response_model=DriverStopOut)
def update_my_stop(
    route_id: int,
    booking_id: int,
    payload: DriverStopUpdate,
    driver: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DriverStopOut:
    """Mark an owned Scheduled stop Completed or Missed, recording time/driver/remark."""
    if payload.status == "missed" and not (payload.remark or "").strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"field": "remark", "message": "A remark is required when marking a pickup Missed."},
        )
    try:
        stop = update_driver_stop(
            db,
            driver,
            route_id,
            booking_id,
            BookingStatus(payload.status),
            payload.remark,
        )
    except (DriverRouteForbiddenError, DriverRouteNotFoundError, DriverStopTransitionError, ValueError) as error:
        raise _translate_access_error(error) from error
    return _stop_out(stop)


@router.get("/{route_id}/stops/{booking_id}/photos/{photo_id}")
def read_my_stop_photo(
    route_id: int,
    booking_id: int,
    photo_id: int,
    driver: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Serve a photo only to the driver assigned to the stop's route."""
    try:
        photo = get_driver_photo(db, driver, route_id, booking_id, photo_id)
    except (DriverRouteForbiddenError, DriverRouteNotFoundError) as error:
        raise _translate_access_error(error) from error
    photo_directory = Path(get_config().photo_storage_dir).resolve()
    photo_path = (photo_directory / photo.stored_name).resolve()
    if photo_path.parent != photo_directory or not photo_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")
    return FileResponse(
        photo_path,
        media_type=photo.content_type,
        headers={"Cache-Control": "private, max-age=300"},
    )
