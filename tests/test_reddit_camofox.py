"""Reddit's authenticated, persistent-profile Camofox retrieval path."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from pricerecon.connectors.external_browser import ExternalBrowserAdapter
from pricerecon.connectors.reddit import RedditHardwareSwapUKConnector
from pricerecon.connectors.rss import TemplateConnector
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus


def _camofox_adapter(handler: Any) -> ExternalBrowserAdapter:
    return ExternalBrowserAdapter.from_config(
        {
            "browser_backends": {
                "reddit_camofox": {
                    "type": "camofox",
                    "endpoint": "http://camofox.test",
                    "options": {
                        "user_id": "pricerecon-reddit",
                        "session_key": "reddit-authenticated",
                    },
                }
            }
        },
        {"browser_backend": "reddit_camofox"},
        client_factory=lambda **kwargs: httpx.AsyncClient(
            transport=httpx.MockTransport(handler), **kwargs
        ),
    )


@pytest.mark.asyncio
async def test_reddit_uses_configured_camofox_profile_after_blocked_rss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connector = RedditHardwareSwapUKConnector()

    async def blocked_rss(*args: Any, **kwargs: Any) -> list[Any]:
        raise ConnectorDegradedError(
            ConnectorStatus.bot_blocked, "RSS blocked", connector.connector_id
        )

    def camofox(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/tabs":
            assert request.content
            return httpx.Response(200, json={"tabId": "reddit-tab"})
        if request.method == "GET" and request.url.path == "/tabs/reddit-tab/snapshot":
            return httpx.Response(
                200,
                json={
                    "snapshot": (
                        "[H] RTX 4090 [W] £900 "
                        "https://www.reddit.com/r/hardwareswapuk/comments/abc123/post/"
                    )
                },
            )
        if request.method == "DELETE":
            return httpx.Response(204)
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    monkeypatch.setattr(TemplateConnector, "search", blocked_rss)
    connector._external_browser = _camofox_adapter(camofox)

    listings = await connector.search("RTX 4090")

    assert [listing.url for listing in listings] == [
        "https://www.reddit.com/r/hardwareswapuk/comments/abc123/post/"
    ]


@pytest.mark.asyncio
async def test_reddit_skips_anonymous_camofox_when_profile_identifiers_are_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connector = RedditHardwareSwapUKConnector()
    requests: list[httpx.Request] = []

    async def blocked_rss(*args: Any, **kwargs: Any) -> list[Any]:
        raise ConnectorDegradedError(
            ConnectorStatus.bot_blocked, "RSS blocked", connector.connector_id
        )

    def camofox(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        raise AssertionError("anonymous Camofox must not be used for Reddit")

    monkeypatch.setattr(TemplateConnector, "search", blocked_rss)
    monkeypatch.setattr(connector, "_rss_max_retries", 0)
    connector._external_browser = ExternalBrowserAdapter.from_config(
        {
            "browser_backends": {
                "anonymous_camofox": {
                    "type": "camofox",
                    "endpoint": "http://camofox.test",
                }
            }
        },
        {"browser_backend": "anonymous_camofox"},
        client_factory=lambda **kwargs: httpx.AsyncClient(
            transport=httpx.MockTransport(camofox), **kwargs
        ),
    )

    with pytest.raises(ConnectorDegradedError) as raised:
        await connector.search("RTX 4090")

    assert raised.value.status is ConnectorStatus.bot_blocked
    assert raised.value.detail is not None
    assert raised.value.detail["fallbacks_attempted"] is False
    assert raised.value.detail.get("fallback_errors", []) == []
    assert raised.value.detail["fallback_stages"][-1] == {
        "stage": "camofox",
        "outcome": "skipped",
        "reason": "authenticated_profile_not_configured",
    }
    assert requests == []


@pytest.mark.asyncio
@pytest.mark.parametrize("entrypoint", ["_search_camofox", "_search_browser"])
async def test_reddit_direct_camofox_entrypoints_fail_closed_without_profile(
    monkeypatch: pytest.MonkeyPatch, entrypoint: str
) -> None:
    connector = RedditHardwareSwapUKConnector()
    navigate = AsyncMock()
    adapter = MagicMock()
    adapter.navigate = navigate

    monkeypatch.setattr(connector, "_camofox_is_configured", lambda: False)
    monkeypatch.setattr(connector, "_camofox_adapter", lambda: adapter)

    with pytest.raises(ConnectorDegradedError) as raised:
        await getattr(connector, entrypoint)("RTX 4090", {})

    assert raised.value.status is ConnectorStatus.auth_failed
    navigate.assert_not_awaited()


@pytest.mark.asyncio
async def test_reddit_fails_closed_when_camofox_profile_is_expired(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connector = RedditHardwareSwapUKConnector()

    async def blocked_rss(*args: Any, **kwargs: Any) -> list[Any]:
        raise ConnectorDegradedError(
            ConnectorStatus.bot_blocked, "RSS blocked", connector.connector_id
        )

    def expired_profile(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, request=request)

    monkeypatch.setattr(TemplateConnector, "search", blocked_rss)
    monkeypatch.setattr(connector, "_rss_max_retries", 0)
    monkeypatch.setattr(connector, "_browser_max_retries", 0)
    monkeypatch.setenv("PRICERECON_REDDIT_BROWSER_ENABLED", "true")
    connector._external_browser = _camofox_adapter(expired_profile)

    with pytest.raises(ConnectorDegradedError) as raised:
        await connector.search("RTX 4090")

    assert raised.value.status is ConnectorStatus.bot_blocked
    assert raised.value.detail is not None
    assert raised.value.detail["fallback_errors"] == ["camofox:auth_failed"]
    assert [stage["stage"] for stage in raised.value.detail["fallback_stages"]] == [
        "rss",
        "rss",
        "api",
        "camofox",
        "camofox",
    ]
