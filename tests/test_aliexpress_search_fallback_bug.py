"""
Phase 1 diagnostic test for AliExpress connector: reproduce the 0-results bug.

This test is meant to FAIL on current code, showing that when both affiliate and
Brave lanes fail, we get 0 results even though DS credentials are available.
"""

import pytest
from typing import cast
from pricerecon.connectors.aliexpress import AliExpressConnector
from pricerecon.connectors.status import ConnectorDegradedError
import httpx


class MockAffiliateFailingResponse:
    """Mock response that simulates InsufficientPermission error from affiliate API."""

    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code
        self.headers: dict[str, str] = {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "boom",
                request=httpx.Request("POST", "https://example.test"),
                response=httpx.Response(self.status_code),
            )

    def json(self) -> dict[str, object]:
        return {
            "error_response": {
                "code": "InsufficientPermission",
                "msg": "App does not have permission to access this api"
            }
        }


class MockBraveRateLimitedResponse:
    """Mock response that simulates 429 rate limit from Brave Search."""

    def __init__(self, status_code: int = 429) -> None:
        self.status_code = status_code
        self.headers: dict[str, str] = {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "boom",
                request=httpx.Request("GET", "https://search.brave.com/search"),
                response=httpx.Response(self.status_code),
            )

    text = ""


class MockClient:
    """Mock HTTP client that fails on affiliate and Brave, but has DS creds available."""

    def __init__(self) -> None:
        self.post_call_count = 0
        self.get_call_count = 0

    async def post(
        self, url: str, json: object = None, headers: object = None, data: object = None
    ) -> MockAffiliateFailingResponse:
        self.post_call_count += 1
        # Affiliate endpoint always fails with InsufficientPermission
        return MockAffiliateFailingResponse()

    async def get(self, url: str, params: object = None, headers: object = None, timeout: object = None) -> MockBraveRateLimitedResponse:
        self.get_call_count += 1
        # Brave search always fails with 429
        return MockBraveRateLimitedResponse()

    async def aclose(self) -> None:
        return None


@pytest.mark.asyncio
async def test_aliexpress_returns_zero_when_affiliate_and_brave_fail() -> None:
    """
    REPRODUCE BUG: When affiliate API fails (InsufficientPermission) and
    Brave Search is rate-limited (429), the connector returns 0 results.

    This test expects 0 listings from search(), which reproduces the bug
    reported in the Kanban task. The bug is that even though DS credentials
    are available, the connector doesn't use them to perform a DS search.

    Expected behavior (BEFORE fix): 0 listings (BUG)
    Expected behavior (AFTER fix): >0 listings via DS search
    """

    mock_client = MockClient()

    connector = AliExpressConnector(
        {
            "app_key": "test-key",
            "app_secret": "test-secret",
            "affiliate_currency": "GBP",
            # DS credentials are available but not used for search
            "ds_app_key": "test-ds-key",
            "ds_app_secret": "test-ds-secret",
            "ds_access_token": "test-access-token",
            "ds_refresh_token": "test-refresh-token",
        },
        http_client=cast(httpx.AsyncClient, mock_client),
    )

    # Perform a generic search query
    listings = await connector.search("RTX 3060", {})

    # BEFORE FIX: This assertion passes (0 listings - BUG)
    # AFTER FIX: This assertion fails (>0 listings - FIXED)
    assert len(listings) == 0, f"Expected 0 listings (bug reproduced), got {len(listings)}"

    # Verify the lanes that were called
    assert mock_client.post_call_count > 0, "Affiliate API should have been called"
    assert mock_client.get_call_count > 0, "Brave Search should have been called"

    await connector.cleanup()


@pytest.mark.asyncio
async def test_aliexpress_should_use_ds_search_when_affiliate_and_brave_fail() -> None:
    """
    HYPOTHESIS TEST: DS search should be used when affiliate and Brave fail.

    This test is a placeholder for the fix. It documents what SHOULD happen:
    - Affiliate lane fails (InsufficientPermission)
    - Brave lane fails (429)
    - DS search lane succeeds and returns listings

    The fix should:
    1. Add a DS search endpoint/method (if exists in AliExpress DS API)
    2. Call it when affiliate and Brave fail
    3. Return listings from DS search

    This test will FAIL until the fix is implemented.
    """

    mock_client = MockClient()

    connector = AliExpressConnector(
        {
            "app_key": "test-key",
            "app_secret": "test-secret",
            "affiliate_currency": "GBP",
            # DS credentials should enable DS search as a fallback
            "ds_app_key": "test-ds-key",
            "ds_app_secret": "test-ds-secret",
            "ds_access_token": "test-access-token",
            "ds_refresh_token": "test-refresh-token",
            "enrich_with_ds": True,  # DS enrichment is enabled
        },
        http_client=cast(httpx.AsyncClient, mock_client),
    )

    # Perform a generic search query
    listings = await connector.search("RTX 3060", {})

    # AFTER FIX: This assertion should pass (>0 listings from DS search)
    assert len(listings) > 0, "DS search should return listings when affiliate and Brave fail"

    # Verify listings came from DS (check variant metadata)
    if listings:
        ds_listings = [l for l in listings if l.variant_normalized and l.variant_normalized.get("aliexpress_source_lane") == "ds"]
        assert len(ds_listings) > 0, "At least one listing should be from DS lane"

    await connector.cleanup()