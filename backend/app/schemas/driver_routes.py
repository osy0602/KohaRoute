"""Driver route and stop response shapes for US-10 and US-11."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class DriverPhotoOut(BaseModel):
    """A private photo available to the assigned driver."""

    id: int
    content_type: str


class DriverStopOut(BaseModel):
    """Stop details visible only to the route's assigned driver."""

    booking_id: int
    reference: str
    sequence: int
    status: str
    address_text: str
    latitude: float
    longitude: float
    donor_name: str
    contact_number: str
    category_names: list[str]
    estimated_weight_kg: int
    estimated_volume_l: int
    description: str | None
    remark: str | None
    completed_at: str | None = None
    updated_by_user_id: int | None = None
    photos: list[DriverPhotoOut]


class DriverRouteOut(BaseModel):
    """A saved route and its stops, returned only to its assigned driver."""

    id: int
    pickup_date: date
    status: str
    vehicle_name: str
    vehicle_plate_number: str
    geometry: str
    total_distance_m: int
    total_duration_s: int
    planned_weight_kg: int
    planned_volume_l: int
    stops: list[DriverStopOut]


class DriverStopUpdate(BaseModel):
    """A one-way driver update from Scheduled to Completed or Missed."""

    status: Literal["completed", "missed"]
    remark: str | None = Field(default=None, max_length=1000)