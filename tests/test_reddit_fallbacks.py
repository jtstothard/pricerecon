from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
import unittest.mock as mock

import httpx
import pytest

from pricerecon.connectors.reddit import (
    RedditHardwareSwapUKConnector,
    _parse_browser_posts,
)
from pricerecon.connectors import reddit as reddit_module
from pricerecon.connectors.rss import TemplateConnector
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus


@pytest.fixture
def mock_api_response() -> dict[str, Any]:
    """Mock successful Reddit API response."""
    return {
        "data": {
            "children": [
                {
                    "data": {
                        "id": "abc123",
                        "title": "[H] RTX 4090 [W] £900",
                        "selftext": "Great condition, works perfectly",
                        "permalink": "/r/hardwareswapuk/comments/abc123/post/",
                        "url": "https://www.reddit.com/r/hardwareswapuk/comments/abc123/post/",
                        "created_utc": 1_700_000_000,
                        "author": "seller123",
                    }
                },
                {
                    "data": {
                        "id": "def456",
                        "title": "[H] RTX 4080 [W] £700",
                        "selftext": "Used but good condition",
                        "permalink": "/r/hardwareswapuk/comments/def456/post/",
                        "url": "https://www.reddit.com/r/hardwareswapuk/comments/def456/post/",
                        "created_utc": 1_700_000_100,
                        "author": "seller456",
                    }
                },
            ]
        }
    }


@pytest.fixture
def mock_token_response() -> dict[str, Any]:
    """Mock successful Reddit token response."""
    return {"access_token": "test_token_12345", "token_type": "bearer", "expires_in": 3600}


@pytest.mark.asyncio
async def test_reddit_api_fallback_preserves_normalization(monkeypatch: Any) -> None:
    connector = RedditHardwareSwapUKConnector()
    rss_error = ConnectorDegradedError(
        ConnectorStatus.bot_blocked,
        "RSS blocked",
        connector.connector_id,
        {"status_code": 403},
    )

    async def blocked(*args: Any, **kwargs: Any) -> list[Any]:
        raise rss_error

    async def api(*args: Any, **kwargs: Any) -> list[Any]:
        return [
            connector._api_post_to_listing(
                {
                    "id": "abc",
                    "title": "[H] RTX 4090 [W] £900",
                    "selftext": "Great condition",
                    "permalink": "/r/hardwareswapuk/comments/abc/post/",
                    "created_utc": 1_700_000_000,
                    "author": "seller",
                }
            )
        ]

    monkeypatch.setattr(TemplateConnector, "search", blocked)
    monkeypatch.setenv("PRICERECON_REDDIT_API_ENABLED", "true")
    monkeypatch.setenv("REDDIT_CLIENT_ID", "id")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
    monkeypatch.setenv("REDDIT_USER_AGENT", "PriceRecon/test")
    monkeypatch.setattr(connector, "_search_api", api)

    listings = await connector.search("RTX 4090")
    assert len(listings) == 1
    assert listings[0].title_raw == "[H] RTX 4090 [W] £900"
    assert listings[0].price == 900
    assert listings[0].url.endswith("/comments/abc/post/")
    assert listings[0].timestamp_seen == datetime.fromtimestamp(1_700_000_000, tz=timezone.utc)


@pytest.mark.asyncio
async def test_reddit_block_is_not_silently_converted_to_empty(monkeypatch: Any) -> None:
    connector = RedditHardwareSwapUKConnector()

    async def blocked(*args: Any, **kwargs: Any) -> list[Any]:
        raise ConnectorDegradedError(
            ConnectorStatus.rate_limited,
            "RSS limited",
            connector.connector_id,
            {"status_code": 429},
        )

    monkeypatch.setattr(TemplateConnector, "search", blocked)
    with pytest.raises(ConnectorDegradedError) as raised:
        await connector.search("RTX")
    assert raised.value.status is ConnectorStatus.rate_limited
    assert raised.value.detail is not None
    assert raised.value.detail["status_code"] == 429
    assert raised.value.detail["fallbacks_attempted"] is False
    assert [
        (stage["stage"], stage["outcome"]) for stage in raised.value.detail["fallback_stages"]
    ] == [("rss", "attempted"), ("rss", "failed"), ("api", "skipped"), ("browser", "skipped")]


