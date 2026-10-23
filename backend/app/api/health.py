"""Health endpoint used by the frontend setup page and by deployment checks."""

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import __version__
from app.database import get_db
from app.timeutil import today_nz

router = APIRouter(prefix="/api", tags=["health"])


class HealthResponse(BaseModel):
    """Shape of the ``GET /api/health`` response."""

    status: Literal["ok", "degraded"]
    version: str
    database: Literal["ok", "unavailable"]
    nz_today: date


def _database_state(db: Session) -> Literal["ok", "unavailable"]:
    """Run the cheapest possible query to prove the database answers."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return "unavailable"
    return "ok"


@router.get("/health", response_model=HealthResponse)
def read_health(db: Annotated[Session, Depends(get_db)]) -> HealthResponse:
    """Report whether the API is running and the database is reachable.

    The API answers 200 even when the database is down, with ``status`` set to "degraded",
    so the frontend can show which part is broken instead of a generic network error.
    """
    database = _database_state(db)
    return HealthResponse(
        status="ok" if database == "ok" else "degraded",
        version=__version__,
        database=database,
        nz_today=today_nz(),
    )
