"""Admin booking review request and response shapes (US-04)."""

from datetime import date

from pydantic import BaseModel, Field, field_validator


class AdminPhotoOut(BaseModel):
    """Authorized photo metadata for an Admin review screen."""

    id: int
    content_type: str


class AdminBookingSummary(BaseModel):
    """Booking fields needed by the Admin review list."""

    id: int
    reference: str
    donor_name: str
    address_text: str
    pickup_date: date
    category_names: list[str]
    estimated_weight_kg: int
    estimated_volume_l: int
    status: str
    driver_remark: str | None = None
    photos: list[AdminPhotoOut]
    latitude: float
    longitude: float


class AdminBookingDetail(AdminBookingSummary):
    """Full booking details visible only to an Admin."""

    contact_number: str
    latitude: float
    longitude: float
    description: str | None
    rejection_reason: str | None


class RejectBookingRequest(BaseModel):
    """Required reason for declining a Pending booking."""

    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("reason")
    @classmethod
    def reason_must_not_be_blank(cls, value: str) -> str:
        """Reject whitespace-only rejection reasons."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("Enter a reason for rejecting this booking.")
        return normalized


class RescheduleBookingRequest(BaseModel):
    """New open pickup date selected by an Admin."""

    pickup_date: date
