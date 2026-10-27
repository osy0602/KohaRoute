"""Manually verify ORS Optimization support for max_tasks and route geometry.

Run from backend/ with KOHA-ROUTE active and ORS_API_KEY configured:

    python ../scripts/ors_optimization_spike.py

This sends one small live request and never prints the API key or route/address data.
"""

import asyncio

import httpx

from app.config import get_config

ORS_OPTIMIZATION_URL = "https://api.openrouteservice.org/optimization"
DEPOT = [174.609864, -36.818826]


async def main() -> None:
    """Send one two-location optimization request and report response capabilities."""
    api_key = get_config().ors_api_key
    if not api_key:
        raise SystemExit("ORS_API_KEY is not configured in backend/.env")
    payload = {
        "jobs": [{"id": 1001, "location": DEPOT, "amount": [5, 20]}],
        "vehicles": [
            {
                "id": 2001,
                "profile": "driving-car",
                "start": DEPOT,
                "end": DEPOT,
                "capacity": [100, 500],
                "max_tasks": 1,
            }
        ],
        "options": {"g": True},
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(30, connect=5)) as client:
        response = await client.post(
            ORS_OPTIMIZATION_URL,
            json=payload,
            headers={"Authorization": api_key, "Content-Type": "application/json"},
        )
    print("HTTP status:", response.status_code)
    body = response.json()
    if response.is_error:
        error = body.get("error", body)
        print("ORS error:", str(error.get("message", error))[:300])
        return
    routes = body.get("routes", [])
    print("Routes returned:", len(routes))
    print("Unassigned jobs:", len(body.get("unassigned", [])))
    print("max_tasks accepted: request succeeded")
    print("Geometry returned:", bool(routes and routes[0].get("geometry")))
    if routes:
        print("Route metric fields:", sorted(key for key in routes[0] if key in {"distance", "duration", "steps", "geometry"}))


if __name__ == "__main__":
    asyncio.run(main())