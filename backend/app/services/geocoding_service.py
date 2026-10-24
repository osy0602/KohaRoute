"""OpenRouteService address search with bounded caching and signed selections."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import time
from collections import OrderedDict, defaultdict, deque
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.security import JWT_SECRET_KEY

ORS_AUTOCOMPLETE_URL = "https://api.openrouteservice.org/geocode/autocomplete"
MIN_QUERY_LENGTH = 3
MAX_SUGGESTIONS = 8
SUGGESTION_TTL_SECONDS = 600
CACHE_TTL_SECONDS = 300
CACHE_MAX_ENTRIES = 128
AUCKLAND_BOUNDS = {"min_lon": 174.3, "min_lat": -37.2, "max_lon": 175.7, "max_lat": -36.0}


class GeocoderUnavailableError(RuntimeError):
    """Raised when address search cannot reach or use OpenRouteService."""


class InvalidAddressSelectionError(ValueError):
    """Raised when a booking submits a forged or expired address selection."""


@dataclass(frozen=True)
class AddressSelection:
    """Verified address and coordinates returned by ORS."""

    token: str
    label: str
    latitude: float
    longitude: float


class AddressProvider(Protocol):
    """Interface implemented by ORS and test providers."""

    async def search(self, query: str) -> list[tuple[str, float, float]]:
        """Return Auckland address labels with latitude and longitude."""


class OrsAddressProvider:
    """Call the ORS autocomplete API and retain only Auckland, New Zealand results."""

    def __init__(self, client: httpx.AsyncClient, api_key: str):
        self._client = client
        self._api_key = api_key

    async def search(self, query: str) -> list[tuple[str, float, float]]:
        """Fetch a short list of address candidates within Auckland search bounds."""
        if not self._api_key:
            raise GeocoderUnavailableError(
                "Address search is not configured. Please try again later."
            )
        params = {
            "text": query,
            "size": MAX_SUGGESTIONS,
            "boundary.country": "NZ",
            **{f"boundary.rect.{key}": value for key, value in AUCKLAND_BOUNDS.items()},
        }
        try:
            response = await self._client.get(
                ORS_AUTOCOMPLETE_URL,
                params=params,
                headers={"Authorization": self._api_key},
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise GeocoderUnavailableError(
                "Address search is unavailable. Please try again."
            ) from error

        try:
            features = response.json().get("features", [])
        except (ValueError, AttributeError) as error:
            raise GeocoderUnavailableError(
                "Address search returned an invalid response."
            ) from error

        results = []
        for feature in features:
            properties = feature.get("properties", {})
            region = str(properties.get("region", "")).casefold()
            country = str(
                properties.get("country_a") or properties.get("country", "")
            ).casefold()
            coordinates = feature.get("geometry", {}).get("coordinates", [])
            if (
                country not in {"nz", "nzl", "new zealand"}
                or region not in {"auckland", "auckland region"}
                or len(coordinates) < 2
            ):
                continue
            longitude, latitude = coordinates[:2]
            if not _inside_auckland_bounds(latitude, longitude):
                continue
            label = properties.get("label")
            if label:
                results.append((str(label), float(latitude), float(longitude)))
        return results[:MAX_SUGGESTIONS]


def _inside_auckland_bounds(latitude: float, longitude: float) -> bool:
    """Reject coordinates outside ORS's Auckland-focused search rectangle."""
    return (
        AUCKLAND_BOUNDS["min_lat"] <= latitude <= AUCKLAND_BOUNDS["max_lat"]
        and AUCKLAND_BOUNDS["min_lon"] <= longitude <= AUCKLAND_BOUNDS["max_lon"]
    )


def _encode(payload: dict[str, str | int | float]) -> str:
    """Create a compact URL-safe token signed with the configured app secret."""
    body = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).rstrip(b"=")
    signature = hmac.new(JWT_SECRET_KEY.encode(), body, hashlib.sha256).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
    return f"{body.decode('ascii')}.{encoded_signature}"