def test_browser_snapshot_parser_normalizes_post_identity() -> None:
    entries = _parse_browser_posts(
        '<article><a href="/r/hardwareswapuk/comments/abc/post/">[H] RTX 4090 [W] £900</a></article>',
        "hardwareswapuk",
        25,
    )
    assert len(entries) == 1
    assert entries[0].id
    assert entries[0].link == "https://www.reddit.com/r/hardwareswapuk/comments/abc/post/"
    assert entries[0].title == "[H] RTX 4090 [W] £900"


@pytest.mark.asyncio
async def test_api_unexpected_error_does_not_prevent_browser_fallback(monkeypatch: Any) -> None:
    connector = RedditHardwareSwapUKConnector()

    async def blocked(*args: Any, **kwargs: Any) -> list[Any]:
        raise ConnectorDegradedError(
            ConnectorStatus.bot_blocked, "RSS blocked", connector.connector_id
        )

    async def api(*args: Any, **kwargs: Any) -> list[Any]:
        raise ValueError("malformed API payload")

    async def browser(*args: Any, **kwargs: Any) -> list[Any]:
        return [
            connector._api_post_to_listing(
                {
                    "id": "browser",
                    "title": "RTX 4090",
                    "url": "https://www.reddit.com/r/hardwareswapuk/comments/browser/post",
                }
            )
        ]

    monkeypatch.setattr(TemplateConnector, "search", blocked)
    monkeypatch.setenv("PRICERECON_REDDIT_API_ENABLED", "true")
    monkeypatch.setenv("REDDIT_CLIENT_ID", "id")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
    monkeypatch.setenv("REDDIT_USER_AGENT", "PriceRecon/test")
    monkeypatch.setenv("PRICERECON_REDDIT_BROWSER_ENABLED", "true")
    monkeypatch.setattr(connector, "_search_api", api)
    monkeypatch.setattr(connector, "_search_browser", browser)

    listings = await connector.search("RTX 4090")
    assert len(listings) == 1
    assert listings[0].url.endswith("/comments/browser/post")


def test_browser_block_page_is_not_treated_as_empty_results() -> None:
    from pricerecon.connectors.reddit import _looks_blocked

    assert _looks_blocked("Access denied. Verify you are human to continue.")


def test_browser_json_parser_extracts_body_and_timestamp() -> None:
    entries = _parse_browser_posts(
        '{"data":{"children":[{"data":{"id":"abc","title":"RTX 4090","selftext":"Like new",'
        '"permalink":"/r/hardwareswapuk/comments/abc/post/","created_utc":1700000000}}]}}',
        "hardwareswapuk",
        25,
    )
    assert len(entries) == 1
    assert entries[0].content == "Like new"
    assert entries[0].published_at == datetime.fromtimestamp(1700000000, tz=timezone.utc)


@pytest.mark.asyncio
async def test_rss_transport_failure_reaches_api(monkeypatch: Any) -> None:
    connector = RedditHardwareSwapUKConnector()
    calls: list[str] = []

    async def rss(*args: Any, **kwargs: Any) -> list[Any]:
        raise httpx.ConnectError("RSS unavailable")

    async def api(*args: Any, **kwargs: Any) -> list[Any]:
        calls.append("api")
        return []

    monkeypatch.setattr(TemplateConnector, "search", rss)
    monkeypatch.setenv("PRICERECON_REDDIT_API_ENABLED", "true")
    monkeypatch.setenv("REDDIT_CLIENT_ID", "id")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
    monkeypatch.setenv("REDDIT_USER_AGENT", "PriceRecon/test")
    monkeypatch.setattr(connector, "_search_api", api)

    assert await connector.search("RTX") == []
    assert calls == ["api"]


