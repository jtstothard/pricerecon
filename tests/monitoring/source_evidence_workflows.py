"""Original synthetic source payloads, real adapters and normal persisted API.

No application imports outside MonitoringHarness. Browser fixture overrides only
the external navigation edge; production browser origin accounting stays blocked.
"""

import asyncio
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import httpx

from .harness import MonitoringHarness
from .workflows import get


def admission():
    from pricerecon.models.discovery import DiscoveryAdmission

    return DiscoveryAdmission(
        mode="offline_verification",
        policy_reference="ticket11-original-fixtures",
        permission_reference="original-synthetic-data",
        activation_reference="guarded-child",
    )


@contextmanager
def browser_fixture(harness, *, truncated=False, discovery_truncated=False):
    from pricerecon import connectors
    from pricerecon.connectors.aliexpress import AliExpressConnector
    from pricerecon.connectors.external_browser import ExternalBrowserResult, RenderedContent
    from pricerecon.core.collection_transport import debit_resources

    class FixtureAliExpress(AliExpressConnector):
        def has_external_browser(self):
            return True

        async def navigate_external_browser(self, url):
            debit_resources(requests=1, **({"pages": 1} if "/w/" in url else {"details": 1}))
            harness.searches.append(("aliexpress", url))
            if "/w/" in url:
                html = '<a href="/item/10000000000001.html">A</a><a href="/item/10000000000002.html">B</a>'
            else:
                # Original markup, not a retained merchant page. Title and
                # selected label disagree; generic stock does not bind a SKU.
                html = """<h1>Addiesdive AD2066 mint</h1>
                    <input name="color" checked value="Space Gray">
                    <input name="quantity" value="1">
                    <span data-current-price>GBP 37.25</span>
                    <p>In stock. Ship to: United States. Price includes VAT.</p>"""
            return ExternalBrowserResult(
                selected_backend="original-fixture",
                attempts=(),
                rendered=RenderedContent(
                    html=html,
                    final_url=url,
                    html_truncated=(truncated and "/item/" in url)
                    or (discovery_truncated and "/w/" in url),
                ),
            )

    with patch.object(connectors, "discover_connectors", lambda: {"aliexpress": FixtureAliExpress}):
        yield


async def aliexpress():
    with MonitoringHarness() as harness, browser_fixture(harness):
        from pricerecon.core.collection_policy import operating_policy
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryRequest

        policy = type(harness.test_policy).model_validate(
            {
                **harness.test_policy.model_dump(),
                "provider_request_caps": {"aliexpress": {"limit": 20, "tracking_reserve": 0}},
            }
        )
        with operating_policy(policy):
            async with harness.session() as (client, _):
                await execute_discovery(
                    DiscoveryRequest(
                        query="AD2066",
                        sources=[
                            {
                                "connector": "aliexpress",
                                "config": {
                                    "browser_max_products": 1,
                                    "evidence_use": {
                                        "permission_reference": "original-fixture",
                                        "retention": "synthetic",
                                    },
                                },
                            }
                        ],
                    ),
                    admission=admission(),
                )
                feed = await get(client, "/api/discovery/watches")
                assert len(feed["candidates"]) == 1, feed
                candidate = feed["candidates"][0]
                assert candidate["advertised_item_price"] == "37.25"
                assert candidate["identity_state"] == "unresolved"
                assert candidate["offers"][0]["item_price"] is None
                raw = candidate["offers"][0]["source_evidence"]
                assert raw["selected_options"] == {"dial": "Space Gray"}
                assert raw["selected_sku"] is None
                assert raw["price_scope"] == "display_unbound"
                assert "selected_sku_stock" in raw["missing_fields"]
                claim = next(c for c in candidate["offers"][0]["evidence"] if c["field"] == "dial")
                assert claim["value"] == "Space Gray"
                assert claim["issuer_kind"] == "visible_observation"
                assert claim["route"] == "aliexpress_browser_first_v1"
                assert claim["retention"] == "synthetic"
                outcome = feed["captures"][0]["outcomes"][0]
                assert outcome["state"] == "partial"
                receipt = outcome["source_evidence"]
                assert receipt["discovered_count"] == 2
                assert receipt["inspected_count"] == 1
                assert receipt["pages_captured"] == 1
                assert receipt["page_limit"] == 1
                assert receipt["completeness"] == "partial"
                assert "product_inspection_capped" in receipt["issues"]
                assert receipt["history_rights"] == "unqualified"
                assert candidate["public_delivered_total"]["amount"] is None
                assert harness.deliveries == harness.blocked_edges == []
                if len(sys.argv) > 2:
                    Path(sys.argv[2]).write_text(json.dumps(feed, indent=2) + "\n")