def _decode(token: str) -> dict[str, str | int | float]:
    """Verify and decode a signed selection token."""
    try:
        body_part, signature_part = token.split(".")
        body = body_part.encode("ascii")
        signature = base64.urlsafe_b64decode(signature_part + "=" * (-len(signature_part) % 4))
        expected = hmac.new(JWT_SECRET_KEY.encode(), body, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise InvalidAddressSelectionError("Select an address from the suggestions.")
        payload = json.loads(base64.urlsafe_b64decode(body + b"=" * (-len(body) % 4)))
        if not isinstance(payload, dict) or payload.get("region") != "Auckland":
            raise InvalidAddressSelectionError("Select an address from the suggestions.")
        if type(payload.get("expires")) is not int or payload["expires"] <= int(time.time()):
            raise InvalidAddressSelectionError(
                "That address selection expired. Please search again."
            )
        if not isinstance(payload.get("label"), str):
            raise InvalidAddressSelectionError("Select an address from the suggestions.")
        latitude, longitude = float(payload["latitude"]), float(payload["longitude"])
        if not _inside_auckland_bounds(latitude, longitude):
            raise InvalidAddressSelectionError("Select an address from the suggestions.")
        return payload
    except InvalidAddressSelectionError:
        raise
    except (ValueError, TypeError, KeyError, UnicodeDecodeError, binascii.Error) as error:
        raise InvalidAddressSelectionError("Select an address from the suggestions.") from error


def verify_address_selection(token: str) -> AddressSelection:
    """Return the address represented by a valid, unexpired ORS suggestion token."""
    payload = _decode(token)
    return AddressSelection(
        token=token,
        label=str(payload["label"]),
        latitude=float(payload["latitude"]),
        longitude=float(payload["longitude"]),
    )


class AddressSearchService:
    """Cache successful address searches and sign their results for safe booking use."""

    def __init__(self, provider: AddressProvider):
        self._provider = provider
        self._cache: OrderedDict[str, tuple[float, tuple[AddressSelection, ...]]] = OrderedDict()

    async def suggestions(self, query: str) -> tuple[AddressSelection, ...]:
        """Return cached or fresh Auckland suggestions for a normalized query."""
        normalized = " ".join(query.split()).casefold()
        if len(normalized) < MIN_QUERY_LENGTH:
            raise ValueError("Enter at least 3 characters to search for an address.")
        now = time.monotonic()
        cached = self._cache.get(normalized)
        if cached and cached[0] > now:
            self._cache.move_to_end(normalized)
            return cached[1]
        if cached:
            del self._cache[normalized]

        results = await self._provider.search(normalized)
        expires = int(time.time()) + SUGGESTION_TTL_SECONDS
        selections = tuple(
            AddressSelection(
                token=_encode(
                    {
                        "label": label,
                        "latitude": latitude,
                        "longitude": longitude,
                        "region": "Auckland",
                        "expires": expires,
                    }
                ),
                label=label,
                latitude=latitude,
                longitude=longitude,
            )
            for label, latitude, longitude in results[:MAX_SUGGESTIONS]
        )
        self._cache[normalized] = (now + CACHE_TTL_SECONDS, selections)
        self._cache.move_to_end(normalized)
        while len(self._cache) > CACHE_MAX_ENTRIES:
            self._cache.popitem(last=False)
        return selections


class AddressRateLimiter:
    """Bound address-search traffic per client address using a sliding time window."""

    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._requests: defaultdict[str, deque[float]] = defaultdict(deque)

    def allow(self, client_key: str, now: float | None = None) -> bool:
        """Return false once the client exceeds its request budget for the window."""
        current = now if now is not None else time.monotonic()
        requests = self._requests[client_key]
        while requests and current - requests[0] >= self._window_seconds:
            requests.popleft()
        if len(requests) >= self._max_requests:
            return False
        requests.append(current)
        return True