@pytest.mark.asyncio
async def test_api_failure_reaches_browser(
    monkeypatch: Any, caplog: pytest.LogCaptureFixture
) -> None:
    connector = RedditHardwareSwapUKConnector()
    calls: list[str] = []

    async def rss(*args: Any, **kwargs: Any) -> list[Any]:
        raise ConnectorDegradedError(
            ConnectorStatus.bot_blocked, "RSS blocked", connector.connector_id
        )

    async def api(*args: Any, **kwargs: Any) -> list[Any]:
        calls.append("api")
        raise ConnectorDegradedError(
            ConnectorStatus.auth_failed, "API unavailable", connector.connector_id
        )

    async def browser(*args: Any, **kwargs: Any) -> list[Any]:
        calls.append("browser")
        return [
            connector._api_post_to_listing(
                {
                    "id": "browser",
                    "title": "RTX 4090",
                    "url": "https://www.reddit.com/r/hardwareswapuk/comments/browser/post",
                }
            )
        ]

    monkeypatch.setattr(TemplateConnector, "search", rss)
    monkeypatch.setenv("PRICERECON_REDDIT_API_ENABLED", "true")
    monkeypatch.setenv("REDDIT_CLIENT_ID", "id")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
    monkeypatch.setenv("REDDIT_USER_AGENT", "PriceRecon/test")
    monkeypatch.setenv("PRICERECON_REDDIT_BROWSER_ENABLED", "true")
    monkeypatch.setattr(connector, "_search_api", api)
    monkeypatch.setattr(connector, "_search_browser", browser)

    with caplog.at_level("INFO", logger=reddit_module.__name__):
        assert len(await connector.search("RTX 4090")) == 1
    assert calls == ["api", "browser"]
    stages = [
        (getattr(record, "stage"), getattr(record, "outcome"))
        for record in caplog.records
        if record.name == reddit_module.__name__ and record.msg == "reddit_fallback_stage"
    ]
    assert stages == [
        ("rss", "attempted"),
        ("rss", "failed"),
        ("api", "attempted"),
        ("api", "failed"),
        ("browser", "attempted"),
        ("browser", "succeeded"),
    ]


@pytest.mark.asyncio
async def test_browser_failure_returns_structured_degraded_error(monkeypatch: Any) -> None:
    connector = RedditHardwareSwapUKConnector()

    async def rss(*args: Any, **kwargs: Any) -> list[Any]:
        raise ConnectorDegradedError(
            ConnectorStatus.rate_limited, "RSS limited", connector.connector_id
        )

    async def browser(*args: Any, **kwargs: Any) -> list[Any]:
        raise ConnectorDegradedError(
            ConnectorStatus.timeout,
            "browser timeout",
            connector.connector_id,
            {"timeout_ms": 30000},
        )

    monkeypatch.setattr(TemplateConnector, "search", rss)
    monkeypatch.delenv("PRICERECON_REDDIT_API_ENABLED", raising=False)
    monkeypatch.setenv("PRICERECON_REDDIT_BROWSER_ENABLED", "true")
    monkeypatch.setattr(connector, "_search_browser", browser)

    with pytest.raises(ConnectorDegradedError) as raised:
        await connector.search("RTX")
    assert raised.value.status is ConnectorStatus.rate_limited
    assert raised.value.detail is not None
    assert raised.value.detail["fallback_errors"] == ["browser:timeout"]
    assert raised.value.detail["fallbacks_attempted"] is True
    assert [
        (stage["stage"], stage["outcome"]) for stage in raised.value.detail["fallback_stages"]
    ] == [
        ("rss", "attempted"),
        ("rss", "failed"),
        ("api", "skipped"),
        ("browser", "attempted"),
        ("browser", "failed"),
    ]


class _FakeResponse:
    def __init__(self, status: int) -> None:
        self.status = status


class _FakePage:
    def __init__(self, content: str, status: int = 200, error: Exception | None = None) -> None:
        self._content, self._status, self._error = content, status, error

    async def goto(self, *args: Any, **kwargs: Any) -> _FakeResponse:
        if self._error:
            raise self._error
        return _FakeResponse(self._status)

    async def wait_for_timeout(self, _: int) -> None:
        return None

    async def content(self) -> str:
        return self._content


class _FakeContext:
    def __init__(self, page: _FakePage) -> None:
        self.page = page

    async def new_page(self) -> _FakePage:
        return self.page

    async def close(self) -> None:
        return None


class _FakeBrowserClient:
    page: _FakePage

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def new_context(self) -> _FakeContext:
        return _FakeContext(type(self).page)

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_browser_session_success_and_structured_errors(monkeypatch: Any) -> None:
    monkeypatch.setattr(reddit_module, "BrowserClient", _FakeBrowserClient)
    monkeypatch.setenv("PRICERECON_REDDIT_BROWSER_ENABLED", "true")
    connector = RedditHardwareSwapUKConnector()

    _FakeBrowserClient.page = _FakePage("Access denied", status=403)
    with pytest.raises(ConnectorDegradedError) as blocked:
        await connector._search_browser("RTX", {})
    assert blocked.value.status is ConnectorStatus.bot_blocked
    assert blocked.value.detail is not None
    assert blocked.value.detail["status_code"] == 403

    _FakeBrowserClient.page = _FakePage("", error=TimeoutError("navigation timeout"))
    with pytest.raises(ConnectorDegradedError) as timed_out:
        await connector._search_browser("RTX", {})
    assert timed_out.value.status is ConnectorStatus.timeout