@contextmanager
def browse_fixture(harness, *, error=None, enriched=False, retry=False, malformed=False):
    from pricerecon import connectors
    from pricerecon.connectors import ebay
    from pricerecon.core.collection_transport import collection_http_client

    def transport(request):
        harness.searches.append(("ebay", str(request.url)))
        if "oauth2" in request.url.path:
            return httpx.Response(
                200,
                json={
                    "access_token": "synthetic-not-a-credential",
                    "expires_in": 7200,
                    "token_type": "Application Access Token",
                },
            )
        if error:
            return httpx.Response(error, json={"errors": [{"message": "synthetic failure"}]})
        if retry and sum("item_summary" in url for _, url in harness.searches) == 1:
            return httpx.Response(401, json={"errors": [{"message": "synthetic expired token"}]})
        items = [
            {
                "itemId": "parent|0",
                "title": "Casio MTP-B145D varied suffixes",
                "price": {"value": "20.00", "currency": "GBP"},
                "itemWebUrl": "https://www.ebay.co.uk/itm/100?var=200",
                "seller": {"username": "Synthetic seller"},
                "condition": "Pre-owned - Good",
                "conditionId": "3000",
                "buyingOptions": ["AUCTION"],
                "currentBidPrice": {"value": "19.50", "currency": "GBP"},
            },
            {
                "itemId": "missing",
                "title": "Merkur Lightning salmon",
                "itemWebUrl": "https://www.ebay.co.uk/itm/101",
            },
        ]
        if enriched:
            items[0].update(
                {
                    "shipToLocationUsedForEstimate": {
                        "country": "GB",
                        "postalCode": "do-not-retain",
                    },
                    "estimatedAvailabilities": [
                        {"estimatedAvailabilityStatus": "IN_STOCK", "estimatedAvailableQuantity": 4}
                    ],
                    "shippingOptions": [
                        {
                            "shippingCostType": "FIXED",
                            "shippingCost": {"value": "5.00", "currency": "GBP"},
                        }
                    ],
                    "taxes": [],
                }
            )
        if malformed:
            items.append(
                {
                    "itemId": "bad",
                    "title": "Malformed",
                    "itemWebUrl": "https://www.ebay.co.uk/itm/102",
                    "price": {"value": "NaN", "currency": "GBP"},
                }
            )
        return httpx.Response(
            200,
            json={
                "total": 80,
                "next": "https://api.ebay.com/next?token=do-not-retain",
                "itemSummaries": items,
            },
        )

    with (
        patch.object(connectors, "discover_connectors", lambda: {"ebay": ebay.eBayConnector}),
        patch.object(
            ebay,
            "collection_http_client",
            lambda **kwargs: collection_http_client(transport=httpx.MockTransport(transport)),
        ),
    ):
        yield


async def ebay():
    with MonitoringHarness() as harness, browse_fixture(harness):
        from pricerecon.core.collection_policy import operating_policy
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryRequest

        policy = type(harness.test_policy).model_validate(
            {
                **harness.test_policy.model_dump(),
                "provider_request_caps": {"ebay": {"limit": 20, "tracking_reserve": 0}},
            }
        )
        with operating_policy(policy):
            async with harness.session() as (client, _):
                await execute_discovery(
                    DiscoveryRequest(
                        query="Casio OR Merkur",
                        sources=[
                            {
                                "connector": "ebay",
                                "config": {
                                    "app_id": "synthetic",
                                    "cert_id": "synthetic",
                                    "evidence_use": {
                                        "permission_reference": "original-fixture",
                                        "retention": "synthetic",
                                    },
                                },
                            }
                        ],
                    ),
                    admission=admission(),
                )
                feed = await get(client, "/api/discovery/watches")
                assert len(feed["candidates"]) == 2, feed
                parent = next(c for c in feed["candidates"] if c["source_listing_id"] == "parent|0")
                assert parent["advertised_item_price"] == "19.50"
                offer = parent["offers"][0]
                assert offer["source_evidence"]["condition_literal"] == "Pre-owned - Good"
                assert offer["source_evidence"]["purchase_modes"] == ["AUCTION"]
                assert offer["source_evidence"]["price_scope"] == "auction_bid"
                assert offer["source_evidence"]["selected_sku"] is None
                assert offer["availability"] is None
                assert offer["item_price"] is None
                assert parent["public_delivered_total"]["amount"] is None
                assert any(
                    c["field"] == "seller" and c["value"] == "Synthetic seller"
                    for c in offer["evidence"]
                )
                missing = next(c for c in feed["candidates"] if c["source_listing_id"] == "missing")
                assert missing["advertised_item_price"] is None
                assert missing["reported_currency"] is None
                receipt = feed["captures"][0]["outcomes"][0]["source_evidence"]
                assert receipt["route"] == "ebay_browse_search_v1"
                assert receipt["next_page"] is True
                assert receipt["pages_captured"] == receipt["page_limit"] == 1
                assert receipt["discovered_count"] == 80
                assert receipt["inspected_count"] == 2
                assert receipt["history_rights"] == "unqualified"
                assert "do-not-retain" not in str(feed)
                assert len(harness.searches) == 2  # one token plus one Browse page
                assert harness.deliveries == harness.blocked_edges == []


