"""Request and response shapes for the auth endpoints."""

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """The login form. Both fields are required."""

    email: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    """What the client may know about a user. Never includes the password hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: str


class LoginResponse(BaseModel):
    """The token and the user returned by a successful login."""

    access_token: str
    token_type: str = "bearer"
    user: UserOut