class TestRedditAPISuccess:
    """Test successful API responses."""

    @pytest.mark.asyncio
    async def test_api_success_returns_listings(
        self,
        mock_api_response: dict[str, Any],
        mock_token_response: dict[str, Any],
        monkeypatch: Any,
    ) -> None:
        monkeypatch.setenv("PRICERECON_REDDIT_API_ENABLED", "true")
        monkeypatch.setenv("REDDIT_CLIENT_ID", "id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
        monkeypatch.setenv("REDDIT_USER_AGENT", "PriceRecon/test")

        connector = RedditHardwareSwapUKConnector()

        token_mock = MagicMock()
        token_mock.status_code = 200
        token_mock.json.return_value = mock_token_response
        token_mock.headers = {}
        token_mock.raise_for_status = MagicMock()

        data_mock = MagicMock()
        data_mock.status_code = 200
        data_mock.json.return_value = mock_api_response
        data_mock.headers = {
            "x-ratelimit-remaining": "599",
            "x-ratelimit-used": "1",
            "x-ratelimit-reset": "100",
        }
        data_mock.raise_for_status = MagicMock()

        with mock.patch.object(
            httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=token_mock
        ) as mock_post:
            with mock.patch.object(
                httpx.AsyncClient, "get", new_callable=AsyncMock, return_value=data_mock
            ) as mock_get:
                listings = await connector._search_api("RTX", {"limit": 25})

                assert len(listings) == 2
                assert listings[0].title_raw == "[H] RTX 4090 [W] £900"
                assert listings[0].price == 900
                assert listings[0].url.endswith("/comments/abc123/post/")
                assert listings[0].timestamp_seen == datetime.fromtimestamp(
                    1_700_000_000, tz=timezone.utc
                )

    @pytest.mark.asyncio
    async def test_api_stores_rate_limit_info(
        self,
        mock_api_response: dict[str, Any],
        mock_token_response: dict[str, Any],
        monkeypatch: Any,
    ) -> None:
        monkeypatch.setenv("PRICERECON_REDDIT_API_ENABLED", "true")
        monkeypatch.setenv("REDDIT_CLIENT_ID", "id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
        monkeypatch.setenv("REDDIT_USER_AGENT", "PriceRecon/test")

        connector = RedditHardwareSwapUKConnector()

        token_mock = MagicMock()
        token_mock.status_code = 200
        token_mock.json.return_value = mock_token_response
        token_mock.headers = {}
        token_mock.raise_for_status = MagicMock()

        data_mock = MagicMock()
        data_mock.status_code = 200
        data_mock.json.return_value = mock_api_response
        data_mock.headers = {
            "x-ratelimit-remaining": "599",
            "x-ratelimit-used": "1",
            "x-ratelimit-reset": "100",
        }
        data_mock.raise_for_status = MagicMock()

        with mock.patch.object(
            httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=token_mock
        ):
            with mock.patch.object(
                httpx.AsyncClient, "get", new_callable=AsyncMock, return_value=data_mock
            ):
                await connector._search_api("RTX", {"limit": 25})

                assert connector._last_rate_limit_info == {
                    "remaining": "599",
                    "used": "1",
                    "reset": "100",
                }


class TestRedditAPIAuthFailure:
    """Test API authentication failures."""

    @pytest.mark.asyncio
    async def test_api_403_raises_auth_error(self, monkeypatch: Any) -> None:
        monkeypatch.setenv("PRICERECON_REDDIT_API_ENABLED", "true")
        monkeypatch.setenv("REDDIT_CLIENT_ID", "id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
        monkeypatch.setenv("REDDIT_USER_AGENT", "PriceRecon/test")

        connector = RedditHardwareSwapUKConnector()

        token_mock = MagicMock()
        token_mock.status_code = 403
        token_mock.headers = {}

        with mock.patch.object(
            httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=token_mock
        ):
            with pytest.raises(ConnectorDegradedError) as exc:
                await connector._search_api("RTX", {})

            assert exc.value.status == ConnectorStatus.auth_failed
            assert "authentication failed" in exc.value.message.lower()
            assert exc.value.detail == {"status_code": 403}

    @pytest.mark.asyncio
    async def test_api_401_raises_auth_error(self, monkeypatch: Any) -> None:
        monkeypatch.setenv("PRICERECON_REDDIT_API_ENABLED", "true")
        monkeypatch.setenv("REDDIT_CLIENT_ID", "id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
        monkeypatch.setenv("REDDIT_USER_AGENT", "PriceRecon/test")

        connector = RedditHardwareSwapUKConnector()

        token_mock = MagicMock()
        token_mock.status_code = 401
        token_mock.headers = {}

        with mock.patch.object(
            httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=token_mock
        ):
            with pytest.raises(ConnectorDegradedError) as exc:
                await connector._search_api("RTX", {})

            assert exc.value.status == ConnectorStatus.auth_failed
            assert "authentication failed" in exc.value.message.lower()

    @pytest.mark.asyncio
    async def test_api_no_token_raises_auth_error(
        self, mock_token_response: dict[str, Any], monkeypatch: Any
    ) -> None:
        monkeypatch.setenv("PRICERECON_REDDIT_API_ENABLED", "true")
        monkeypatch.setenv("REDDIT_CLIENT_ID", "id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
        monkeypatch.setenv("REDDIT_USER_AGENT", "PriceRecon/test")

        connector = RedditHardwareSwapUKConnector()

        # Mock successful response but with no access token
        token_mock = MagicMock()
        token_mock.status_code = 200
        token_mock.json.return_value = {"access_token": None}
        token_mock.headers = {}
        token_mock.raise_for_status = MagicMock()

        with mock.patch.object(
            httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=token_mock
        ):
            with pytest.raises(ConnectorDegradedError) as exc:
                await connector._search_api("RTX", {})

            assert exc.value.status == ConnectorStatus.auth_failed
            assert "no access token" in exc.value.message.lower()


class TestRedditAPIRateLimit:
    """Test API rate limiting."""

    @pytest.mark.asyncio
    async def test_api_429_on_token_raises_rate_limit(self, monkeypatch: Any) -> None:
        monkeypatch.setenv("PRICERECON_REDDIT_API_ENABLED", "true")
        monkeypatch.setenv("REDDIT_CLIENT_ID", "id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
        monkeypatch.setenv("REDDIT_USER_AGENT", "PriceRecon/test")

        connector = RedditHardwareSwapUKConnector()

        token_mock = MagicMock()
        token_mock.status_code = 429
        token_mock.headers = {}

        with mock.patch.object(
            httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=token_mock
        ):
            with pytest.raises(ConnectorDegradedError) as exc:
                await connector._search_api("RTX", {})

            assert exc.value.status == ConnectorStatus.rate_limited
            assert "rate limited" in exc.value.message.lower()

    @pytest.mark.asyncio
    async def test_api_429_on_data_request_raises_rate_limit(
        self, mock_token_response: dict[str, Any], monkeypatch: Any
    ) -> None:
        monkeypatch.setenv("PRICERECON_REDDIT_API_ENABLED", "true")
        monkeypatch.setenv("REDDIT_CLIENT_ID", "id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
        monkeypatch.setenv("REDDIT_USER_AGENT", "PriceRecon/test")

        connector = RedditHardwareSwapUKConnector()

        token_mock = MagicMock()
        token_mock.status_code = 200
        token_mock.json.return_value = mock_token_response
        token_mock.headers = {}
        token_mock.raise_for_status = MagicMock()

        data_mock = MagicMock()
        data_mock.status_code = 429
        data_mock.headers = {}

        with mock.patch.object(
            httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=token_mock
        ):
            with mock.patch.object(
                httpx.AsyncClient, "get", new_callable=AsyncMock, return_value=data_mock
            ):
                with pytest.raises(ConnectorDegradedError) as exc:
                    await connector._search_api("RTX", {})

                assert exc.value.status == ConnectorStatus.rate_limited
                assert "rate limited" in exc.value.message.lower()


class TestRedditAPITransportErrors:
    """Test API transport/network errors."""

    @pytest.mark.asyncio
    async def test_api_http_error_on_token_raises_unknown_error(self, monkeypatch: Any) -> None:
        monkeypatch.setenv("PRICERECON_REDDIT_API_ENABLED", "true")
        monkeypatch.setenv("REDDIT_CLIENT_ID", "id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
        monkeypatch.setenv("REDDIT_USER_AGENT", "PriceRecon/test")

        connector = RedditHardwareSwapUKConnector()

        with mock.patch.object(
            httpx.AsyncClient,
            "post",
            new_callable=AsyncMock,
            side_effect=httpx.TimeoutException("Request timeout"),
        ):
            with pytest.raises(ConnectorDegradedError) as exc:
                await connector._search_api("RTX", {})

            assert exc.value.status == ConnectorStatus.unknown_error
            assert "token request failed" in exc.value.message.lower()

    @pytest.mark.asyncio
    async def test_api_connection_error_raises_unknown_error(self, monkeypatch: Any) -> None:
        monkeypatch.setenv("PRICERECON_REDDIT_API_ENABLED", "true")
        monkeypatch.setenv("REDDIT_CLIENT_ID", "id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
        monkeypatch.setenv("REDDIT_USER_AGENT", "PriceRecon/test")

        connector = RedditHardwareSwapUKConnector()

        with mock.patch.object(
            httpx.AsyncClient,
            "post",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            with pytest.raises(ConnectorDegradedError) as exc:
                await connector._search_api("RTX", {})

            assert exc.value.status == ConnectorStatus.unknown_error


class TestRedditAPINormalization:
    """Test API response normalization matches RSS shape."""

    @pytest.mark.asyncio
    async def test_api_normalization_produces_correct_fields(
        self,
        mock_api_response: dict[str, Any],
        mock_token_response: dict[str, Any],
        monkeypatch: Any,
    ) -> None:
        monkeypatch.setenv("PRICERECON_REDDIT_API_ENABLED", "true")
        monkeypatch.setenv("REDDIT_CLIENT_ID", "id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
        monkeypatch.setenv("REDDIT_USER_AGENT", "PriceRecon/test")

        connector = RedditHardwareSwapUKConnector()

        token_mock = MagicMock()
        token_mock.status_code = 200
        token_mock.json.return_value = mock_token_response
        token_mock.headers = {}
        token_mock.raise_for_status = MagicMock()

        data_mock = MagicMock()
        data_mock.status_code = 200
        data_mock.json.return_value = mock_api_response
        data_mock.headers = {}
        data_mock.raise_for_status = MagicMock()

        with mock.patch.object(
            httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=token_mock
        ):
            with mock.patch.object(
                httpx.AsyncClient, "get", new_callable=AsyncMock, return_value=data_mock
            ):
                listings = await connector._search_api("RTX", {})

                # Verify all expected fields are present
                assert all(hasattr(l, "title_raw") for l in listings)
                assert all(hasattr(l, "price") for l in listings)
                assert all(hasattr(l, "url") for l in listings)
                assert all(hasattr(l, "timestamp_seen") for l in listings)
                assert all(hasattr(l, "source") for l in listings)

                # Verify data types
                assert isinstance(listings[0].title_raw, str)
                from decimal import Decimal

                assert isinstance(listings[0].price, (Decimal, type(None)))
                assert isinstance(listings[0].url, str)
                assert isinstance(listings[0].timestamp_seen, datetime)
                assert listings[0].timestamp_seen.tzinfo == timezone.utc

    @pytest.mark.asyncio
    async def test_api_empty_results_list_does_not_raise(
        self, mock_token_response: dict[str, Any], monkeypatch: Any
    ) -> None:
        """Empty results (genuinely no posts) should return empty list, not raise."""
        monkeypatch.setenv("PRICERECON_REDDIT_API_ENABLED", "true")
        monkeypatch.setenv("REDDIT_CLIENT_ID", "id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
        monkeypatch.setenv("REDDIT_USER_AGENT", "PriceRecon/test")

        connector = RedditHardwareSwapUKConnector()

        token_mock = MagicMock()
        token_mock.status_code = 200
        token_mock.json.return_value = mock_token_response
        token_mock.headers = {}
        token_mock.raise_for_status = MagicMock()

        # Mock empty response
        data_mock = MagicMock()
        data_mock.status_code = 200
        data_mock.json.return_value = {"data": {"children": []}}
        data_mock.headers = {}
        data_mock.raise_for_status = MagicMock()

        with mock.patch.object(
            httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=token_mock
        ):
            with mock.patch.object(
                httpx.AsyncClient, "get", new_callable=AsyncMock, return_value=data_mock
            ):
                listings = await connector._search_api("RTX", {})

                assert listings == []


class TestRedditAPICredentialLoading:
    """Test credential loading from environment and file."""

    def test_load_credentials_from_env(self, monkeypatch: Any) -> None:
        monkeypatch.setenv("REDDIT_CLIENT_ID", "env_id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "env_secret")
        monkeypatch.setenv("REDDIT_USER_AGENT", "env_ua")

        connector = RedditHardwareSwapUKConnector()

        client_id, client_secret, user_agent = connector._load_api_credentials()

        assert client_id == "env_id"
        assert client_secret == "env_secret"
        assert user_agent == "env_ua"

    def test_load_credentials_from_file(self, monkeypatch: Any, tmp_path: Any) -> None:
        import json

        cred_file = tmp_path / "reddit_creds.json"
        cred_data = {
            "client_id": "file_id",
            "client_secret": "file_secret",
            "user_agent": "file_ua",
        }
        cred_file.write_text(json.dumps(cred_data))
        monkeypatch.setenv("REDDIT_CREDENTIAL_FILE", str(cred_file))
        # Ensure env vars are not set
        monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
        monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)
        monkeypatch.delenv("REDDIT_USER_AGENT", raising=False)

        connector = RedditHardwareSwapUKConnector()

        client_id, client_secret, user_agent = connector._load_api_credentials()

        assert client_id == "file_id"
        assert client_secret == "file_secret"
        assert user_agent == "file_ua"

    def test_load_credentials_defaults(self, monkeypatch: Any) -> None:
        monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
        monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)
        monkeypatch.delenv("REDDIT_USER_AGENT", raising=False)
        monkeypatch.delenv("REDDIT_CREDENTIAL_FILE", raising=False)

        connector = RedditHardwareSwapUKConnector()

        client_id, client_secret, user_agent = connector._load_api_credentials()

        assert client_id == ""
        assert client_secret == ""
        assert user_agent == "PriceRecon/1.0"

    def test_api_is_approved_with_env(self, monkeypatch: Any) -> None:
        monkeypatch.setenv("PRICERECON_REDDIT_API_ENABLED", "true")
        monkeypatch.setenv("REDDIT_CLIENT_ID", "id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
        monkeypatch.setenv("REDDIT_USER_AGENT", "ua")

        connector = RedditHardwareSwapUKConnector()

        assert connector._api_is_approved() is True

    def test_api_is_approved_with_file(self, monkeypatch: Any, tmp_path: Any) -> None:
        import json

        cred_file = tmp_path / "reddit_creds.json"
        cred_data = {"client_id": "id", "client_secret": "secret", "user_agent": "ua"}
        cred_file.write_text(json.dumps(cred_data))
        monkeypatch.setenv("PRICERECON_REDDIT_API_ENABLED", "true")
        monkeypatch.setenv("REDDIT_CREDENTIAL_FILE", str(cred_file))

        connector = RedditHardwareSwapUKConnector()

        assert connector._api_is_approved() is True

    def test_api_is_approved_disabled(self, monkeypatch: Any) -> None:
        monkeypatch.setenv("PRICERECON_REDDIT_API_ENABLED", "false")

        connector = RedditHardwareSwapUKConnector()

        assert connector._api_is_approved() is False


class TestRedditAPIRateLimitExtraction:
    """Test rate limit header extraction."""

    def test_extract_rate_limit_info_all_headers(self, monkeypatch: Any) -> None:
        connector = RedditHardwareSwapUKConnector()

        headers = {
            "x-ratelimit-remaining": "599",
            "x-ratelimit-used": "1",
            "x-ratelimit-reset": "100",
        }

        info = connector._extract_rate_limit_info(headers)

        assert info == {"remaining": "599", "used": "1", "reset": "100"}

    def test_extract_rate_limit_info_partial_headers(self, monkeypatch: Any) -> None:
        connector = RedditHardwareSwapUKConnector()

        headers = {"x-ratelimit-remaining": "599"}

        info = connector._extract_rate_limit_info(headers)

        assert info == {"remaining": "599"}

    def test_extract_rate_limit_info_no_headers(self, monkeypatch: Any) -> None:
        connector = RedditHardwareSwapUKConnector()

        headers = {}

        info = connector._extract_rate_limit_info(headers)

        assert info is None


# TODO: Add integration test with live credentials once available
# This would verify the actual Reddit API token flow works with real credentials