@contextmanager
def retailer_fixture(harness):
    from pricerecon import connectors
    from pricerecon.connectors import shopify
    from pricerecon.core.collection_transport import collection_http_client

    def transport(request):
        harness.searches.append(("shopify", str(request.url)))
        if "products.json" not in request.url.path:
            return httpx.Response(200, text="Original synthetic retailer search")
        return httpx.Response(
            200,
            json={
                "products": [
                    {
                        "id": 123,
                        "handle": "synthetic-sn0144",
                        "title": "San Martin SN0144",
                        "options": [
                            {"name": "Movement", "position": 1},
                            {"name": "Strap", "position": 2},
                        ],
                        "variants": [
                            {
                                "id": 201,
                                "option1": "NH35",
                                "option2": "FKM",
                                "price": "110.00",
                                "currency": "GBP",
                                "available": True,
                            },
                            {
                                "id": 202,
                                "option1": "Miyota",
                                "option2": "bracelet",
                                "price": "180.00",
                            },
                        ],
                    }
                ]
            },
        )

    with (
        patch.object(
            connectors, "discover_connectors", lambda: {"shopify": shopify.ShopifyConnector}
        ),
        patch.object(
            shopify,
            "collection_http_client",
            lambda **kwargs: collection_http_client(transport=httpx.MockTransport(transport)),
            create=True,
        ),
    ):
        yield


async def retailer():
    with MonitoringHarness() as harness, retailer_fixture(harness):
        from pricerecon.core.collection_policy import operating_policy
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryRequest

        policy = type(harness.test_policy).model_validate(
            {
                **harness.test_policy.model_dump(),
                "provider_request_caps": {"shopify": {"limit": 20, "tracking_reserve": 0}},
            }
        )
        with operating_policy(policy):
            async with harness.session() as (client, _):
                await execute_discovery(
                    DiscoveryRequest(
                        query="SN0144",
                        sources=[
                            {
                                "connector": "shopify",
                                "config": {
                                    "base_url": "https://www.sanmartin.watch",
                                    "evidence_use": {
                                        "permission_reference": "original-fixture",
                                        "retention": "synthetic",
                                    },
                                },
                            }
                        ],
                    ),
                    admission=admission(),
                )
                feed = await get(client, "/api/discovery/watches")
                assert len(feed["candidates"]) == 2, feed
                first = next(c for c in feed["candidates"] if c["source_listing_id"] == "201")
                second = next(c for c in feed["candidates"] if c["source_listing_id"] == "202")
                assert first["advertised_item_price"] == "110.00"
                assert second["advertised_item_price"] == "180.00"
                assert second["reported_currency"] is None
                assert first["offers"][0]["source_evidence"]["selected_options"] == {
                    "movement": "NH35",
                    "strap": "FKM",
                }
                assert second["offers"][0]["source_evidence"]["selected_options"] == {
                    "movement": "Miyota",
                    "strap": "bracelet",
                }
                assert (
                    first["offers"][0]["source_evidence"]["merchant_role"] == "independent_retailer"
                )
                assert all(
                    c["identity_state"] == "unresolved"
                    and c["public_delivered_total"]["amount"] is None
                    for c in feed["candidates"]
                )
                assert len(harness.searches) == 2
                assert harness.deliveries == harness.blocked_edges == []


