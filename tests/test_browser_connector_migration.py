"""Deterministic migration coverage for browser/anti-bot retail connectors."""

from __future__ import annotations

import httpx
import pytest

from pricerecon.connectors.external_browser import ExternalBrowserAdapter
from pricerecon.connectors.fb_marketplace import FacebookMarketplaceConnector
from pricerecon.connectors.google_shopping import GoogleShoppingConnector
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus
from pricerecon.connectors.template_connector import TemplateConnector

GOOGLE_HTML = """
<div class="sh-dgr__content">
  <h3>RTX 5090</h3><a href="/product/1">View</a><span>£1999.99</span>
  <div class="seller">Example Store</div>
</div>
"""

FACEBOOK_HTML = """
<a href="https://www.facebook.com/marketplace/item/123"><div>£550 RTX 4060</div></a>
"""


def adapter_with_transport(
    config: dict[str, object], handler: httpx.MockTransport
) -> ExternalBrowserAdapter:
    return ExternalBrowserAdapter.from_config(
        config,
        {"browser_backend": config["browser_default"]},
        client_factory=lambda **kwargs: httpx.AsyncClient(transport=handler, **kwargs),
    )


@pytest.mark.asyncio
async def test_google_uses_configured_ordered_fallback_and_records_selected_backend() -> None:
    config: dict[str, object] = {
        "browser_backends": {
            "cloak": {"type": "cloakbrowser", "endpoint": "http://cloak.test"},
            "solver": {"type": "flaresolverr", "endpoint": "http://solver.test/v1"},
        },
        "browser_default": ["cloak", "solver"],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "cloak.test":
            return httpx.Response(503, request=request)
        assert request.url == httpx.URL("http://solver.test/v1")
        return httpx.Response(200, json={"solution": {"response": GOOGLE_HTML}})

    connector = GoogleShoppingConnector()
    connector._external_browser = adapter_with_transport(config, httpx.MockTransport(handler))

    listings = await connector.search("RTX 5090")

    assert len(listings) == 1
    assert listings[0].source == "google_shopping"
    assert listings[0].price is not None
    assert listings[0].variant_normalized is not None
    assert listings[0].variant_normalized["selected_backend"] == "solver"
    assert listings[0].variant_normalized["browser_attempts"] == [
        {"backend": "cloak", "degradation": "backend_unavailable"},
        {"backend": "solver", "degradation": "none"},
    ]


@pytest.mark.asyncio
async def test_google_exposes_blocked_external_browser_as_degraded_output() -> None:
    config: dict[str, object] = {
        "browser_backends": {"cloak": {"type": "cloakbrowser", "endpoint": "http://cloak.test"}},
        "browser_default": "cloak",
    }

    connector = GoogleShoppingConnector()
    connector._external_browser = adapter_with_transport(
        config, httpx.MockTransport(lambda request: httpx.Response(403, request=request))
    )

    with pytest.raises(ConnectorDegradedError) as error:
        await connector.search("RTX 5090")

    assert error.value.status is ConnectorStatus.bot_blocked
    assert error.value.detail == {
        "selected_backend": "cloak",
        "degradation": "blocked",
        "attempts": [
            {
                "backend": "cloak",
                "degradation": "blocked",
                "reason": "backend returned HTTP 403 at http://cloak.test/api/browser/session",
                "status": 403,
            }
        ],
    }


@pytest.mark.asyncio
async def test_facebook_uses_cloak_rendered_html_without_local_browser_or_cookie_access() -> None:
    config: dict[str, object] = {
        "browser_backends": {"cloak": {"type": "cloakbrowser", "endpoint": "http://cloak.test"}},
        "browser_default": "cloak",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/browser/session"
        return httpx.Response(200, json={"navigated": True, "html": FACEBOOK_HTML})

    connector = FacebookMarketplaceConnector(latitude=51.5, longitude=-0.12)
    connector._external_browser = adapter_with_transport(config, httpx.MockTransport(handler))

    listings = await connector.search("RTX 4060")

    assert len(listings) == 1
    assert listings[0].source == "facebook_marketplace"
    assert str(listings[0].price) == "550"
    assert listings[0].variant_normalized is not None
    assert listings[0].variant_normalized["selected_backend"] == "cloak"


@pytest.mark.asyncio
async def test_flaresolverr_template_connector_uses_shared_adapter_when_selected() -> None:
    config: dict[str, object] = {
        "browser_backends": {
            "solver": {"type": "flaresolverr", "endpoint": "http://solver.test/v1"}
        },
        "browser_default": "solver",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        return httpx.Response(
            200,
            json={
                "solution": {
                    "response": "<article class='product'><a href='/product/1'><h3>RTX 5090</h3></a><span class='price'>£1999.99</span></article>"
                }
            },
        )

    class TestCclConnector(TemplateConnector):
        template_name = "ccl"

    connector = TestCclConnector()
    connector._external_browser = adapter_with_transport(config, httpx.MockTransport(handler))
    listings = await connector.search("RTX 5090")
    await connector.cleanup()

    assert listings
    assert all(listing.source == "ccl" for listing in listings)
    assert all(listing.price is not None for listing in listings)


@pytest.mark.asyncio
async def test_facebook_selected_external_backend_skips_local_browser_and_cookie_setup() -> None:
    config: dict[str, object] = {
        "browser_backends": {"cloak": {"type": "cloakbrowser", "endpoint": "http://cloak.test"}},
        "browser_default": "cloak",
    }

    connector = FacebookMarketplaceConnector(latitude=51.5, longitude=-0.12)
    connector._external_browser = adapter_with_transport(
        config,
        httpx.MockTransport(
            lambda _request: httpx.Response(200, json={"navigated": True, "html": FACEBOOK_HTML})
        ),
    )

    await connector.initialize()
    assert connector._context is None
    assert connector._page is None
    await connector.cleanup()
