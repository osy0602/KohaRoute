"""Tests for ORS address filtering, signed selections, caching and throttling."""

import asyncio

import httpx
import pytest

from app.services.geocoding_service import (
    AddressRateLimiter,
    AddressSearchService,
    GeocoderUnavailableError,
    InvalidAddressSelectionError,
    OrsAddressProvider,
    verify_address_selection,
)


def _feature(label, region="Auckland", country="NZ", coordinates=(174.65, -36.85)):
    """Build a small ORS-like GeoJSON feature for provider tests."""
    return {
        "type": "Feature",
        "properties": {"label": label, "region": region, "country_a": country},
        "geometry": {"type": "Point", "coordinates": list(coordinates)},
    }


def test_ors_provider_sends_auckland_bounds_and_filters_results():
    """Provider requests are bounded and non-Auckland results are discarded."""
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "features": [
                    _feature("1 Sample Road, Auckland"),
                    _feature("Outside region", region="Waikato"),
                    _feature("Wrong country", country="AU"),
                    _feature("Outside bounds", coordinates=(175.9, -36.8)),
                ]
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            provider = OrsAddressProvider(client, "fake-key")
            return await provider.search("sample road")

    results = asyncio.run(run())
    assert results == [("1 Sample Road, Auckland", -36.85, 174.65)]
    assert requests[0].headers["Authorization"] == "fake-key"
    assert "boundary.rect.min_lon=174.3" in str(requests[0].url)
    assert "boundary.country=NZ" in str(requests[0].url)


def test_ors_provider_accepts_ors_three_letter_new_zealand_country_code():
    """ORS emits NZL in country_a, which must be accepted as New Zealand."""

    def respond(_request):
        return httpx.Response(
            200,
            json={"features": [_feature("Auckland address", country="NZL", region="Auckland Region")]},
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await OrsAddressProvider(client, "fake-key").search("auckland")

    assert asyncio.run(run()) == [("Auckland address", -36.85, 174.65)]


def test_ors_provider_without_key_fails_without_network_call():
    """Missing credentials produce a retryable configuration error."""

    async def run():
        async with httpx.AsyncClient() as client:
            provider = OrsAddressProvider(client, "")
            with pytest.raises(GeocoderUnavailableError, match="not configured"):
                await provider.search("sample road")

    asyncio.run(run())


def test_search_service_signs_results_and_caches_normalized_query():
    """Equivalent searches share one provider request and yield verifiable tokens."""

    class FakeProvider:
        calls = 0

        async def search(self, query):
            self.calls += 1
            assert query == "sample road"
            return [("1 Sample Road, Auckland", -36.85, 174.65)]

    provider = FakeProvider()
    service = AddressSearchService(provider)

    async def run():
        first = await service.suggestions("  Sample   Road ")
        second = await service.suggestions("sample road")
        return first, second

    first, second = asyncio.run(run())
    assert first == second
    assert provider.calls == 1
    assert verify_address_selection(first[0].token).label == "1 Sample Road, Auckland"


def test_address_selection_tampering_is_rejected():
    """A client cannot change the label or coordinates in a signed suggestion."""

    class FakeProvider:
        async def search(self, _query):
            return [("1 Sample Road, Auckland", -36.85, 174.65)]

    selection = asyncio.run(AddressSearchService(FakeProvider()).suggestions("sample"))[0]
    body, signature = selection.token.split(".")
    changed_body = ("A" if body[0] != "A" else "B") + body[1:]
    with pytest.raises(InvalidAddressSelectionError, match="Select an address"):
        verify_address_selection(f"{changed_body}.{signature}")


def test_address_search_rate_limit_resets_after_window():
    """The limiter rejects excess requests and permits them after expiry."""
    limiter = AddressRateLimiter(max_requests=2, window_seconds=60)
    assert limiter.allow("127.0.0.1", now=10)
    assert limiter.allow("127.0.0.1", now=11)
    assert not limiter.allow("127.0.0.1", now=12)
    assert limiter.allow("127.0.0.1", now=70)


def test_search_service_requires_three_characters():
    """Short queries are rejected before contacting the provider."""

    class FakeProvider:
        async def search(self, _query):
            raise AssertionError("provider should not be called")

    with pytest.raises(ValueError, match="at least 3 characters"):
        asyncio.run(AddressSearchService(FakeProvider()).suggestions("ab"))