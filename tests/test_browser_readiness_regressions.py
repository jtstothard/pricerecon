import json

import httpx

from pricerecon.connectors.external_browser import BrowserDegradation, ExternalBrowserAdapter


async def test_title_only_cloak_response_is_not_success():
    adapter = ExternalBrowserAdapter.from_config(
        {
            "browser_backends": {"cloak": {"type": "cloakbrowser", "endpoint": "http://cloak"}},
            "browser_default": "cloak",
        },
        client_factory=lambda **kw: httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json={"navigated": True, "title": "Example Domain"})
            ),
            **kw,
        ),
    )
    result = await adapter.navigate("https://example.com")
    assert result.degradation is BrowserDegradation.EMPTY_RESULT


async def test_anonymous_camofox_callers_do_not_share_contexts():
    opened = []

    def handler(request):
        if request.url.path == "/tabs":
            opened.append(json.loads(request.content))
            return httpx.Response(200, json={"tabId": "probe"})
        if request.method == "DELETE":
            return httpx.Response(204)
        return httpx.Response(200, json={"snapshot": "/comments/ rendered content"})

    config = {
        "browser_backends": {"camo": {"type": "camofox", "endpoint": "http://camo"}},
        "browser_default": "camo",
    }
    for _ in range(2):
        adapter = ExternalBrowserAdapter.from_config(
            config,
            client_factory=lambda **kw: httpx.AsyncClient(
                transport=httpx.MockTransport(handler), **kw
            ),
        )
        await adapter.navigate("https://example.com")
    assert opened[0]["userId"] != opened[1]["userId"]


async def test_connector_and_merchant_contexts_are_stable_and_separate():
    opened = []

    def handler(request):
        if request.url.path == "/tabs":
            opened.append(json.loads(request.content)["userId"])
            return httpx.Response(200, json={"tabId": "probe"})
        if request.method == "DELETE":
            return httpx.Response(204)
        return httpx.Response(200, json={"snapshot": "Example Domain"})

    config = {
        "browser_backends": {"camo": {"type": "camofox", "endpoint": "http://camo"}},
        "browser_default": "camo",
    }
    for connector, url in [
        ("shopify", "https://one.test/a"),
        ("shopify", "https://one.test/b"),
        ("shopify", "https://two.test/a"),
        ("ebay", "https://one.test/a"),
    ]:
        adapter = ExternalBrowserAdapter.from_config(
            config,
            session_scope=connector,
            client_factory=lambda **kw: httpx.AsyncClient(
                transport=httpx.MockTransport(handler), **kw
            ),
        )
        await adapter.navigate(url)
    assert opened[0] == opened[1]
    assert len(set(opened)) == 3


async def test_assigned_account_profile_is_preserved():
    seen = []

    def handler(request):
        if request.url.path == "/tabs":
            seen.append(json.loads(request.content))
            return httpx.Response(200, json={"tabId": "probe"})
        if request.method == "DELETE":
            return httpx.Response(204)
        return httpx.Response(200, json={"snapshot": "Example Domain"})

    config = {
        "browser_backends": {
            "camo": {
                "type": "camofox",
                "endpoint": "http://camo",
                "options": {"user_id": "assigned-facebook-profile", "session_key": "marketplace"},
            }
        },
        "browser_default": "camo",
    }
    adapter = ExternalBrowserAdapter.from_config(
        config,
        session_scope="facebook",
        client_factory=lambda **kw: httpx.AsyncClient(transport=httpx.MockTransport(handler), **kw),
    )
    await adapter.navigate("https://example.com")
    assert seen[0]["userId"] == "assigned-facebook-profile"
    assert seen[0]["sessionKey"] == "marketplace"


async def test_cloak_preserves_page_status_and_bounds_content():
    def handler(request):
        return httpx.Response(
            200,
            json={
                "navigated": True,
                "html": "x" * 80,
                "mainStatus": 200,
                "finalUrl": "https://example.com/final",
                "networkInterceptionSupported": False,
            },
        )

    config = {
        "browser_backends": {"cloak": {"type": "cloakbrowser", "endpoint": "http://cloak"}},
        "browser_default": "cloak",
    }
    adapter = ExternalBrowserAdapter.from_config(
        config,
        client_factory=lambda **kw: httpx.AsyncClient(transport=httpx.MockTransport(handler), **kw),
    )
    result = await adapter.navigate("https://example.com", response_body_limit=40)
    assert result.rendered.html == "x" * 40
    assert result.rendered.html_truncated
    assert result.rendered.final_url == "https://example.com/final"
    assert result.rendered.status == 200
    assert not result.network_interception_supported


async def test_cloak_blocked_document_is_not_success():
    config = {
        "browser_backends": {"cloak": {"type": "cloakbrowser", "endpoint": "http://cloak"}},
        "browser_default": "cloak",
    }
    adapter = ExternalBrowserAdapter.from_config(
        config,
        client_factory=lambda **kw: httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(
                    200, json={"navigated": True, "html": "Access denied", "mainStatus": 403}
                )
            ),
            **kw,
        ),
    )
    result = await adapter.navigate("https://example.com")
    assert result.degradation is BrowserDegradation.BLOCKED
