"""Admin-only vehicle management endpoints (US-05)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.database import get_db
from app.schemas.vehicles import VehicleCreate, VehicleOut, VehicleUpdate
from app.services.vehicle_service import (
    DuplicateVehiclePlateError,
    VehicleInUseError,
    VehicleNotFoundError,
    create_vehicle,
    deactivate_vehicle,
    list_vehicles,
    reactivate_vehicle,
    update_vehicle,
)

router = APIRouter(
    prefix="/api/admin/vehicles",
    tags=["admin-vehicles"],
    dependencies=[Depends(require_admin)],
)


def _translate_error(error: Exception) -> HTTPException:
    """Map domain validation errors to suitable HTTP responses."""
    if isinstance(error, VehicleNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, DuplicateVehiclePlateError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(error, VehicleInUseError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error))


@router.get("", response_model=list[VehicleOut])
def read_vehicles(db: Annotated[Session, Depends(get_db)]) -> list[VehicleOut]:
    """List active and inactive vehicles for the Admin screen."""
    return [VehicleOut.model_validate(vehicle) for vehicle in list_vehicles(db)]


@router.post("", response_model=VehicleOut, status_code=status.HTTP_201_CREATED)
def add_vehicle(
    payload: VehicleCreate, db: Annotated[Session, Depends(get_db)]
) -> VehicleOut:
    """Create a validated active vehicle."""
    try:
        vehicle = create_vehicle(
            db,
            payload.name,
            payload.plate_number,
            payload.capacity_kg,
            payload.capacity_litres,
        )
    except (ValueError, VehicleInUseError, VehicleNotFoundError) as error:
        raise _translate_error(error) from error
    return VehicleOut.model_validate(vehicle)


@router.put("/{vehicle_id}", response_model=VehicleOut)
def edit_vehicle(
    vehicle_id: int,
    payload: VehicleUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> VehicleOut:
    """Edit name, plate, and capacities for future route generation."""
    try:
        vehicle = update_vehicle(
            db,
            vehicle_id,
            payload.name,
            payload.plate_number,
            payload.capacity_kg,
            payload.capacity_litres,
        )
    except (ValueError, VehicleNotFoundError) as error:
        raise _translate_error(error) from error
    return VehicleOut.model_validate(vehicle)


@router.patch("/{vehicle_id}/deactivate", response_model=VehicleOut)
def deactivate_admin_vehicle(
    vehicle_id: int, db: Annotated[Session, Depends(get_db)]
) -> VehicleOut:
    """Mark a vehicle inactive without deleting its record."""
    try:
        vehicle = deactivate_vehicle(db, vehicle_id)
    except (ValueError, VehicleInUseError, VehicleNotFoundError) as error:
        raise _translate_error(error) from error
    return VehicleOut.model_validate(vehicle)


@router.patch("/{vehicle_id}/reactivate", response_model=VehicleOut)
def reactivate_admin_vehicle(
    vehicle_id: int, db: Annotated[Session, Depends(get_db)]
) -> VehicleOut:
    """Mark an inactive vehicle active so it can be used for future routes."""
    try:
        vehicle = reactivate_vehicle(db, vehicle_id)
    except (ValueError, VehicleNotFoundError) as error:
        raise _translate_error(error) from error
    return VehicleOut.model_validate(vehicle)
