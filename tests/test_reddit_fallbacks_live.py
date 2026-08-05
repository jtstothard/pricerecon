"""Live integration tests for Reddit fallback chain.

These tests make real HTTP requests to Reddit and require credentials/environment
configuration. They are skipped by default in CI.

Run live tests with:
  pytest tests/test_reddit_fallbacks_live.py -m live

Or configure with environment variables:
  export PRICERECON_REDDIT_BROWSER_ENABLED=true
  export CAMOFOX_URL=your_camofox_url
  export CAMOFOX_API_KEY=your_api_key
  export CAMOFOX_ACCESS_KEY=your_access_key
  export CAMOFOX_USER_ID=your_user_id
  export CAMOFOX_SESSION_KEY=your_session_key
"""

from __future__ import annotations

from datetime import datetime, timezone

import os
import pytest

from pricerecon.connectors.reddit import (
    RedditHardwareSwapUKConnector,
    RedditBuildAPCSalesUKConnector,
)
from pricerecon.connectors.status import ConnectorDegradedError


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "live: marks tests as live integration tests (deselect with '-m \"not live\"')"
    )


def _browser_enabled() -> bool:
    """Check if browser testing is enabled."""
    return os.getenv("PRICERECON_REDDIT_BROWSER_ENABLED", "").strip().lower() in {
        "1",
        "true",
        "yes",
    } and (os.getenv("CAMOFOX_URL") or os.getenv("PRICERECON_CAMOFOX_URL"))


def _api_enabled() -> bool:
    """Check if API testing is enabled."""
    return (
        os.getenv("PRICERECON_REDDIT_API_ENABLED", "").strip().lower() in {"1", "true", "yes"}
        and os.getenv("REDDIT_CLIENT_ID")
        and os.getenv("REDDIT_CLIENT_SECRET")
        and os.getenv("REDDIT_USER_AGENT")
    )


@pytest.mark.live
@pytest.mark.asyncio
@pytest.mark.skipif(
    not _browser_enabled(),
    reason="Browser not configured - set PRICERECON_REDDIT_BROWSER_ENABLED and CAMOFOX_* env vars",
)
async def test_live_browser_fallback_fetches_real_posts() -> None:
    """Live test: browser tier fetches real posts from r/test.

    This verifies:
    - Browser client successfully navigates to Reddit
    - HTML/JSON parsing works on real content
    - Listings are normalized correctly
    - Field names and types match expected schema
    """
    connector = RedditHardwareSwapUKConnector()

    try:
        # Try to fetch from a low-traffic subreddit
        listings = await connector._search_browser("test", {"limit": 5})
    except ConnectorDegradedError as exc:
        pytest.skip(f"Browser test degraded: {exc.message} (status: {exc.status.value})")

    # Verify we got listings
    assert isinstance(listings, list), "Browser should return a list of listings"

    if not listings:
        pytest.skip("No listings returned from r/test (subreddit may be empty)")

    # Verify normalization for each listing
    for listing in listings:
        # Check required fields exist and have correct types
        assert hasattr(listing, "title_raw"), "Listing must have title_raw"
        assert hasattr(listing, "url"), "Listing must have url"
        assert hasattr(listing, "source"), "Listing must have source"
        assert hasattr(listing, "source_type"), "Listing must have source_type"
        assert hasattr(listing, "timestamp_seen"), "Listing must have timestamp_seen"

        # Verify field values
        assert listing.source == "reddit_hardwareswapuk"
        assert isinstance(listing.title_raw, str)
        assert len(listing.title_raw) > 0
        assert isinstance(listing.url, str)
        assert listing.url.startswith("https://www.reddit.com/")

        # Verify timestamp is timezone-aware
        assert listing.timestamp_seen is not None
        assert isinstance(listing.timestamp_seen, datetime)
        assert listing.timestamp_seen.tzinfo == timezone.utc

    print(f"\nLive browser test: Successfully fetched {len(listings)} listings from Reddit")


@pytest.mark.live
@pytest.mark.asyncio
@pytest.mark.skipif(
    not _browser_enabled(),
    reason="Browser not configured - set PRICERECON_REDDIT_BROWSER_ENABLED and CAMOFOX_* env vars",
)
async def test_live_browser_multiple_subreddits_work() -> None:
    """Live test: browser tier works across different Reddit subreddits."""
    connectors = [
        RedditHardwareSwapUKConnector(),
        RedditBuildAPCSalesUKConnector(),
    ]

    results = {}

    for connector in connectors:
        try:
            listings = await connector._search_browser("test", {"limit": 3})
            results[connector.connector_id] = {
                "count": len(listings),
                "sample_url": listings[0].url if listings else None,
            }
        except ConnectorDegradedError as exc:
            results[connector.connector_id] = {
                "error": exc.message,
                "status": exc.status.value,
            }

    # At least one connector should succeed
    successful = [k for k, v in results.items() if "error" not in v]
    if not successful:
        pytest.skip(f"All connectors failed: {results}")

    # Verify successful results
    for conn_id in successful:
        result = results[conn_id]
        assert result["count"] > 0, f"{conn_id} returned empty results"
        assert result["sample_url"].startswith("https://www.reddit.com/")

    print(f"\nLive multi-subreddit test results: {results}")


