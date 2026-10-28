"""Application-seam discovery workflows; import app only after isolation guards."""

import asyncio
import sys
from pathlib import Path

from .harness import MonitoringHarness
from .workflows import get, listing


async def independent():
    with MonitoringHarness() as harness:
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest

        harness.outcomes["cex"] = [
            listing(harness, "cex", "new-mint", "Addiesdive AD2066 mint", "48.00")
        ]
        async with harness.session() as (client, scheduler):
            assert (await get(client, "/api/watches"))["items"] == []
            report = await execute_discovery(
                DiscoveryRequest(query="wristwatch", sources=[{"connector": "cex"}]),
                admission=DiscoveryAdmission(
                    policy_reference="fixture-policy-v1",
                    permission_reference="offline-fixtures",
                    activation_reference="isolated-harness",
                    mode="offline_verification",
                ),
            )
            feed = await get(client, "/api/discovery/watches")
            assert len(feed["candidates"]) == 1
            candidate = feed["candidates"][0]
            assert candidate["title"] == "Addiesdive AD2066 mint"
            assert candidate["origin"] == "category_discovery"
            assert candidate["query"] == "wristwatch"
            assert candidate["capture_id"] == report.capture_id
            assert candidate["captured_at"] == "2026-10-27T12:00:00Z"
            assert candidate["evidence"][0]["capture_id"] == report.capture_id
            assert candidate["evidence"][0]["value"] == "Addiesdive AD2066 mint"
            assert candidate["identity_state"] == "unresolved"
            assert candidate["public_delivered_total"]["state"] == "unknown"
            assert candidate["usual_price"]["state"] == "unavailable"
            assert candidate["alert_eligible"] is False
            assert candidate["image"]["kind"] == "original_placeholder"
            assert harness.searches == [("cex", "wristwatch", {})]
            assert scheduler.list_watches() == []
            assert harness.deliveries == []
            assert harness.blocked_edges == []
        async with harness.session() as (client, _):
            assert (await get(client, "/api/discovery/watches"))["candidates"][0][
                "id"
            ] == candidate["id"]


async def permitted_image():
    with MonitoringHarness() as harness:
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest

        item = listing(harness, "cex", "image-control", "Synthetic image contract control")
        item.discovery_image = {
            "kind": "photo",
            "url": "https://assets.invalid/control.jpg",
            "attribution": "Offline fixture author",
            "provenance": "Synthetic contract metadata only",
            "permission_reference": "fixture-permission-v1",
            "identity_reference": "fixture-depiction-v1",
            "source_listing_id": "image-control",
            "depicts_exact_watch": True,
        }
        harness.outcomes["cex"] = [item]
        async with harness.session() as (client, _):
            await execute_discovery(
                DiscoveryRequest(query="control", sources=[{"connector": "cex"}]),
                admission=DiscoveryAdmission(
                    mode="offline_verification",
                    policy_reference="fixture",
                    permission_reference="fixture",
                    activation_reference="harness",
                ),
            )
            image = (await get(client, "/api/discovery/watches"))["candidates"][0]["image"]
            assert image["kind"] == "photo"
            assert image["attribution"] == "Offline fixture author"
            assert image["permission_reference"] == "fixture-permission-v1"
            assert image["identity_reference"] == "fixture-depiction-v1"
        async with harness.session() as (client, _):
            assert (await get(client, "/api/discovery/watches"))["candidates"][0]["image"] == image
        assert harness.blocked_edges == []
        assert harness.deliveries == []


async def image_rejections():
    with MonitoringHarness() as harness:
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest

        base = {
            "kind": "illustration",
            "url": "https://assets.invalid/control.png",
            "attribution": "Fixture artist",
            "provenance": "Synthetic contract control",
            "permission_reference": "fixture-rights",
            "identity_reference": "fixture-identity",
            "source_listing_id": "control",
            "depicts_exact_watch": True,
        }
        changes = [
            {"source_listing_id": "other-watch"},
            {"depicts_exact_watch": False},
            {"permission_reference": " "},
            {"identity_reference": ""},
            {"url": "javascript:alert(1)"},
            {"url": "https://user:secret@assets.invalid/a"},
            {"url": "https://assets.invalid/a?token=secret"},
            {"kind": "unknown"},
            *(
                {"url": url}
                for url in [
                    "https://assets.invalid:999999/control.jpg",
                    "https://assets.invalid:no/control.jpg",
                    "https://assets.invalid\\evil/control.jpg",
                    "https://%zz/control.jpg",
                    "https://256.256.256.256/control.jpg",
                ]
            ),
        ]
        items = []
        for index, change in enumerate(changes):
            item = listing(harness, "cex", str(index), "Rejected image control")
            item.discovery_image = {**base, "source_listing_id": str(index), **change}
            items.append(item)
        valid = listing(harness, "cex", "control", "Illustration control")
        valid.discovery_image = base
        harness.outcomes["cex"] = [*items, valid]
        async with harness.session() as (client, _):
            await execute_discovery(
                DiscoveryRequest(query="control", sources=[{"connector": "cex"}]),
                admission=DiscoveryAdmission(
                    mode="offline_verification",
                    policy_reference="fixture",
                    permission_reference="fixture",
                    activation_reference="harness",
                ),
            )
            feed = (await get(client, "/api/discovery/watches"))["candidates"]
            assert len(feed) == len(changes) + 1
            for candidate in feed:
                assert candidate["image"]["kind"] == (
                    "illustration"
                    if candidate["source_listing_id"] == "control"
                    else "original_placeholder"
                )
            valid_image = next(c["image"] for c in feed if c["source_listing_id"] == "control")
            assert valid_image["attribution"] == "Fixture artist"
            assert valid_image["permission_reference"] == "fixture-rights"
        async with harness.session() as (client, _):
            assert (await get(client, "/api/discovery/watches"))["candidates"] == feed
        assert harness.blocked_edges == []
        assert harness.deliveries == []