async def retailer_watch():
    with MonitoringHarness() as harness, retailer_fixture(harness):
        from pricerecon.core.collection_policy import operating_policy

        from .workflows import LEGACY

        harness.seed_legacy(
            [
                (
                    7,
                    {
                        **LEGACY,
                        "query": "SN0144",
                        "synonym_groups": [],
                        "source_queries": {},
                        "filters": {},
                        "sources": [
                            {
                                "connector": "shopify",
                                "config": {"base_url": "https://www.sanmartin.watch"},
                            }
                        ],
                    },
                )
            ]
        )
        policy = type(harness.test_policy).model_validate(
            {
                **harness.test_policy.model_dump(),
                "provider_request_caps": {"shopify": {"limit": 20, "tracking_reserve": 0}},
            }
        )
        with operating_policy(policy):
            async with harness.session() as (client, _):
                for _ in range(2):
                    response = await client.post("/api/watches/7/check")
                    assert response.status_code == 200, response.text
                    assert response.json()["status"] == "completed"
                    result = response.json()["result"]
                    assert result["success"] is True
                    assert result["listings_found"] == 2
                    assert result["notifications_sent"] == 0
                listings = await get(client, "/api/watches/7/listings")
                assert {item["source_listing_id"] for item in listings["items"]} == {"201", "202"}
                assert (await get(client, "/api/watches/7"))[
                    "last_check_at"
                ] == "2026-10-27T12:00:00Z"
                assert len(harness.searches) == 4
                assert harness.deliveries == harness.blocked_edges == []


async def gates():
    with MonitoringHarness() as harness:
        from pricerecon import connectors
        from pricerecon.connectors.aliexpress import AliExpressConnector
        from pricerecon.connectors.ebay import eBayConnector
        from pricerecon.core import acquisition
        from pricerecon.core.collection_policy import operating_policy
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryRequest

        policy = type(harness.test_policy).model_validate(
            {
                **harness.test_policy.model_dump(),
                "provider_request_caps": {
                    source: {"limit": 20, "tracking_reserve": 0}
                    for source in ("ebay", "aliexpress")
                },
            }
        )
        with (
            operating_policy(policy),
            patch.object(
                connectors,
                "discover_connectors",
                lambda: {"ebay": eBayConnector, "aliexpress": AliExpressConnector},
            ),
            patch.object(
                acquisition,
                "load_config",
                lambda: {
                    "browser_backends": {
                        "fixture": {"type": "cloakbrowser", "endpoint": "https://forbidden.invalid"}
                    }
                },
            ),
        ):
            async with harness.session() as (client, _):
                await execute_discovery(
                    DiscoveryRequest(
                        query="watch",
                        sources=[{"connector": "ebay", "config": {"app_id": "synthetic"}}],
                    ),
                    admission=admission(),
                )
                feed = await get(client, "/api/discovery/watches")
                outcome = feed["captures"][0]["outcomes"][0]
                assert outcome["state"] == "blocked"
                assert outcome["source_evidence"]["use"] is None
                assert outcome["source_evidence"]["prerequisites"]
                # Named browser setup is synthetic metadata; no actual browser work
                # is authorised and its origin subrequests cannot yet be bounded.
                await execute_discovery(
                    DiscoveryRequest(
                        query="AD2066",
                        sources=[
                            {
                                "connector": "aliexpress",
                                "config": {
                                    "evidence_use": {
                                        "permission_reference": "original-fixture",
                                        "retention": "synthetic",
                                    },
                                    "browser_backend": "fixture",
                                    "browser_backends": {
                                        "fixture": {
                                            "type": "cloakbrowser",
                                            "endpoint": "https://forbidden.invalid",
                                        }
                                    },
                                },
                            }
                        ],
                    ),
                    admission=admission(),
                )
                feed = await get(client, "/api/discovery/watches")
                outcome = feed["captures"][0]["outcomes"][0]
                assert outcome["state"] == "blocked", outcome
                assert outcome["reason"] == "browser_origin_accounting_unavailable", outcome
                assert outcome["source_evidence"]["route"] == "aliexpress_browser_first_v1"
                state = await get(client, "/api/discovery/collection")
                assert all(u["used"] == 0 for u in state["usage"] if u["resource"] == "requests")
                assert harness.searches == harness.deliveries == harness.blocked_edges == []