@pytest.mark.live
@pytest.mark.asyncio
@pytest.mark.skipif(
    not _api_enabled(),
    reason="API not configured - set PRICERECON_REDDIT_API_ENABLED and REDDIT_* env vars",
)
async def test_live_api_fallback_fetches_real_posts() -> None:
    """Live test: API tier fetches real posts and normalizes correctly.

    This verifies:
    - OAuth token flow works with real Reddit API
    - JSON response parsing works on real content
    - Rate limit headers are extracted correctly
    - Listings are normalized to match RSS/browser schema
    """
    connector = RedditHardwareSwapUKConnector()

    try:
        listings = await connector._search_api("test", {"limit": 5})
    except ConnectorDegradedError as exc:
        pytest.skip(f"API test degraded: {exc.message} (status: {exc.status.value})")

    # Verify we got listings
    assert isinstance(listings, list), "API should return a list of listings"

    if not listings:
        pytest.skip("No listings returned from API (subreddit may be empty)")

    # Verify normalization
    for listing in listings:
        assert hasattr(listing, "title_raw")
        assert hasattr(listing, "url")
        assert hasattr(listing, "source")
        assert hasattr(listing, "timestamp_seen")

        assert isinstance(listing.title_raw, str)
        assert len(listing.title_raw) > 0
        assert isinstance(listing.url, str)
        assert listing.url.startswith("https://www.reddit.com/")

        # Verify timestamp is timezone-aware
        assert listing.timestamp_seen is not None
        assert isinstance(listing.timestamp_seen, datetime)
        assert listing.timestamp_seen.tzinfo == timezone.utc

    # Verify rate limit info was captured
    if connector._last_rate_limit_info:
        assert (
            "remaining" in connector._last_rate_limit_info
            or "used" in connector._last_rate_limit_info
        )
        print(f"\nLive API test: Rate limit info captured: {connector._last_rate_limit_info}")

    print(f"\nLive API test: Successfully fetched {len(listings)} listings from Reddit API")


@pytest.mark.live
@pytest.mark.asyncio
@pytest.mark.skipif(
    not (_browser_enabled() or _api_enabled()), reason="No fallback tier configured"
)
async def test_live_fallback_schema_consistency() -> None:
    """Live test: all active tiers produce identically-shaped NormalizedListing objects.

    This runs live calls to each configured tier and verifies the output schemas match.
    """
    field_sets = {}

    # Test browser if enabled
    if _browser_enabled():
        connector = RedditHardwareSwapUKConnector()
        try:
            browser_listings = await connector._search_browser("test", {"limit": 3})
            if browser_listings:
                field_sets["browser"] = set(
                    browser_listings[0].model_dump(exclude_none=True).keys()
                )
        except ConnectorDegradedError as exc:
            print(f"Browser degraded: {exc.message}")

    # Test API if enabled
    if _api_enabled():
        connector = RedditHardwareSwapUKConnector()
        try:
            api_listings = await connector._search_api("test", {"limit": 3})
            if api_listings:
                field_sets["api"] = set(api_listings[0].model_dump(exclude_none=True).keys())
        except ConnectorDegradedError as exc:
            print(f"API degraded: {exc.message}")

    # If we have data from multiple tiers, verify consistency
    if len(field_sets) >= 2:
        first_fields = list(field_sets.values())[0]
        for tier, fields in field_sets.items():
            assert (
                fields == first_fields
            ), f"Field mismatch for {tier}: {fields - first_fields} extra, {first_fields - fields} missing"
        print("\nLive schema consistency test: All tiers produce identical fields")
    else:
        pytest.skip(
            f"Need at least 2 active tiers for schema comparison, got: {list(field_sets.keys())}"
        )


# Documentation for running live tests
LIVE_TEST_DOCS = """
=== Running Live Reddit Fallback Tests ===

Live tests make real HTTP requests to Reddit and require credentials.

Prerequisites:

For Browser tests:
  export PRICERECON_REDDIT_BROWSER_ENABLED=true
  export CAMOFOX_URL=your_camofox_url
  export CAMOFOX_API_KEY=your_api_key
  export CAMOFOX_ACCESS_KEY=your_access_key
  export CAMOFOX_USER_ID=your_user_id
  export CAMOFOX_SESSION_KEY=your_session_key

For API tests:
  export PRICERECON_REDDIT_API_ENABLED=true
  export REDDIT_CLIENT_ID=your_client_id
  export REDDIT_CLIENT_SECRET=your_client_secret
  export REDDIT_USER_AGENT=your_user_agent

Running the tests:

  # Run only live tests
  pytest tests/test_reddit_fallbacks_live.py -m live -v

  # Run all tests including live
  pytest tests/ -v

  # Skip live tests (default in CI)
  pytest tests/ -v -m "not live"

Notes:
- Live tests use low-traffic subreddits (r/test) to minimize impact
- Tests are marked with pytest.mark.live for easy filtering
- Tests will be skipped if credentials are not configured
- Failures in live tests are logged but don't block CI
"""
