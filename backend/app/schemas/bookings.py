"""Public booking request and response schemas for US-02."""

from datetime import date

from pydantic import BaseModel, ConfigDict


class CategoryOption(BaseModel):
    """A category available to donors."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class SizePresetOption(BaseModel):
    """A configured size choice and its per-unit estimate."""

    key: str
    label: str
    description: str
    weight_kg: int
    volume_l: int


class BookingOptionsResponse(BaseModel):
    """The dynamic rules and choices needed to render the donor form."""

    pickup_dates: list[date]
    earliest_pickup_date: date
    latest_pickup_date: date
    categories: list[CategoryOption]
    size_presets: list[SizePresetOption]
    max_quantity: int
    min_photos: int
    max_photos: int
    max_photo_size_bytes: int
    description_max_chars: int


class AddressSuggestionResponse(BaseModel):
    """A label and signed token for an ORS address suggestion."""

    label: str
    token: str


class BookingCreatedResponse(BaseModel):
    """Safe public confirmation response; it contains no donor contact details."""

    reference: str
    status: str
    pickup_date: date
    estimated_weight_kg: int
    estimated_volume_l: int


class BookingTrackingResponse(BaseModel):
    """Privacy-limited information a donor may retrieve with their reference."""

    status: str
    pickup_date: date
    address_area: str
    rejection_reason: str | None = None
    missed_message: str | None = None
