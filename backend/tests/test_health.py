from datetime import date

from sqlalchemy.exc import OperationalError

from app import __version__
from app.database import get_db
from app.main import app


def test_health_reports_ok(client, monkeypatch):
    monkeypatch.setattr("app.api.health.today_nz", lambda: date(2026, 10, 15))
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": __version__,
        "database": "ok",
        "nz_today": "2026-10-15",
    }


def test_health_reports_degraded_when_database_is_down(client):
    class BrokenSession:
        def execute(self, *args, **kwargs):
            raise OperationalError("SELECT 1", {}, Exception("database is down"))

    def broken_get_db():
        yield BrokenSession()

    app.dependency_overrides[get_db] = broken_get_db
    body = client.get("/api/health").json()
    assert body["status"] == "degraded"
    assert body["database"] == "unavailable"


def test_frontend_origin_is_allowed_by_cors(client):
    response = client.options(
        "/api/health",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
