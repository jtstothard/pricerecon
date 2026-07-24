"""Unit tests for Reddit official API connector with mocked HTTP responses."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from pricerecon.connectors.reddit import (
    RedditHardwareSwapUKConnector,
)
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus


@pytest.fixture
def connector() -> RedditHardwareSwapUKConnector:
    return RedditHardwareSwapUKConnector()


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


class TestRedditAPISuccess:
    """Test successful API responses."""

    @pytest.mark.asyncio
    async def test_api_success_returns_listings(
        self,
        connector: RedditHardwareSwapUKConnector,
        mock_api_response: dict[str, Any],
        mock_token_response: dict[str, Any],
    ) -> None:
        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
            with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
                # Mock token response
                token_mock = MagicMock()
                token_mock.status_code = 200
                token_mock.json.return_value = mock_token_response
                token_mock.headers = {}
                token_mock.raise_for_status = MagicMock()

                # Mock data response
                data_mock = MagicMock()
                data_mock.status_code = 200
                data_mock.json.return_value = mock_api_response
                data_mock.headers = {
                    "x-ratelimit-remaining": "599",
                    "x-ratelimit-used": "1",
                    "x-ratelimit-reset": "100",
                }
                data_mock.raise_for_status = MagicMock()

                mock_post.return_value = token_mock
                mock_get.return_value = data_mock

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
        connector: RedditHardwareSwapUKConnector,
        mock_api_response: dict[str, Any],
        mock_token_response: dict[str, Any],
    ) -> None:
        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
            with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
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

                mock_post.return_value = token_mock
                mock_get.return_value = data_mock

                await connector._search_api("RTX", {"limit": 25})

                assert connector._last_rate_limit_info == {
                    "remaining": "599",
                    "used": "1",
                    "reset": "100",
                }


class TestRedditAPIAuthFailure:
    """Test API authentication failures."""

    @pytest.mark.asyncio
    async def test_api_403_raises_auth_error(
        self, connector: RedditHardwareSwapUKConnector
    ) -> None:
        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
            token_mock = MagicMock()
            token_mock.status_code = 403
            token_mock.headers = {}
            mock_post.return_value = token_mock

            with pytest.raises(ConnectorDegradedError) as exc:
                await connector._search_api("RTX", {})

            assert exc.value.status == ConnectorStatus.auth_failed
            assert "authentication failed" in exc.value.message.lower()
            assert exc.value.detail == {"status_code": 403}

    @pytest.mark.asyncio
    async def test_api_401_raises_auth_error(
        self, connector: RedditHardwareSwapUKConnector
    ) -> None:
        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
            token_mock = MagicMock()
            token_mock.status_code = 401
            token_mock.headers = {}
            mock_post.return_value = token_mock

            with pytest.raises(ConnectorDegradedError) as exc:
                await connector._search_api("RTX", {})

            assert exc.value.status == ConnectorStatus.auth_failed
            assert "authentication failed" in exc.value.message.lower()

    @pytest.mark.asyncio
    async def test_api_no_token_raises_auth_error(
        self, connector: RedditHardwareSwapUKConnector, mock_token_response: dict[str, Any]
    ) -> None:
        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
            # Mock successful response but with no access token
            token_mock = MagicMock()
            token_mock.status_code = 200
            token_mock.json.return_value = {"access_token": None}
            token_mock.headers = {}
            token_mock.raise_for_status = MagicMock()
            mock_post.return_value = token_mock

            with pytest.raises(ConnectorDegradedError) as exc:
                await connector._search_api("RTX", {})

            assert exc.value.status == ConnectorStatus.auth_failed
            assert "no access token" in exc.value.message.lower()


class TestRedditAPIRateLimit:
    """Test API rate limiting."""

    @pytest.mark.asyncio
    async def test_api_429_on_token_raises_rate_limit(
        self, connector: RedditHardwareSwapUKConnector
    ) -> None:
        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
            token_mock = MagicMock()
            token_mock.status_code = 429
            token_mock.headers = {}
            mock_post.return_value = token_mock

            with pytest.raises(ConnectorDegradedError) as exc:
                await connector._search_api("RTX", {})

            assert exc.value.status == ConnectorStatus.rate_limited
            assert "rate limited" in exc.value.message.lower()

    @pytest.mark.asyncio
    async def test_api_429_on_data_request_raises_rate_limit(
        self, connector: RedditHardwareSwapUKConnector, mock_token_response: dict[str, Any]
    ) -> None:
        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
            with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
                token_mock = MagicMock()
                token_mock.status_code = 200
                token_mock.json.return_value = mock_token_response
                token_mock.headers = {}
                token_mock.raise_for_status = MagicMock()
                mock_post.return_value = token_mock

                data_mock = MagicMock()
                data_mock.status_code = 429
                data_mock.headers = {}
                mock_get.return_value = data_mock

                with pytest.raises(ConnectorDegradedError) as exc:
                    await connector._search_api("RTX", {})

                assert exc.value.status == ConnectorStatus.rate_limited
                assert "rate limited" in exc.value.message.lower()


class TestRedditAPITransportErrors:
    """Test API transport/network errors."""

    @pytest.mark.asyncio
    async def test_api_http_error_on_token_raises_unknown_error(
        self, connector: RedditHardwareSwapUKConnector
    ) -> None:
        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timeout")

            with pytest.raises(ConnectorDegradedError) as exc:
                await connector._search_api("RTX", {})

            assert exc.value.status == ConnectorStatus.unknown_error
            assert "token request failed" in exc.value.message.lower()

    @pytest.mark.asyncio
    async def test_api_connection_error_raises_unknown_error(
        self, connector: RedditHardwareSwapUKConnector
    ) -> None:
        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection refused")

            with pytest.raises(ConnectorDegradedError) as exc:
                await connector._search_api("RTX", {})

            assert exc.value.status == ConnectorStatus.unknown_error


class TestRedditAPINormalization:
    """Test API response normalization matches RSS shape."""

    @pytest.mark.asyncio
    async def test_api_normalization_produces_correct_fields(
        self,
        connector: RedditHardwareSwapUKConnector,
        mock_api_response: dict[str, Any],
        mock_token_response: dict[str, Any],
    ) -> None:
        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
            with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
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

                mock_post.return_value = token_mock
                mock_get.return_value = data_mock

                listings = await connector._search_api("RTX", {})

                # Verify all expected fields are present
                assert all(hasattr(listing, "title_raw") for listing in listings)
                assert all(hasattr(listing, "price") for listing in listings)
                assert all(hasattr(listing, "url") for listing in listings)
                assert all(hasattr(listing, "timestamp_seen") for listing in listings)
                assert all(hasattr(listing, "source") for listing in listings)

                # Verify data types
                assert isinstance(listings[0].title_raw, str)
                assert isinstance(listings[0].price, (int, float, type(None)))
                assert isinstance(listings[0].url, str)
                assert isinstance(listings[0].timestamp_seen, datetime)
                assert listings[0].timestamp_seen.tzinfo == timezone.utc

    @pytest.mark.asyncio
    async def test_api_empty_results_list_does_not_raise(
        self, connector: RedditHardwareSwapUKConnector, mock_token_response: dict[str, Any]
    ) -> None:
        """Empty results (genuinely no posts) should return empty list, not raise."""
        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
            with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
                token_mock = MagicMock()
                token_mock.status_code = 200
                token_mock.json.return_value = mock_token_response
                token_mock.headers = {}
                token_mock.raise_for_status = MagicMock()
                mock_post.return_value = token_mock

                # Mock empty response
                data_mock = MagicMock()
                data_mock.status_code = 200
                data_mock.json.return_value = {"data": {"children": []}}
                data_mock.headers = {}
                data_mock.raise_for_status = MagicMock()
                mock_get.return_value = data_mock

                listings = await connector._search_api("RTX", {})

                assert listings == []


class TestRedditAPICredentialLoading:
    """Test credential loading from environment and file."""

    def test_load_credentials_from_env(
        self, connector: RedditHardwareSwapUKConnector, monkeypatch: Any
    ) -> None:
        monkeypatch.setenv("REDDIT_CLIENT_ID", "env_id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "env_secret")
        monkeypatch.setenv("REDDIT_USER_AGENT", "env_ua")

        client_id, client_secret, user_agent = connector._load_api_credentials()

        assert client_id == "env_id"
        assert client_secret == "env_secret"
        assert user_agent == "env_ua"

    def test_load_credentials_from_file(
        self, connector: RedditHardwareSwapUKConnector, monkeypatch: Any, tmp_path: Any
    ) -> None:
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

        client_id, client_secret, user_agent = connector._load_api_credentials()

        assert client_id == "file_id"
        assert client_secret == "file_secret"
        assert user_agent == "file_ua"

    def test_load_credentials_defaults(
        self, connector: RedditHardwareSwapUKConnector, monkeypatch: Any
    ) -> None:
        monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
        monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)
        monkeypatch.delenv("REDDIT_USER_AGENT", raising=False)
        monkeypatch.delenv("REDDIT_CREDENTIAL_FILE", raising=False)

        client_id, client_secret, user_agent = connector._load_api_credentials()

        assert client_id == ""
        assert client_secret == ""
        assert user_agent == "PriceRecon/1.0"

    def test_api_is_approved_with_env(
        self, connector: RedditHardwareSwapUKConnector, monkeypatch: Any
    ) -> None:
        monkeypatch.setenv("PRICERECON_REDDIT_API_ENABLED", "true")
        monkeypatch.setenv("REDDIT_CLIENT_ID", "id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
        monkeypatch.setenv("REDDIT_USER_AGENT", "ua")

        assert connector._api_is_approved() is True

    def test_api_is_approved_with_file(
        self, connector: RedditHardwareSwapUKConnector, monkeypatch: Any, tmp_path: Any
    ) -> None:
        import json

        cred_file = tmp_path / "reddit_creds.json"
        cred_data = {"client_id": "id", "client_secret": "secret", "user_agent": "ua"}
        cred_file.write_text(json.dumps(cred_data))
        monkeypatch.setenv("PRICERECON_REDDIT_API_ENABLED", "true")
        monkeypatch.setenv("REDDIT_CREDENTIAL_FILE", str(cred_file))

        assert connector._api_is_approved() is True

    def test_api_is_approved_disabled(
        self, connector: RedditHardwareSwapUKConnector, monkeypatch: Any
    ) -> None:
        monkeypatch.setenv("PRICERECON_REDDIT_API_ENABLED", "false")

        assert connector._api_is_approved() is False


class TestRedditAPIRateLimitExtraction:
    """Test rate limit header extraction."""

    def test_extract_rate_limit_info_all_headers(
        self, connector: RedditHardwareSwapUKConnector
    ) -> None:
        headers = {
            "x-ratelimit-remaining": "599",
            "x-ratelimit-used": "1",
            "x-ratelimit-reset": "100",
        }

        info = connector._extract_rate_limit_info(headers)

        assert info == {"remaining": "599", "used": "1", "reset": "100"}

    def test_extract_rate_limit_info_partial_headers(
        self, connector: RedditHardwareSwapUKConnector
    ) -> None:
        headers = {"x-ratelimit-remaining": "599"}

        info = connector._extract_rate_limit_info(headers)

        assert info == {"remaining": "599"}

    def test_extract_rate_limit_info_no_headers(
        self, connector: RedditHardwareSwapUKConnector
    ) -> None:
        headers = {}

        info = connector._extract_rate_limit_info(headers)

        assert info is None


# TODO: Add integration test with live credentials once available
# This would verify the actual Reddit API token flow works with real credentials
