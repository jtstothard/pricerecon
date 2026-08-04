from __future__ import annotations

import httpx

from pricerecon.connectors.external_browser import (
    BrowserDegradation,
    ExternalBrowserAdapter,
)

CONFIG = {
    "browser_backends": {
        "cloak": {"type": "cloakbrowser", "endpoint": "http://cloak.example:9378"},
        "camo": {"type": "camofox", "endpoint": "http://camo.example:9377"},
    },
    "browser_default": ["cloak", "camo"],
}


def make_transport(handler: httpx.MockTransport) -> object:
    return lambda **kwargs: httpx.AsyncClient(transport=handler, **kwargs)


async def test_single_named_backend_is_authoritative() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json={"navigated": True, "title": "Argos"})

    adapter = ExternalBrowserAdapter.from_config(
        CONFIG,
        {"browser_backend": "cloak"},
        client_factory=make_transport(httpx.MockTransport(handler)),
    )
    result = await adapter.navigate("https://www.argos.co.uk/")

    assert result.selected_backend == "cloak"
    assert result.degradation is BrowserDegradation.NONE
    assert seen == ["http://cloak.example:9378/api/browser/session"]


async def test_timeout_retries_ordered_backend_and_records_reason() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if request.url.host == "cloak.example":
            raise httpx.ConnectTimeout("down", request=request)
        if request.url.path == "/tabs":
            return httpx.Response(200, json={"tabId": "tab-1"})
        if request.url.path.endswith("/snapshot"):
            return httpx.Response(200, json={"snapshot": "rendered result"})
        if request.method == "DELETE":
            return httpx.Response(204)
        raise AssertionError(request.url)

    adapter = ExternalBrowserAdapter.from_config(
        CONFIG, client_factory=make_transport(httpx.MockTransport(handler))
    )
    result = await adapter.navigate("https://example.test/")

    assert result.selected_backend == "camo"
    assert [attempt.backend for attempt in result.attempts] == ["cloak", "camo"]
    assert result.attempts[0].degradation is BrowserDegradation.TIMEOUT
    assert result.rendered.snapshot == "rendered result"
    assert result.network_interception_supported is False


async def test_blocked_response_does_not_fallback_without_explicit_policy() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.host or "")
        return httpx.Response(403, request=request)

    adapter = ExternalBrowserAdapter.from_config(
        CONFIG, client_factory=make_transport(httpx.MockTransport(handler))
    )
    result = await adapter.navigate("https://example.test/")

    assert result.degradation is BrowserDegradation.BLOCKED
    assert [attempt.backend for attempt in result.attempts] == ["cloak"]
    assert seen == ["cloak.example"]


async def test_explicit_blocked_fallback_policy_uses_next_backend() -> None:
    config = {
        "browser_backends": {
            "cloak": {
                "type": "cloakbrowser",
                "endpoint": "http://cloak.example:9378",
                "options": {"fallback_on": ["blocked"]},
            },
            "camo": {"type": "camofox", "endpoint": "http://camo.example:9377"},
        },
        "browser_default": ["cloak", "camo"],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "cloak.example":
            return httpx.Response(403, request=request)
        if request.url.path == "/tabs":
            return httpx.Response(200, json={"id": "tab-1"})
        if request.url.path.endswith("/snapshot"):
            return httpx.Response(200, json={"text": "rendered"})
        return httpx.Response(204)

    result = await ExternalBrowserAdapter.from_config(
        config, client_factory=make_transport(httpx.MockTransport(handler))
    ).navigate("https://example.test/")
    assert [attempt.degradation for attempt in result.attempts] == [
        BrowserDegradation.BLOCKED,
        BrowserDegradation.NONE,
    ]
    assert result.selected_backend == "camo"


async def test_cloakbrowser_api_response_is_bounded_and_redacted_not_intercepted() -> None:
    huge = "x" * 200

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "navigated": True,
                "title": "Argos",
                "apiUrl": "https://api.example/products",
                "api": {
                    "status": 200,
                    "contentType": "application/json",
                    "body": {"token": "secret", "items": huge},
                },
            },
        )

    result = await ExternalBrowserAdapter.from_config(
        CONFIG,
        {"browser_backend": "cloak"},
        client_factory=make_transport(httpx.MockTransport(handler)),
    ).navigate("https://example.test/", response_body_limit=80)

    response = result.responses[0]
    assert response.intercepted is False
    assert response.status == 200
    assert "secret" not in response.body
    assert "[redacted]" in response.body
    assert len(response.body) == 80
    assert result.network_interception_supported is True


async def test_malformed_and_empty_results_are_typed() -> None:
    def malformed(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"navigated": "yes"})

    malformed_result = await ExternalBrowserAdapter.from_config(
        CONFIG,
        {"browser_backend": "cloak"},
        client_factory=make_transport(httpx.MockTransport(malformed)),
    ).navigate("https://example.test/")
    assert malformed_result.degradation is BrowserDegradation.MALFORMED_RESPONSE

    def empty(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"navigated": True})

    empty_result = await ExternalBrowserAdapter.from_config(
        CONFIG,
        {"browser_backend": "cloak"},
        client_factory=make_transport(httpx.MockTransport(empty)),
    ).navigate("https://example.test/")
    assert empty_result.degradation is BrowserDegradation.EMPTY_RESULT


