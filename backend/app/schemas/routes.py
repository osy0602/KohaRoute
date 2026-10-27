"""Admin route planning request and response shapes (US-06)."""

from datetime import date

from pydantic import BaseModel, Field


class DriverVehiclePair(BaseModel):
    """One chosen driver and vehicle for a generated route."""

    driver_id: int = Field(gt=0)
    vehicle_id: int = Field(gt=0)


class GenerateRoutesRequest(BaseModel):
    """Selected date and driver/vehicle assignments for route generation."""

    pickup_date: date
    assignments: list[DriverVehiclePair] = Field(min_length=1)


class PlanningDriverOut(BaseModel):
    id: int
    full_name: str


class PlanningVehicleOut(BaseModel):
    id: int
    name: str
    plate_number: str
    capacity_kg: int
    capacity_litres: int


class RoutePlanningOptions(BaseModel):
    """Active planning resources and date-specific route generation state."""

    pickup_date: date
    approved_booking_count: int
    candidate_booking_count: int
    existing_route_count: int
    replacement_allowed: bool
    replacement_block_reason: str | None = None
    drivers: list[PlanningDriverOut]
    vehicles: list[PlanningVehicleOut]


class RouteStopOut(BaseModel):
    """A saved, ordered booking stop on a route."""

    booking_id: int
    reference: str
    sequence: int
    status: str
    address_text: str
    latitude: float
    longitude: float
    category_names: list[str]
    estimated_weight_kg: int
    estimated_volume_l: int
    description: str | None


class RouteOut(BaseModel):
    """A route as saved after an ORS optimization response."""

    id: int
    pickup_date: date
    driver_id: int
    driver_name: str
    vehicle_id: int
    vehicle_name: str
    vehicle_plate_number: str
    vehicle_capacity_kg: int
    vehicle_capacity_litres: int
    status: str
    total_distance_m: int
    total_duration_s: int
    planned_weight_kg: int
    planned_volume_l: int
    geometry: str
    color: str
    stops: list[RouteStopOut]


class UnassignedBookingOut(BaseModel):
    """Approved booking that ORS could not assign to any selected vehicle."""

    id: int
    reference: str
    address_text: str
    estimated_weight_kg: int
    estimated_volume_l: int


class GenerateRoutesResponse(BaseModel):
    """Saved routes and bookings left Approved after generation."""

    routes: list[RouteOut]
    unassigned: list[UnassignedBookingOut]