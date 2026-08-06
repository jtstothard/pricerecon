from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from pricerecon.connectors import browser_client
from pricerecon.connectors.external_browser import BrowserDegradation, ExternalBrowserAdapter

STATE = {
    "cookies": [
        {"name": "reddit_session", "value": "COOKIE", "domain": ".reddit.com", "path": "/"}
    ],
    "origins": [],
}


def adapter(handler: Any, *, storage_path: str = "/storage-state") -> ExternalBrowserAdapter:
    return ExternalBrowserAdapter.from_config(
        {
            "browser_backends": {
                "camo": {
                    "type": "camofox",
                    "endpoint": "http://camo.test",
                    "options": {
                        "user_id": "user",
                        "session_key": "reddit",
                        "storage_state_path": storage_path,
                    },
                },
                "cloak": {"type": "cloakbrowser", "endpoint": "http://cloak.test"},
            },
            "browser_default": ["camo", "cloak"],
        },
        client_factory=lambda **kwargs: httpx.AsyncClient(
            transport=httpx.MockTransport(handler), **kwargs
        ),
    )


def test_storage_state_validation_rejects_malformed_state() -> None:
    with pytest.raises(ValueError, match="cookies/origins"):
        browser_client._validate_playwright_storage_state({"cookies": "COOKIE", "origins": []})
    with pytest.raises(ValueError, match="malformed cookie"):
        browser_client._validate_playwright_storage_state(
            {"cookies": [{"name": "x"}], "origins": []}
        )
    with pytest.raises(ValueError, match="too large"):
        browser_client._validate_playwright_storage_state(
            {"cookies": [{"name": "x", "value": "x" * (256 * 1024)}], "origins": []}
        )


@pytest.mark.asyncio
async def test_bridge_rejects_noncanonical_state_endpoint() -> None:
    result = await adapter(
        lambda request: httpx.Response(200, json=STATE), storage_path="/admin"
    ).navigate_with_camofox_storage_state("https://www.reddit.com/r/x/new/")
    assert result.degradation is BrowserDegradation.NOT_CONFIGURED


@pytest.mark.asyncio
async def test_bridge_streams_state_in_memory_and_returns_only_structured_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen_state: list[object] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "camo.test":
            assert request.url.path == "/storage-state"
            assert request.url.params["userId"] == "user"
            assert "sessionKey" not in request.url.params
            return httpx.Response(200, json=STATE)
        assert request.url.host == "cloak.test"
        assert request.url.path == "/api/browser/authenticated-session"
        payload = json.loads(request.content)
        seen_state.append(payload["storageState"])
        return httpx.Response(
            200,
            json={
                "ok": True,
                "navigated": True,
                "authenticated": True,
                "title": "Reddit",
                "items": [
                    {"title": "RTX 4090", "url": "https://www.reddit.com/r/x/comments/1/post/"}
                ],
            },
        )

    result = await adapter(handler).navigate_with_camofox_storage_state(
        "https://www.reddit.com/r/x/new/"
    )

    assert result.degradation is BrowserDegradation.NONE
    assert json.loads(result.rendered.snapshot) == {
        "authenticated": True,
        "items": [{"title": "RTX 4090", "url": "https://www.reddit.com/r/x/comments/1/post/"}],
    }
    assert seen_state == [STATE]
    assert "COOKIE" not in result.rendered.snapshot


@pytest.mark.asyncio
async def test_malformed_camofox_state_degrades_without_running_cloakbrowser() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json={"storageState": {"cookies": "not-a-list", "origins": []}})

    result = await adapter(handler).navigate_with_camofox_storage_state(
        "https://www.reddit.com/r/x/new/"
    )

    assert result.degradation is BrowserDegradation.MALFORMED_RESPONSE
    assert calls == ["/storage-state"]
    assert "not-a-list" not in result.attempts[0].reason


@pytest.mark.asyncio
async def test_missing_authenticated_pair_is_explicit_unauthenticated_fallback() -> None:
    config = {
        "browser_backends": {
            "cloak": {"type": "cloakbrowser", "endpoint": "http://cloak.test"},
        },
        "browser_default": "cloak",
    }
    result = await ExternalBrowserAdapter.from_config(config).navigate_with_camofox_storage_state(
        "https://www.reddit.com/r/x/new/"
    )
    assert result.degradation is BrowserDegradation.NOT_CONFIGURED
    assert "cookie" not in result.attempts[0].reason.lower()


@pytest.mark.asyncio
async def test_wrapper_must_return_boolean_authenticated_true() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "camo.test":
            return httpx.Response(200, json=STATE)
        return httpx.Response(
            200,
            json={"ok": True, "navigated": True, "authenticated": "false", "items": []},
        )

    result = await adapter(handler).navigate_with_camofox_storage_state(
        "https://www.reddit.com/r/x/new/"
    )
    assert result.degradation is BrowserDegradation.BLOCKED


@pytest.mark.asyncio
async def test_wrapper_rejects_malformed_structured_items() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "camo.test":
            return httpx.Response(200, json=STATE)
        return httpx.Response(
            200,
            json={
                "ok": True,
                "navigated": True,
                "authenticated": True,
                "items": [{"title": "bogus", "url": "not-a-reddit-url"}],
            },
        )

    result = await adapter(handler).navigate_with_camofox_storage_state(
        "https://www.reddit.com/r/x/new/"
    )
    assert result.degradation is BrowserDegradation.MALFORMED_RESPONSE


@pytest.mark.asyncio
async def test_bridge_maps_timeout_separately() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    result = await adapter(handler).navigate_with_camofox_storage_state(
        "https://www.reddit.com/r/x/new/"
    )
    assert result.degradation is BrowserDegradation.TIMEOUT