async def failure():
    with MonitoringHarness() as harness:
        from pricerecon.core.collection_policy import operating_policy
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryRequest

        policy = type(harness.test_policy).model_validate(
            {
                **harness.test_policy.model_dump(),
                "provider_request_caps": {"ebay": {"limit": 20, "tracking_reserve": 0}},
            }
        )
        request = DiscoveryRequest(
            query="Casio",
            sources=[
                {
                    "connector": "ebay",
                    "config": {
                        "app_id": "synthetic",
                        "cert_id": "synthetic",
                        "evidence_use": {
                            "permission_reference": "original-fixture",
                            "retention": "synthetic",
                        },
                    },
                }
            ],
        )
        with operating_policy(policy), browse_fixture(harness):
            async with harness.session() as (client, _):
                await execute_discovery(request, admission=admission())
                before = await get(client, "/api/discovery/watches")
                harness.clock.advance()
                with browse_fixture(harness, error=429):
                    await execute_discovery(request, admission=admission())
                after = await get(client, "/api/discovery/watches")
                outcome = after["captures"][0]["outcomes"][0]
                assert outcome["state"] == "blocked", outcome
                assert outcome["reason"] == "rate_limited", outcome
                assert outcome["source_evidence"]["route"] == "ebay_browse_search_v1"
                assert outcome["source_evidence"]["pages_captured"] == 0
                assert after["candidates"] == before["candidates"]
                assert harness.deliveries == harness.blocked_edges == []


async def roster():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            feed = await get(client, "/api/discovery/watches")
            rows = feed["source_coverage"]
            assert {r["family"] for r in rows} == {
                "aliexpress",
                "ebay_secondhand",
                "brand_direct",
                "uk_retail",
                "uk_shipping_international",
                "search_aggregator_community",
            }
            assert len(rows) == 16
            assert all(
                row["activation"] == "staged"
                and row["last_outcome"] is None
                and row["prerequisites"]
                for row in rows
            )
            militado = next(row for row in rows if row["source"] == "Militado")
            assert militado["accepted_status"] == "blocked"
            assert "recognized Web Bot Auth signer" in militado["prerequisites"]
            assert any("Merkur" in gap for gap in feed["cohort_gaps"])
            assert any("Militado" in gap for gap in feed["cohort_gaps"])
            assert harness.searches == harness.deliveries == harness.blocked_edges == []


async def restart(seed):
    with MonitoringHarness(storage_root=Path(sys.argv[2])) as harness, browser_fixture(harness):
        from pricerecon.core.collection_policy import operating_policy
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryRequest

        policy = type(harness.test_policy).model_validate(
            {
                **harness.test_policy.model_dump(),
                "provider_request_caps": {"aliexpress": {"limit": 20, "tracking_reserve": 0}},
            }
        )
        with operating_policy(policy):
            async with harness.session() as (client, _):
                if seed:
                    await execute_discovery(
                        DiscoveryRequest(
                            query="AD2066",
                            sources=[
                                {
                                    "connector": "aliexpress",
                                    "config": {
                                        "browser_max_products": 1,
                                        "evidence_use": {
                                            "permission_reference": "original-fixture",
                                            "retention": "synthetic",
                                        },
                                    },
                                }
                            ],
                        ),
                        admission=admission(),
                    )
                else:
                    harness.clock.advance(hours=24)
                feed = await get(client, "/api/discovery/watches")
                assert len(feed["candidates"]) == 1
                candidate = feed["candidates"][0]
                assert candidate["captured_at"] == "2026-10-27T12:00:00Z"
                assert candidate["offers"][0]["source_evidence"]["selected_options"] == {
                    "dial": "Space Gray"
                }
                receipt = feed["captures"][0]["outcomes"][0]["source_evidence"]
                assert receipt["retrieved_at"] == "2026-10-27T12:00:00Z"
                assert receipt["inspected_count"] == 1
                coverage = next(
                    row
                    for row in feed["source_coverage"]
                    if row["route"] == "aliexpress_browser_first_v1"
                )
                assert coverage["last_outcome"]["source_evidence"] == receipt
                assert harness.searches == (
                    []
                    if not seed
                    else [
                        ("aliexpress", "https://www.aliexpress.com/w/wholesale-ad2066.html"),
                        ("aliexpress", "https://www.aliexpress.com/item/10000000000001.html"),
                    ]
                )
                assert harness.deliveries == harness.blocked_edges == []


async def restart_seed():
    await restart(True)


async def restart_read():
    await restart(False)


