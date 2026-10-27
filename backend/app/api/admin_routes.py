"""Admin route planning and saved route endpoints (US-06)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_admin
from app.database import get_db
from app.models import Booking, BookingStatus, Route, RouteStop, User, UserRole, Vehicle
from app.schemas.routes import (
    GenerateRoutesRequest,
    GenerateRoutesResponse,
    PlanningDriverOut,
    PlanningVehicleOut,
    RouteOut,
    RoutePlanningOptions,
    RouteStopOut,
    UnassignedBookingOut,
)
from app.services.route_generation_service import (
    DriverVehicleAssignment,
    RouteGenerationConflictError,
    RouteGenerationError,
    RouteRequestValidationError,
    generate_routes,
    route_status,
)
from app.services.route_planner import RoutePlannerError

router = APIRouter(
    prefix="/api/admin/routes",
    tags=["admin-routes"],
    dependencies=[Depends(require_admin)],
)


def _route_out(route: Route) -> RouteOut:
    """Convert a saved route into its Admin response representation."""
    return RouteOut(
        id=route.id,
        pickup_date=route.pickup_date,
        driver_id=route.driver_id,
        driver_name=route.driver.full_name,
        vehicle_id=route.vehicle_id,
        vehicle_name=route.vehicle_name,
        vehicle_plate_number=route.vehicle_plate_number,
        vehicle_capacity_kg=route.vehicle_capacity_kg,
        vehicle_capacity_litres=route.vehicle_capacity_litres,
        status=route_status(route),
        total_distance_m=route.total_distance_m,
        total_duration_s=route.total_duration_s,
        planned_weight_kg=route.planned_weight_kg,
        planned_volume_l=route.planned_volume_l,
        geometry=route.geometry,
        color=route.color,
        stops=[
            RouteStopOut(
                booking_id=stop.booking_id,
                reference=stop.booking.reference,
                sequence=stop.sequence,
                status=stop.status.value,
                address_text=stop.booking.address_text,
                latitude=stop.booking.latitude,
                longitude=stop.booking.longitude,
                category_names=[category.name for category in stop.booking.categories],
                estimated_weight_kg=stop.booking.estimated_weight_kg,
                estimated_volume_l=stop.booking.estimated_volume_l,
                description=stop.booking.description,
            )
            for stop in route.stops
        ],
    )


def _load_routes(db: Session, pickup_date: date) -> list[Route]:
    """Load saved routes, drivers, stops, bookings and categories without N+1 queries."""
    statement = (
        select(Route)
        .where(Route.pickup_date == pickup_date)
        .options(
            selectinload(Route.driver),
            selectinload(Route.stops)
            .selectinload(RouteStop.booking)
            .selectinload(Booking.categories),
        )
        .order_by(Route.id)
    )
    return list(db.scalars(statement).all())


@router.get("/options", response_model=RoutePlanningOptions)
def read_route_planning_options(
    pickup_date: Annotated[date, Query()],
    db: Annotated[Session, Depends(get_db)],
) -> RoutePlanningOptions:
    """Return active drivers/vehicles, approved job count, and replacement availability."""
    drivers = db.scalars(
        select(User)
        .where(User.role == UserRole.DRIVER, User.is_active.is_(True))
        .order_by(User.full_name, User.id)
    ).all()
    vehicles = db.scalars(
        select(Vehicle)
        .where(Vehicle.is_active.is_(True))
        .order_by(Vehicle.name, Vehicle.id)
    ).all()
    approved_count = db.scalar(
        select(func.count(Booking.id)).where(
            Booking.pickup_date == pickup_date,
            Booking.status == BookingStatus.APPROVED,
        )
    )
    routes = _load_routes(db, pickup_date)
    scheduled_count = sum(
        1 for route in routes for stop in route.stops if stop.status == BookingStatus.SCHEDULED
    )
    replacement_blocked = any(
        stop.status.value in {"completed", "missed"} for route in routes for stop in route.stops
    )
    return RoutePlanningOptions(
        pickup_date=pickup_date,
        approved_booking_count=approved_count or 0,
        candidate_booking_count=(approved_count or 0) + scheduled_count,
        existing_route_count=len(routes),
        replacement_allowed=not replacement_blocked,
        replacement_block_reason=(
            "Routes for this date are already in progress" if replacement_blocked else None
        ),
        drivers=[PlanningDriverOut(id=item.id, full_name=item.full_name) for item in drivers],
        vehicles=[
            PlanningVehicleOut(
                id=item.id,
                name=item.name,
                plate_number=item.plate_number,
                capacity_kg=item.capacity_kg,
                capacity_litres=item.capacity_litres,
            )
            for item in vehicles
        ],
    )


@router.get("", response_model=list[RouteOut])
def read_admin_routes(
    pickup_date: Annotated[date, Query()],
    db: Annotated[Session, Depends(get_db)],
) -> list[RouteOut]:
    """Read the saved route plan; this endpoint never calls ORS."""
    return [_route_out(route) for route in _load_routes(db, pickup_date)]


@router.post("/generate", response_model=GenerateRoutesResponse)
async def generate_admin_routes(
    payload: GenerateRoutesRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> GenerateRoutesResponse:
    """Optimize one date and replace its previous plan only after successful ORS output."""
    planner = request.app.state.route_planner
    try:
        result = await generate_routes(
            db,
            planner,
            payload.pickup_date,
            tuple(
                DriverVehicleAssignment(item.driver_id, item.vehicle_id)
                for item in payload.assignments
            ),
        )
    except RouteGenerationConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except RouteRequestValidationError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    except RouteGenerationError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    except RoutePlannerError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error

    persisted = {_route.id: _route for _route in result.routes}
    return GenerateRoutesResponse(
        routes=[_route_out(route) for route in persisted.values()],
        unassigned=[
            UnassignedBookingOut(
                id=booking.id,
                reference=booking.reference,
                address_text=booking.address_text,
                estimated_weight_kg=booking.estimated_weight_kg,
                estimated_volume_l=booking.estimated_volume_l,
            )
            for booking in result.unassigned_bookings
        ],
    )