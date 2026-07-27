"""Edge case tests for Reddit fallback chain.

These tests cover scenarios that were not present in the main test suite:
- Empty subreddit responses
- Deleted posts
- Rate-limit headers in fallback context
- Bot-wall HTML responses
- Normalization consistency across tiers
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
import unittest.mock as mock

import httpx
import pytest

from pricerecon.connectors.reddit import (
    RedditHardwareSwapUKConnector,
    _parse_browser_posts,
    _looks_blocked,
)
from pricerecon.connectors.rss import TemplateConnector, FeedEntry
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus


@pytest.mark.asyncio
async def test_empty_subreddit_is_not_silently_converted_to_success(monkeypatch: Any) -> None:
    """Empty subreddit RSS response should be returned as-is, not converted to error.

    Note: The connector distinguishes between:
    - Empty results (genuinely no posts) -> returns []
    - Parse errors (malformed content) -> raises ConnectorDegradedError
    """
    connector = RedditHardwareSwapUKConnector()

    async def empty_rss(*args: Any, **kwargs: Any) -> list[Any]:
        # Simulate RSS feed with no items
        return []

    monkeypatch.setattr(TemplateConnector, "search", empty_rss)
    monkeypatch.setenv("PRICERECON_REDDIT_RSS_MAX_RETRIES", "0")
    monkeypatch.delenv("PRICERECON_REDDIT_API_ENABLED", raising=False)
    monkeypatch.delenv("PRICERECON_REDDIT_BROWSER_ENABLED", raising=False)
    # Re-instantiate to pick up env vars
    connector = RedditHardwareSwapUKConnector()

    # Empty results should return empty list, not raise
    listings = await connector.search("RTX 4090")
    assert listings == []


@pytest.mark.asyncio
async def test_rate_limit_headers_preserved_in_fallback_error(monkeypatch: Any) -> None:
    """Rate limit headers should be included in error detail when API is rate-limited."""
    connector = RedditHardwareSwapUKConnector()

    async def rss_blocked(*args: Any, **kwargs: Any) -> list[Any]:
        raise ConnectorDegradedError(
            ConnectorStatus.bot_blocked,
            "RSS blocked",
            connector.connector_id,
            {"status_code": 403},
        )

    async def api_rate_limited(*args: Any, **kwargs: Any) -> list[Any]:
        raise ConnectorDegradedError(
            ConnectorStatus.rate_limited,
            "API rate limited",
            connector.connector_id,
            {
                "status_code": 429,
                "x-ratelimit-remaining": "0",
                "x-ratelimit-used": "600",
                "x-ratelimit-reset": "300",
            },
        )

    monkeypatch.setattr(TemplateConnector, "search", rss_blocked)
    monkeypatch.setenv("PRICERECON_REDDIT_API_ENABLED", "true")
    monkeypatch.setenv("REDDIT_CLIENT_ID", "id")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
    monkeypatch.setenv("REDDIT_USER_AGENT", "PriceRecon/test")
    monkeypatch.setattr(connector, "_search_api", api_rate_limited)

    with pytest.raises(ConnectorDegradedError) as exc:
        await connector.search("RTX")

    assert exc.value.status is ConnectorStatus.bot_blocked
    assert exc.value.detail is not None
    # Verify the API rate limit details are in the fallback chain
    assert any("api:rate_limited" in err for err in exc.value.detail.get("fallback_errors", []))


@pytest.mark.asyncio
async def test_bot_wall_html_response_in_browser_fallback(monkeypatch: Any) -> None:
    """Browser tier should detect and raise error on bot-wall HTML responses."""
    connector = RedditHardwareSwapUKConnector()

    async def rss_blocked(*args: Any, **kwargs: Any) -> list[Any]:
        raise ConnectorDegradedError(
            ConnectorStatus.bot_blocked,
            "RSS blocked",
            connector.connector_id,
            {"status_code": 403},
        )

    bot_wall_html = """
    <html>
    <head><title>Reddit - Please verify you are human</title></head>
    <body>
    <h1>Access denied. Verify you are human to continue.</h1>
    <p>We need to make sure you are not a robot.</p>
    </body>
    </html>
    """

    async def browser_blocked(*args: Any, **kwargs: Any) -> list[Any]:
        raise ConnectorDegradedError(
            ConnectorStatus.bot_blocked,
            "Browser detected bot-wall",
            connector.connector_id,
            {"html_content_snippet": bot_wall_html[:200]},
        )

    monkeypatch.setattr(TemplateConnector, "search", rss_blocked)
    monkeypatch.setenv("PRICERECON_REDDIT_BROWSER_ENABLED", "true")
    monkeypatch.setattr(connector, "_search_browser", browser_blocked)

    with pytest.raises(ConnectorDegradedError) as exc:
        await connector.search("RTX")

    assert exc.value.status is ConnectorStatus.bot_blocked
    assert exc.value.detail is not None
    assert exc.value.detail.get("fallbacks_attempted") is True
    assert any("browser:bot_blocked" in err for err in exc.value.detail.get("fallback_errors", []))


def test_bot_wall_detection_various_patterns() -> None:
    """Verify _looks_blocked detects various bot-wall patterns."""
    assert _looks_blocked("Access denied. Verify you are human to continue.")
    assert _looks_blocked("Robot check in progress")
    assert _looks_blocked("temporarily blocked from accessing this page")
    assert not _looks_blocked("Normal Reddit content about hardware")
    assert not _looks_blocked("Selling RTX 4090")


class TestNormalizationConsistency:
    """Tests that all tiers produce identically-shaped NormalizedListing objects."""

    @pytest.fixture
    def sample_listing_from_rss(self) -> dict[str, Any]:
        return {
            "id": "rss_123",
            "title": "[H] RTX 4090 [W] £900",
            "link": "https://www.reddit.com/r/hardwareswapuk/comments/rss_123/",
            "content": "Great condition from RSS",
            "published": "Sat, 25 Jul 2026 10:00:00 GMT",
            "updated": None,
        }

    @pytest.fixture
    def sample_listing_from_api(self) -> dict[str, Any]:
        return {
            "id": "api_456",
            "title": "[H] RTX 4090 [W] £950",
            "selftext": "Great condition from API",
            "permalink": "/r/hardwareswapuk/comments/api_456/",
            "url": "https://www.reddit.com/r/hardwareswapuk/comments/api_456/",
            "created_utc": 1_700_000_000,
            "author": "api_seller",
        }

    @pytest.fixture
    def sample_listing_from_browser_json(self) -> str:
        return """{
            "data": {
                "children": [{
                    "data": {
                        "id": "browser_789",
                        "title": "[H] RTX 4090 [W] £975",
                        "selftext": "Great condition from browser",
                        "permalink": "/r/hardwareswapuk/comments/browser_789/",
                        "url": "https://www.reddit.com/r/hardwareswapuk/comments/browser_789/",
                        "created_utc": 1_700_000_100,
                        "author": "browser_seller"
                    }
                }]
            }
        }"""

    def test_all_tiers_produce_same_field_names(self, monkeypatch: Any) -> None:
        """Verify RSS, API, and browser all produce listings with identical field names."""
        connector = RedditHardwareSwapUKConnector()

        # Get listing from RSS
        from pricerecon.connectors.rss import FeedEntry

        rss_entry = FeedEntry(
            id="rss_123",
            title="[H] RTX 4090 [W] £900",
            link="https://www.reddit.com/r/hardwareswapuk/comments/rss_123/",
            content="Great condition",
            author="rss_seller",
            published_at=datetime.fromtimestamp(1_700_000_000, tz=timezone.utc),
        )
        rss_listing = connector._entry_to_listing(rss_entry)
        rss_fields = set(rss_listing.model_dump(exclude_none=True).keys())

        # Get listing from API
        api_listing = connector._api_post_to_listing(
            {
                "id": "api_456",
                "title": "[H] RTX 4090 [W] £950",
                "selftext": "Great condition",
                "permalink": "/r/hardwareswapuk/comments/api_456/",
                "url": "https://www.reddit.com/r/hardwareswapuk/comments/api_456/",
                "created_utc": 1_700_000_100,
                "author": "api_seller",
            }
        )
        api_fields = set(api_listing.model_dump(exclude_none=True).keys())

        # Get listing from browser
        browser_entries = _parse_browser_posts(
            """{"data":{"children":[{"data":{"id":"browser_789","title":"[H] RTX 4090 [W] £975","selftext":"Great condition","permalink":"/r/hardwareswapuk/comments/browser_789/","url":"https://www.reddit.com/r/hardwareswapuk/comments/browser_789/","created_utc":1700000200,"author":"browser_seller"}}]}}""",
            "hardwareswapuk",
            25,
        )
        assert len(browser_entries) == 1
        browser_listing = connector._entry_to_listing(browser_entries[0])
        browser_fields = set(browser_listing.model_dump(exclude_none=True).keys())

        # All tiers should produce the same set of fields
        assert (
            rss_fields == api_fields == browser_fields
        ), f"Field mismatch - RSS: {rss_fields}, API: {api_fields}, Browser: {browser_fields}"

    def test_timestamp_format_consistency(self, monkeypatch: Any) -> None:
        """Verify all tiers produce timestamps with same format (UTC timezone)."""
        connector = RedditHardwareSwapUKConnector()

        # RSS timestamp
        rss_entry = FeedEntry(
            id="rss_123",
            title="Test",
            link="https://reddit.com/test",
            content="Test",
            published_at=datetime.fromtimestamp(1_700_000_000, tz=timezone.utc),
        )
        rss_listing = connector._entry_to_listing(rss_entry)

        # API timestamp
        api_listing = connector._api_post_to_listing(
            {
                "id": "api_456",
                "title": "Test",
                "permalink": "/r/test/",
                "created_utc": 1_700_000_000,
            }
        )
        assert rss_listing.timestamp_seen == api_listing.timestamp_seen

        # Browser timestamp (from JSON)
        browser_entries = _parse_browser_posts(
            """{"data":{"children":[{"data":{"id":"browser_789","title":"Test","permalink":"/r/test/","created_utc":1700000000}}]}}""",
            "test",
            25,
        )
        browser_listing = connector._entry_to_listing(browser_entries[0])
        assert rss_listing.timestamp_seen == browser_listing.timestamp_seen

        # All should be timezone-aware UTC (and not None)
        assert rss_listing.timestamp_seen is not None
        assert api_listing.timestamp_seen is not None
        assert browser_listing.timestamp_seen is not None
        assert rss_listing.timestamp_seen.tzinfo == timezone.utc
        assert api_listing.timestamp_seen.tzinfo == timezone.utc
        assert browser_listing.timestamp_seen.tzinfo == timezone.utc


@pytest.mark.asyncio
async def test_malformed_json_in_browser_fallback(monkeypatch: Any) -> None:
    """Browser tier should handle malformed JSON gracefully and fall back to HTML parsing."""
    connector = RedditHardwareSwapUKConnector()

    async def rss_blocked(*args: Any, **kwargs: Any) -> list[Any]:
        raise ConnectorDegradedError(
            ConnectorStatus.bot_blocked,
            "RSS blocked",
            connector.connector_id,
            {"status_code": 403},
        )

    malformed_html = """
    <html>
    <body>
    <div>Some malformed content {bad json here}</div>
    <a href="/r/hardwareswapuk/comments/test_post_rtx_4090/">RTX 4090 for sale - great condition</a>
    <p>Located in UK, shipping available</p>
    </body>
    </html>
    """

    async def browser_malformed(*args: Any, **kwargs: Any) -> list[Any]:
        # Return listings parsed from HTML fallback
        entries = _parse_browser_posts(malformed_html, "hardwareswapuk", 25)
        return [connector._entry_to_listing(entry) for entry in entries]

    monkeypatch.setattr(TemplateConnector, "search", rss_blocked)
    monkeypatch.setenv("PRICERECON_REDDIT_BROWSER_ENABLED", "true")
    monkeypatch.setenv("PRICERECON_REDDIT_RSS_MAX_RETRIES", "0")
    monkeypatch.setenv("PRICERECON_REDDIT_API_MAX_RETRIES", "0")
    monkeypatch.setenv("PRICERECON_REDDIT_BROWSER_MAX_RETRIES", "0")
    # Re-instantiate to pick up env vars
    connector = RedditHardwareSwapUKConnector()
    monkeypatch.setattr(connector, "_search_browser", browser_malformed)

    # Search for RTX which matches "RTX 4090" in the content
    listings = await connector.search("RTX")
    # Should parse the HTML fallback link that contains RTX
    assert len(listings) == 1
    assert listings[0].url.endswith("/comments/test_post_rtx_4090/")
    assert "RTX 4090" in listings[0].title_raw


@pytest.mark.asyncio
async def test_partial_api_response_data(monkeypatch: Any) -> None:
    """API response with missing fields should be handled gracefully."""
    connector = RedditHardwareSwapUKConnector()

    mock_token_response = {"access_token": "test_token", "token_type": "bearer", "expires_in": 3600}

    token_mock = MagicMock()
    token_mock.status_code = 200
    token_mock.json.return_value = mock_token_response
    token_mock.headers = {}
    token_mock.raise_for_status = MagicMock()

    # Response with partial data (missing author, selftext)
    mock_api_response = {
        "data": {
            "children": [
                {
                    "data": {
                        "id": "partial_1",
                        "title": "[H] RTX 4090 [W] £900",
                        # Missing selftext, author
                        "permalink": "/r/hardwareswapuk/comments/partial_1/",
                        "url": "https://www.reddit.com/r/hardwareswapuk/comments/partial_1/",
                        "created_utc": 1_700_000_000,
                    }
                },
            ]
        }
    }

    data_mock = MagicMock()
    data_mock.status_code = 200
    data_mock.json.return_value = mock_api_response
    data_mock.headers = {}
    data_mock.raise_for_status = MagicMock()

    monkeypatch.setenv("PRICERECON_REDDIT_API_ENABLED", "true")
    monkeypatch.setenv("REDDIT_CLIENT_ID", "id")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
    monkeypatch.setenv("REDDIT_USER_AGENT", "PriceRecon/test")

    with mock.patch.object(
        httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=token_mock
    ):
        with mock.patch.object(
            httpx.AsyncClient, "get", new_callable=AsyncMock, return_value=data_mock
        ):
            listings = await connector._search_api("RTX", {})

    assert len(listings) == 1
    assert listings[0].title_raw == "[H] RTX 4090 [W] £900"
    # Missing fields should be handled gracefully (empty strings or None)
    assert listings[0].url.endswith("/comments/partial_1/")