async def source_context():
    with MonitoringHarness() as harness, browse_fixture(harness, enriched=True):
        from pricerecon.core.collection_policy import operating_policy
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryRequest

        policy = type(harness.test_policy).model_validate(
            {
                **harness.test_policy.model_dump(),
                "provider_request_caps": {"ebay": {"limit": 20, "tracking_reserve": 0}},
            }
        )
        with operating_policy(policy):
            async with harness.session() as (client, _):
                await execute_discovery(
                    DiscoveryRequest(
                        query="Casio",
                        sources=[
                            {
                                "connector": "ebay",
                                "config": {
                                    "app_id": "synthetic",
                                    "cert_id": "synthetic",
                                    "evidence_use": {
                                        "permission_reference": "original-fixture",
                                        "retention": "synthetic",
                                    },
                                },
                            }
                        ],
                    ),
                    admission=admission(),
                )
                feed = await get(client, "/api/discovery/watches")
                parent = next(c for c in feed["candidates"] if c["source_listing_id"] == "parent|0")
                observed = parent["offers"][0]["source_evidence"]
                assert observed["destination"] == "GB"
                assert observed["availability_literal"] == "IN_STOCK"
                assert observed["stock_quantity"] == 4
                assert observed["shipping_claim"] == "FIXED GBP 5.00"
                assert "taxes_unknown" in observed["missing_fields"]
                assert parent["offers"][0]["destination"] is None
                assert parent["offers"][0]["availability"] is None
                assert parent["public_delivered_total"]["amount"] is None
                assert "do-not-retain" not in str(feed)
                assert harness.deliveries == harness.blocked_edges == []


async def retry_case(capped=False, malformed=False):
    with (
        MonitoringHarness() as harness,
        browse_fixture(harness, retry=not malformed, malformed=malformed),
    ):
        from pricerecon.core.collection_policy import operating_policy
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryRequest

        policy = type(harness.test_policy).model_validate(
            {
                **harness.test_policy.model_dump(),
                "provider_request_caps": {"ebay": {"limit": 20, "tracking_reserve": 0}},
                "caps": {
                    **harness.test_policy.model_dump()["caps"],
                    "requests": {"limit": 2 if capped else 10, "tracking_reserve": 0},
                },
            }
        )
        with operating_policy(policy):
            async with harness.session() as (client, _):
                await execute_discovery(
                    DiscoveryRequest(
                        query="Casio",
                        sources=[
                            {
                                "connector": "ebay",
                                "config": {
                                    "app_id": "synthetic",
                                    "cert_id": "synthetic",
                                    "evidence_use": {
                                        "permission_reference": "original-fixture",
                                        "retention": "synthetic",
                                    },
                                },
                            }
                        ],
                    ),
                    admission=admission(),
                )
                feed = await get(client, "/api/discovery/watches")
                state = await get(client, "/api/discovery/collection")
                outcome = feed["captures"][0]["outcomes"][0]
                if capped:
                    assert outcome["state"] == "capped", outcome
                    assert len(harness.searches) == 2
                    assert feed["candidates"] == []
                else:
                    assert outcome["state"] == "partial", outcome
                    assert len(feed["candidates"]) == 2
                    if malformed:
                        assert "invalid_item:2" in outcome["source_evidence"]["issues"]
                        assert len(harness.searches) == 2
                    else:
                        assert len(harness.searches) == 4
                        assert (
                            next(u["used"] for u in state["usage"] if u["resource"] == "retries")
                            == 2
                        )
                assert next(
                    u["used"] for u in state["usage"] if u["resource"] == "requests"
                ) == len(harness.searches)
                assert harness.deliveries == harness.blocked_edges == []


async def retry_admitted():
    await retry_case()


async def retry_capped():
    await retry_case(capped=True)


async def malformed():
    await retry_case(malformed=True)


async def truncated():
    with MonitoringHarness() as harness, browser_fixture(harness, truncated=True):
        from pricerecon.core.collection_policy import operating_policy
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryRequest

        policy = type(harness.test_policy).model_validate(
            {
                **harness.test_policy.model_dump(),
                "provider_request_caps": {"aliexpress": {"limit": 20, "tracking_reserve": 0}},
            }
        )
        with operating_policy(policy):
            async with harness.session() as (client, _):
                await execute_discovery(
                    DiscoveryRequest(
                        query="AD2066",
                        sources=[
                            {
                                "connector": "aliexpress",
                                "config": {
                                    "browser_max_products": 1,
                                    "evidence_use": {
                                        "permission_reference": "original-fixture",
                                        "retention": "synthetic",
                                    },
                                },
                            }
                        ],
                    ),
                    admission=admission(),
                )
                feed = await get(client, "/api/discovery/watches")
                receipt = feed["captures"][0]["outcomes"][0]["source_evidence"]
                assert receipt["content_truncated"] is True
                assert "truncated_product_content" in receipt["issues"]
                assert feed["candidates"][0]["public_delivered_total"]["amount"] is None
                assert harness.deliveries == harness.blocked_edges == []


