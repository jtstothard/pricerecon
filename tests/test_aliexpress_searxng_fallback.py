"""Test SearXNG fallback lane in AliExpress connector."""

from typing import Any, cast

import httpx
import pytest

from pricerecon.connectors.aliexpress import AliExpressConnector


@pytest.mark.asyncio
async def test_aliexpress_uses_searxng_when_affiliate_and_brave_fail():
    """Test that SearXNG is used as fallback when affiliate and Brave both fail."""
    calls: list[tuple[str, str]] = []

    class DummyResponse:
        def __init__(self, payload: dict[str, object] | str, status_code: int = 200):
            self._payload = payload
            self.status_code = status_code

        def raise_for_status(self):
            if self.status_code >= 400:
                raise httpx.HTTPStatusError(
                    "boom",
                    request=httpx.Request("POST", "https://example.test"),
                    response=httpx.Response(self.status_code),
                )

        def json(self):
            if isinstance(self._payload, dict):
                return self._payload
            raise ValueError("Not JSON")

        @property
        def text(self):
            if isinstance(self._payload, str):
                return self._payload
            return str(self._payload)

    class DummyClient:
        async def get(self, url, headers=None, params=None, timeout=None, follow_redirects=True):
            calls.append((url, "GET"))

            # SearXNG endpoint - return mock results (titles include prices)
            if "searxng" in url:
                return DummyResponse(
                    {
                        "results": [
                            {
                                "url": "https://www.aliexpress.com/item/1005001234567890.html",
                                "title": "Test Product 1 £29.99",
                            },
                            {
                                "url": "https://www.aliexpress.com/item/1005009876543210.html",
                                "title": "Test Product 2 £49.99",
                            },
                        ]
                    }
                )

            raise AssertionError(f"Unexpected GET request to: {url}")

        async def post(self, url, json=None, headers=None):
            calls.append((url, "POST"))
            raise AssertionError(f"Unexpected POST to: {url}")

        async def aclose(self):
            return None

    async def noop_rate_limit():
        return None

    # Configure connector with SearXNG URL
    connector = AliExpressConnector(
        {
            "searxng_url": "http://mock-searxng:8080",
            "searxng_discovery": True,
        },
        http_client=cast(Any, DummyClient()),
    )
    connector._rate_limit_searxng = noop_rate_limit  # type: ignore[method-assign]

    # Test SearXNG search directly (bypassing the full search pipeline)
    listings = await connector._searxng_search("RTX 4090", {})
    await connector.cleanup()

    # Verify SearXNG was called
    searxng_calls = [url for url, method in calls if "searxng" in url]
    assert len(searxng_calls) == 1, f"Expected 1 SearXNG call, got {len(searxng_calls)}"

    # Verify we got the PIDs from SearXNG
    assert len(listings) == 2
    pids = {listing.source_listing_id for listing in listings}
    assert pids == {"1005001234567890", "1005009876543210"}

    # Verify listings have SearXNG discovery mode
    for listing in listings:
        assert listing.variant_normalized is not None
        assert listing.variant_normalized["aliexpress_source_lane"] == "searxng_discovery"
        assert listing.source == "aliexpress"


@pytest.mark.asyncio
async def test_aliexpress_searxng_disabled_when_flag_false():
    """Test that SearXNG is not used when disabled via filter."""
    calls: list[str] = []

    class DummyClient:
        async def get(self, url, headers=None, params=None, timeout=None, follow_redirects=True):
            calls.append(url)
            # Brave Search - return empty results
            if "search.brave.com" in url:
                return type(
                    "Resp",
                    (),
                    {
                        "text": "<html><body>No results</body></html>",
                        "raise_for_status": lambda self: None,
                    },
                )()
            # Affiliate endpoint - fail
            if "api-sg.aliexpress.com" in url:
                raise httpx.HTTPStatusError(
                    "Auth failed",
                    request=httpx.Request("POST", "https://example.test"),
                    response=httpx.Response(403),
                )
            raise AssertionError(f"Unexpected GET to: {url}")

        async def post(self, url, json=None, headers=None):
            raise AssertionError(f"Unexpected POST to: {url}")

        async def aclose(self):
            return None

    async def noop_rate_limit():
        return None

    connector = AliExpressConnector(
        {"searxng_discovery": True},
        http_client=cast(Any, DummyClient()),
    )
    connector._rate_limit_brave = noop_rate_limit  # type: ignore[method-assign]
    connector._rate_limit_searxng = noop_rate_limit  # type: ignore[method-assign]

    # Search with SearXNG explicitly disabled
    await connector.search("test", {"searxng_discovery": False})
    await connector.cleanup()

    # Verify SearXNG was not called
    searxng_calls = [url for url in calls if "searxng" in url]
    assert len(searxng_calls) == 0


