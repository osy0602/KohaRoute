"""OpenRouteService Optimization adapter and a deterministic fake planner (US-06)."""

from dataclasses import dataclass
from typing import Protocol

import httpx

ORS_OPTIMIZATION_URL = "https://api.openrouteservice.org/optimization"


class RoutePlannerError(RuntimeError):
    """Raised when a planner cannot produce a valid route result."""


@dataclass(frozen=True)
class RouteJob:
    """A pickup passed to the optimization provider."""

    id: int
    location: tuple[float, float]
    weight_kg: int
    volume_l: int


@dataclass(frozen=True)
class RouteVehicle:
    """A driver/vehicle resource passed to the optimization provider."""

    id: int
    start: tuple[float, float]
    end: tuple[float, float]
    capacity_kg: int
    capacity_litres: int
    max_tasks: int


@dataclass(frozen=True)
class RouteProblem:
    """Jobs and vehicles for one date's single ORS optimization request."""

    jobs: tuple[RouteJob, ...]
    vehicles: tuple[RouteVehicle, ...]


@dataclass(frozen=True)
class PlannedRoute:
    """One ordered provider route with saved geometry and summary metrics."""

    vehicle_id: int
    job_ids: tuple[int, ...]
    geometry: str
    distance_m: int
    duration_s: int


@dataclass(frozen=True)
class RoutePlan:
    """All provider routes plus jobs that could not be assigned."""

    routes: tuple[PlannedRoute, ...]
    unassigned_job_ids: tuple[int, ...]


class RoutePlanner(Protocol):
    """Adapter contract implemented by the ORS client and deterministic fakes."""

    async def plan(self, problem: RouteProblem) -> RoutePlan:
        """Optimize the supplied jobs over the selected vehicles."""


class OrsRoutePlanner:
    """Translate KohaRoute jobs/vehicles to the ORS Optimization API contract."""

    def __init__(self, client: httpx.AsyncClient, api_key: str):
        self._client = client
        self._api_key = api_key

    async def plan(self, problem: RouteProblem) -> RoutePlan:
        """Call ORS once and parse ordered jobs, unassigned jobs, geometry, distance and time."""
        if not self._api_key:
            raise RoutePlannerError("Route optimization is not configured. Add ORS_API_KEY.")
        payload = {
            "jobs": [
                {
                    "id": job.id,
                    "location": list(job.location),
                    "amount": [job.weight_kg, job.volume_l],
                }
                for job in problem.jobs
            ],
            "vehicles": [
                {
                    "id": vehicle.id,
                    "profile": "driving-car",
                    "start": list(vehicle.start),
                    "end": list(vehicle.end),
                    "capacity": [vehicle.capacity_kg, vehicle.capacity_litres],
                    "max_tasks": vehicle.max_tasks,
                }
                for vehicle in problem.vehicles
            ],
            "options": {"g": True},
        }
        try:
            response = await self._client.post(
                ORS_OPTIMIZATION_URL,
                json=payload,
                headers={"Authorization": self._api_key, "Content-Type": "application/json"},
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise RoutePlannerError("Route optimization is unavailable. Please try again.") from error
        if not isinstance(body, dict) or not isinstance(body.get("routes"), list):
            raise RoutePlannerError("Route optimization returned an invalid response.")

        routes = []
        for item in body["routes"]:
            try:
                job_ids = tuple(
                    int(step["job"])
                    for step in item.get("steps", [])
                    if step.get("type") == "job" and step.get("job") is not None
                )
                geometry = item.get("geometry")
                if not isinstance(geometry, str) or not geometry:
                    raise ValueError("Missing route geometry")
                routes.append(
                    PlannedRoute(
                        vehicle_id=int(item["vehicle"]),
                        job_ids=job_ids,
                        geometry=geometry,
                        distance_m=round(float(item.get("distance", 0))),
                        duration_s=round(float(item.get("duration", 0))),
                    )
                )
            except (KeyError, TypeError, ValueError) as error:
                raise RoutePlannerError("Route optimization returned an invalid route.") from error
        unassigned = []
        for item in body.get("unassigned", []):
            if isinstance(item, dict) and item.get("type") == "job" and item.get("id") is not None:
                unassigned.append(int(item["id"]))
        return RoutePlan(tuple(routes), tuple(unassigned))


class FakeRoutePlanner:
    """Deterministic no-network planner for local/manual runs and future tests."""

    def __init__(self, plan: RoutePlan | None = None):
        self._plan = plan
        self.call_count = 0

    async def plan(self, problem: RouteProblem) -> RoutePlan:
        """Return the configured plan or assign jobs round-robin with placeholder geometry."""
        self.call_count += 1
        if self._plan is not None:
            return self._plan
        if not problem.vehicles:
            return RoutePlan((), tuple(job.id for job in problem.jobs))
        jobs_by_vehicle: dict[int, list[int]] = {vehicle.id: [] for vehicle in problem.vehicles}
        unassigned: list[int] = []
        loads = {vehicle.id: [0, 0] for vehicle in problem.vehicles}
        for job in problem.jobs:
            candidates = sorted(problem.vehicles, key=lambda vehicle: len(jobs_by_vehicle[vehicle.id]))
            vehicle = next(
                (
                    candidate
                    for candidate in candidates
                    if loads[candidate.id][0] + job.weight_kg <= candidate.capacity_kg
                    and loads[candidate.id][1] + job.volume_l <= candidate.capacity_litres
                    and len(jobs_by_vehicle[candidate.id]) < candidate.max_tasks
                ),
                None,
            )
            if vehicle is None:
                unassigned.append(job.id)
                continue
            jobs_by_vehicle[vehicle.id].append(job.id)
            loads[vehicle.id][0] += job.weight_kg
            loads[vehicle.id][1] += job.volume_l
        routes = tuple(
            PlannedRoute(
                vehicle_id=vehicle_id,
                job_ids=tuple(job_ids),
                geometry="_p~iF~ps|U_ulLnnqC_mqNvxq`@",
                distance_m=0,
                duration_s=0,
            )
            for vehicle_id, job_ids in jobs_by_vehicle.items()
            if job_ids
        )
        return RoutePlan(routes, tuple(unassigned))