async def query_lineage():
    with MonitoringHarness() as harness:
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest

        harness.outcomes["cex"] = [listing(harness, "legacy-cex", "mint", "Addiesdive AD2066 mint")]
        async with harness.session() as (client, _):
            await execute_discovery(
                DiscoveryRequest(
                    query="broad wristwatch",
                    sources=[{"connector": "cex"}],
                    source_queries={"cex": ' (wristwatch OR "montre") '},
                ),
                admission=DiscoveryAdmission(
                    mode="offline_verification",
                    policy_reference="fixture-v1",
                    permission_reference="fixtures",
                    activation_reference="harness",
                ),
            )
            candidate = (await get(client, "/api/discovery/watches"))["candidates"][0]
            assert candidate["query"] == ' (wristwatch OR "montre") '
            assert candidate["source"] == "cex"
            assert candidate["reported_source"] == "legacy-cex"
            assert candidate["evidence"][0]["issuer"] == "cex"
            assert harness.searches == [("cex", ' (wristwatch OR "montre") ', {})]
            assert harness.blocked_edges == []
            assert harness.deliveries == []


async def preferences():
    with MonitoringHarness() as harness:
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest

        harness.outcomes["cex"] = [listing(harness, "cex", "mint", "Addiesdive AD2066 mint")]
        async with harness.session() as (client, _):
            original = await get(client, "/api/discovery/watches/preferences")
            assert original["values"]["compact_max_width_mm"] is None
            assert original["values"]["budget_gbp"] is None
            assert original["values"]["colourful_dials"] == []
            assert original["revision"] == 0
            await execute_discovery(
                DiscoveryRequest(query="wristwatch", sources=[{"connector": "cex"}]),
                admission=DiscoveryAdmission(
                    mode="offline_verification",
                    policy_reference="fixture-v1",
                    permission_reference="fixtures",
                    activation_reference="harness",
                ),
            )
            values = {
                "compact_max_width_mm": "37.5",
                "compact_strength": "hard",
                "colourful_dials": ["mint", "salmon"],
                "colourful_strength": "soft",
                "budget_gbp": "120.25",
                "budget_strength": "hard",
            }
            response = await client.put(
                "/api/discovery/watches/preferences",
                json={
                    "expected_revision": 0,
                    "values": values,
                },
            )
            assert response.status_code == 200, response.text
            saved = response.json()
            assert saved["values"] == values
            assert saved["revision"] == 1
            assert "37.5 mm" in saved["interpretation"][0]["meaning"]
            assert saved["interpretation"][0]["strength"] == "hard"
            assert saved["interpretation"][1]["strength"] == "soft"
            feed = await get(client, "/api/discovery/watches")
            assert len(feed["candidates"]) == 1
            assert [fit["state"] for fit in feed["candidates"][0]["preference_fit"]] == [
                "unknown"
            ] * 3
            assert (
                feed["candidates"][0]["preference_fit"][2]["reason"]
                == "Delivered total unknown; an item price cannot satisfy this budget."
            )
            assert (
                await client.put(
                    "/api/discovery/watches/preferences",
                    json={
                        "expected_revision": 0,
                        "values": values,
                    },
                )
            ).status_code == 409
            assert (
                await client.put(
                    "/api/discovery/watches/preferences",
                    json={
                        "expected_revision": 1,
                        "values": {**values, "budget_gbp": "-1"},
                    },
                )
            ).status_code == 422
        async with harness.session() as (client, _):
            assert (await get(client, "/api/discovery/watches/preferences")) == saved
            assert len((await get(client, "/api/discovery/watches"))["candidates"]) == 1
            assert harness.deliveries == []
            assert harness.blocked_edges == []