async def test_no_selection_is_explicitly_degraded() -> None:
    adapter = ExternalBrowserAdapter.from_config({"browser_backends": CONFIG["browser_backends"]})

    result = await adapter.navigate("https://example.test/")

    assert result.selected_backend is None
    assert result.degradation is BrowserDegradation.NOT_CONFIGURED
    assert result.attempts[0].reason == "no browser backend selected"


async def test_cloakbrowser_network_capture_is_intercepted_and_capable() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "navigated": True,
                "networkResponses": [
                    {
                        "url": "https://api.example/products",
                        "status": 201,
                        "headers": {"Authorization": "leaked", "x-request-id": "abc"},
                        "body": {"items": ["widget"], "token": "leaked"},
                    }
                ],
            },
        )

    result = await ExternalBrowserAdapter.from_config(
        CONFIG,
        {"browser_backend": "cloak"},
        client_factory=make_transport(httpx.MockTransport(handler)),
    ).navigate("https://example.test/", response_body_limit=80)

    response = result.responses[0]
    assert result.network_interception_supported is True
    assert response.intercepted is True
    assert response.status == 201
    assert response.headers["Authorization"] == "[redacted]"
    assert response.body == '{"items":["widget"],"token":"[redacted]"}'


async def test_cloakbrowser_reports_interception_capability_without_captures() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"navigated": True, "title": "Example"})

    result = await ExternalBrowserAdapter.from_config(
        CONFIG,
        {"browser_backend": "cloak"},
        client_factory=make_transport(httpx.MockTransport(handler)),
    ).navigate("https://example.test/")

    assert result.network_interception_supported is True


async def test_empty_result_preserves_interception_capability() -> None:
    """CloakBrowser navigated but returned no content — still reports interception support."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"navigated": True})

    result = await ExternalBrowserAdapter.from_config(
        CONFIG,
        {"browser_backend": "cloak"},
        client_factory=make_transport(httpx.MockTransport(handler)),
    ).navigate("https://example.test/")

    assert result.degradation is BrowserDegradation.EMPTY_RESULT
    assert result.network_interception_supported is True


async def test_all_retryable_backends_exhaust_to_empty_degraded_result() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.host or "")
        raise httpx.ConnectTimeout("offline", request=request)

    result = await ExternalBrowserAdapter.from_config(
        CONFIG, client_factory=make_transport(httpx.MockTransport(handler))
    ).navigate("https://example.test/")

    assert [attempt.backend for attempt in result.attempts] == ["cloak", "camo"]
    assert result.degradation is BrowserDegradation.TIMEOUT
    assert result.rendered.html == ""
    assert result.rendered.snapshot == ""
    assert result.responses == ()
    assert seen == ["cloak.example", "camo.example"]


async def test_camofox_snapshot_failure_survives_cleanup_failure() -> None:
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.method == "POST":
            return httpx.Response(200, json={"tabId": "tab-1"})
        if request.method == "GET":
            return httpx.Response(500, request=request)
        if request.method == "DELETE":
            raise httpx.ConnectError("cleanup unavailable", request=request)
        raise AssertionError(request.url)

    result = await ExternalBrowserAdapter.from_config(
        CONFIG,
        {"browser_backend": "camo"},
        client_factory=make_transport(httpx.MockTransport(handler)),
    ).navigate("https://example.test/")

    assert ("DELETE", "/tabs/tab-1") in calls
    assert result.degradation is BrowserDegradation.BACKEND_UNAVAILABLE
    assert "backend returned HTTP 500" in result.attempts[0].reason


async def test_nested_secrets_in_intercepted_body_are_redacted() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "navigated": True,
                "networkResponses": [
                    {
                        "url": "https://api.example",
                        "headers": {},
                        "body": {"auth": {"access_token": "leaked"}},
                    }
                ],
            },
        )

    result = await ExternalBrowserAdapter.from_config(
        CONFIG,
        {"browser_backend": "cloak"},
        client_factory=make_transport(httpx.MockTransport(handler)),
    ).navigate("https://example.test/")

    assert "leaked" not in result.responses[0].body
    assert result.responses[0].body == '{"auth":{"access_token":"[redacted]"}}'


async def test_malformed_fallback_policy_raises_value_error() -> None:
    config = {
        "browser_backends": {
            "cloak": {
                "type": "cloakbrowser",
                "endpoint": "http://cloak.example:9378",
                "options": {"fallback_on": "timeout"},
            }
        },
        "browser_default": ["cloak"],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("offline", request=request)

    adapter = ExternalBrowserAdapter.from_config(
        config, client_factory=make_transport(httpx.MockTransport(handler))
    )

    import pytest

    with pytest.raises(ValueError, match="fallback_on"):
        await adapter.navigate("https://example.test/")