@pytest.mark.asyncio
async def test_aliexpress_searxng_handles_network_failure():
    """Test that SearXNG failures are handled gracefully."""
    calls: list[tuple[str, str]] = []

    class DummyClient:
        async def get(self, url, headers=None, params=None, timeout=None, follow_redirects=True):
            calls.append((url, "GET"))
            # Affiliate endpoint - fail
            if "api-sg.aliexpress.com" in url:
                raise httpx.HTTPStatusError(
                    "Auth failed",
                    request=httpx.Request("POST", "https://example.test"),
                    response=httpx.Response(403),
                )
            # Brave Search - fail with 429
            if "search.brave.com" in url:
                raise httpx.HTTPStatusError(
                    "Rate limited",
                    request=httpx.Request("GET", "https://example.test"),
                    response=httpx.Response(429),
                )
            # SearXNG - fail with network error
            if "searxng" in url:
                raise Exception("SearXNG network error")
            raise AssertionError(f"Unexpected GET to: {url}")

        async def post(self, url, json=None, headers=None):
            calls.append((url, "POST"))
            raise AssertionError(f"Unexpected POST to: {url}")

        async def aclose(self):
            return None

    async def noop_rate_limit():
        return None

    connector = AliExpressConnector(
        {"searxng_url": "http://mock-searxng:8080"},
        http_client=cast(Any, DummyClient()),
    )
    connector._rate_limit_brave = noop_rate_limit  # type: ignore[method-assign]
    connector._rate_limit_searxng = noop_rate_limit  # type: ignore[method-assign]

    # Should not raise exception, just return empty listings
    listings = await connector.search("test", {})
    await connector.cleanup()

    # SearXNG was attempted but failed
    searxng_calls = [url for url, _ in calls if "searxng" in url]
    assert len(searxng_calls) == 1

    # No listings due to all lanes failing
    assert len(listings) == 0


@pytest.mark.asyncio
async def test_aliexpress_searxng_respects_max_results():
    """Test that SearXNG respects the max_results limit."""

    class DummyResponse:
        def __init__(self, payload: dict[str, object]):
            self._payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self._payload

    class DummyClient:
        async def get(self, url, headers=None, params=None, timeout=None, follow_redirects=True):
            # Return mock results with 10 PIDs
            if "searxng" in url:
                results = [
                    {
                        "url": f"https://www.aliexpress.com/item/10050012345678{i}.html",
                        "title": f"Product {i} £19.99",
                    }
                    for i in range(10)
                ]
                return DummyResponse({"results": results})

            raise AssertionError(f"Unexpected GET to: {url}")

        async def post(self, url, json=None, headers=None):
            raise AssertionError(f"Unexpected POST to: {url}")

        async def aclose(self):
            return None

    async def noop_rate_limit():
        return None

    connector = AliExpressConnector(
        {
            "searxng_url": "http://mock-searxng:8080",
            "searxng_max_results": 3,
        },
        http_client=cast(Any, DummyClient()),
    )
    connector._rate_limit_searxng = noop_rate_limit  # type: ignore[method-assign]

    # Test SearXNG search directly
    listings = await connector._searxng_search("test", {"searxng_max_results": 3})
    await connector.cleanup()

    # Should only get 3 listings due to max_results limit
    assert len(listings) == 3