async def militado_gate():
    with MonitoringHarness() as harness, retailer_fixture(harness):
        from pricerecon.core.collection_policy import operating_policy
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryRequest

        policy = type(harness.test_policy).model_validate(
            {
                **harness.test_policy.model_dump(),
                "provider_request_caps": {"shopify": {"limit": 20, "tracking_reserve": 0}},
            }
        )
        with operating_policy(policy):
            async with harness.session() as (client, _):
                await execute_discovery(
                    DiscoveryRequest(
                        query="ML05",
                        sources=[
                            {
                                "connector": "shopify",
                                "config": {
                                    "base_url": "https://www.militadowatch.com",
                                    "evidence_use": {
                                        "permission_reference": "original-fixture",
                                        "retention": "synthetic",
                                    },
                                },
                            }
                        ],
                    ),
                    admission=admission(),
                )
                feed = await get(client, "/api/discovery/watches")
                outcome = feed["captures"][0]["outcomes"][0]
                assert outcome["state"] == "blocked", outcome
                assert (
                    "recognized Web Bot Auth signer" in outcome["source_evidence"]["prerequisites"]
                )
                assert feed["candidates"] == []
                assert harness.searches == harness.deliveries == harness.blocked_edges == []


async def discovery_truncated():
    with MonitoringHarness() as harness, browser_fixture(harness, discovery_truncated=True):
        from pricerecon.core.collection_policy import operating_policy
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryRequest

        policy = type(harness.test_policy).model_validate(
            {
                **harness.test_policy.model_dump(),
                "provider_request_caps": {"aliexpress": {"limit": 20, "tracking_reserve": 0}},
            }
        )
        with operating_policy(policy):
            async with harness.session() as (client, _):
                await execute_discovery(
                    DiscoveryRequest(
                        query="AD2066",
                        sources=[
                            {
                                "connector": "aliexpress",
                                "config": {
                                    "browser_max_products": 1,
                                    "evidence_use": {
                                        "permission_reference": "original-fixture",
                                        "retention": "synthetic",
                                    },
                                },
                            }
                        ],
                    ),
                    admission=admission(),
                )
                feed = await get(client, "/api/discovery/watches")
                outcome = feed["captures"][0]["outcomes"][0]
                assert outcome["state"] == "failed", outcome
                assert feed["candidates"] == []
                assert outcome["source_evidence"]["content_truncated"] is True
                assert outcome["source_evidence"]["pages_captured"] == 1
                assert outcome["source_evidence"]["detail_limit"] == 1
                assert "truncated_discovery_content" in outcome["source_evidence"]["issues"]
                assert harness.deliveries == harness.blocked_edges == []


async def assessment_interaction():
    with MonitoringHarness() as harness:
        from .assessment_workflows import policy
        from .source_evidence_ui_fixture import populate

        async with harness.session() as (client, _):
            supplied = policy(harness).model_copy(
                update={"sources": ["aliexpress", "ebay", "shopify"]}
            )
            await populate(harness, supplied)
            feed = await get(client, "/api/discovery/watches")
            assert len(feed["candidates"]) == 5
            assert all(c["public_delivered_total"]["amount"] is None for c in feed["candidates"])
            assessments = await get(client, "/api/discovery/assessments")
            for assessment in assessments["items"]:
                assert assessment["current_best"]["amount"] is None
                assert assessment["observed_low"]["amount"] is None
                assert assessment["usual_price"]["amount"] is None
                assert assessment["savings"] is None
            assert all(c["offers"][0]["source_evidence"] is not None for c in feed["candidates"])
            assert (
                len([row for row in feed["source_coverage"] if row["last_outcome"] is not None])
                == 3
            )
            assert harness.deliveries == harness.blocked_edges == []


if __name__ == "__main__":
    asyncio.run(globals()[sys.argv[1]]())
