"""Admin vehicle request and response shapes (US-05)."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VehicleCreate(BaseModel):
    """Fields required to add a vehicle."""

    name: str = Field(min_length=1, max_length=80)
    plate_number: str = Field(min_length=1, max_length=6)
    capacity_kg: int = Field(gt=0)
    capacity_litres: int = Field(gt=0)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        """Strip surrounding whitespace and reject a blank name."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("Vehicle name is required.")
        return normalized

    @field_validator("plate_number")
    @classmethod
    def normalize_plate(cls, value: str) -> str:
        """Normalize the plate and enforce NZ's six alphanumeric-character limit."""
        normalized = value.strip().upper()
        if not normalized.isalnum() or len(normalized) > 6:
            raise ValueError("Plate number must contain 1 to 6 letters and numbers.")
        return normalized


class VehicleUpdate(BaseModel):
    """Fields that may be edited on an existing vehicle."""

    name: str = Field(min_length=1, max_length=80)
    plate_number: str = Field(min_length=1, max_length=6)
    capacity_kg: int = Field(gt=0)
    capacity_litres: int = Field(gt=0)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        """Strip surrounding whitespace and reject a blank name."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("Vehicle name is required.")
        return normalized

    @field_validator("plate_number")
    @classmethod
    def normalize_plate(cls, value: str) -> str:
        """Normalize the plate and enforce NZ's six alphanumeric-character limit."""
        normalized = value.strip().upper()
        if not normalized.isalnum() or len(normalized) > 6:
            raise ValueError("Plate number must contain 1 to 6 letters and numbers.")
        return normalized


class VehicleOut(BaseModel):
    """Vehicle fields visible to Admins."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    plate_number: str
    capacity_kg: int
    capacity_litres: int
    is_active: bool