async def coverage():
    with MonitoringHarness() as harness:
        from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest

        request = DiscoveryRequest(
            query="wristwatch",
            sources=[
                {"connector": "cex", "config": {"credential": "do-not-expose"}},
                {"connector": "scan"},
                {"connector": "ebay", "enabled": False},
            ],
            source_queries={"cex": "colourful compact watch"},
        )
        admission = DiscoveryAdmission(
            mode="offline_verification",
            policy_reference="fixture-v1",
            permission_reference="fixtures",
            activation_reference="harness",
        )
        async with harness.session() as (client, _):
            denied = await execute_discovery(request)
            assert [outcome.state for outcome in denied.outcomes] == ["not_attempted"] * 3
            assert harness.searches == []
            harness.outcomes["cex"] = [
                listing(harness, "cex", str(i), title)
                for i, title in enumerate(
                    [
                        "Militado ML05/ML05B",
                        "Addiesdive AD2066 mint",
                        "San Martin SN0144",
                        "Merkur Lightning salmon",
                        "Casio MTP-B145D-2A2VEF",
                    ]
                )
            ]
            harness.outcomes["cex"][0].exact_variant_confirmed = True
            harness.outcomes["cex"][0].total_landed_cost = 1
            harness.outcomes["cex"][0].image_url = "https://unpermitted.invalid/photo.jpg"
            harness.outcomes["cex"][0].url = "javascript:alert(1)"
            await execute_discovery(request, admission=admission)
            feed = await get(client, "/api/discovery/watches")
            assert len(feed["candidates"]) == 5
            assert [outcome["state"] for outcome in feed["captures"][0]["outcomes"]] == [
                "success",
                "success_empty",
                "not_attempted",
            ]
            assert feed["captures"][0]["outcomes"][0]["listing_count"] == 5
            assert "do-not-expose" not in str(feed)
            first = next(
                candidate
                for candidate in feed["candidates"]
                if candidate["source_listing_id"] == "0"
            )
            assert first["url"] is None
            assert first["identity_state"] == "unresolved"
            assert first["public_delivered_total"]["amount"] is None
            assert first["image"]["kind"] == "original_placeholder"
            harness.clock.advance()
            harness.outcomes["cex"] = ConnectorDegradedError(
                ConnectorStatus.parse_error, "bad parse", "cex"
            )
            harness.outcomes["scan"] = ConnectorDegradedError(
                ConnectorStatus.rate_limited, "cap", "scan", {"capped": True}
            )
            await execute_discovery(request, admission=admission)
            feed = await get(client, "/api/discovery/watches")
            assert [outcome["state"] for outcome in feed["captures"][0]["outcomes"]] == [
                "failed",
                "capped",
                "not_attempted",
            ]
            assert len(feed["candidates"]) == 5
            assert all(
                candidate["captured_at"] == "2026-10-27T12:00:00Z"
                for candidate in feed["candidates"]
            )
            assert all(candidate["alert_eligible"] is False for candidate in feed["candidates"])
            assert harness.deliveries == []
            assert harness.blocked_edges == []


async def restart(before):
    with MonitoringHarness(storage_root=Path(sys.argv[2])) as harness:
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest

        async with harness.session() as (client, _):
            if before:
                missing_price = listing(harness, "cex", "no-price", "Unknown wristwatch")
                missing_price.price = None
                lead = listing(harness, "cex", "repeat", "Militado ML05/ML05B")
                harness.outcomes["cex"] = [lead, lead, missing_price]
                await execute_discovery(
                    DiscoveryRequest(query="wristwatch", sources=[{"connector": "cex"}]),
                    admission=DiscoveryAdmission(
                        mode="offline_verification",
                        policy_reference="fixture-v1",
                        permission_reference="fixtures",
                        activation_reference="harness",
                    ),
                )
                response = await client.put(
                    "/api/discovery/watches/preferences",
                    json={
                        "expected_revision": 0,
                        "values": {"budget_gbp": "60.01"},
                    },
                )
                assert response.status_code == 200, response.text
            feed = await get(client, "/api/discovery/watches")
            assert len(feed["candidates"]) == 2
            assert len(feed["captures"]) == 1
            assert feed["captures"][0]["outcomes"][0]["listing_count"] == 3
            assert feed["preferences"]["values"]["budget_gbp"] == "60.01"
            assert feed["preferences"]["revision"] == 1
            unknown = next(
                candidate
                for candidate in feed["candidates"]
                if candidate["source_listing_id"] == "no-price"
            )
            assert unknown["advertised_item_price"] is None
            assert len(unknown["evidence"]) == 1
            assert (
                len(
                    next(
                        candidate
                        for candidate in feed["candidates"]
                        if candidate["source_listing_id"] == "repeat"
                    )["evidence"]
                )
                == 2
            )
            assert all(
                candidate["captured_at"] == "2026-10-27T12:00:00Z"
                for candidate in feed["candidates"]
            )
            assert harness.searches == ([] if not before else [("cex", "wristwatch", {})])
            assert harness.deliveries == []
            assert harness.blocked_edges == []


async def before_restart():
    await restart(True)


async def after_restart():
    await restart(False)


if __name__ == "__main__":
    asyncio.run(globals()[sys.argv[1]]())
