"""Review regressions at the approved guarded application boundary."""

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import patch

import httpx

from .harness import MonitoringHarness


async def coupon_conflict(case, output):
    from .cost_workflows import read_capture
    from .coupon_workflows import reproduced_report

    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            valid = reproduced_report(harness)
            expired = valid.model_copy(deep=True)
            expired.coupons[0].terms.ends_at = harness.clock.now
            expired.coupons[0].terms.literal = "Conflicting synthetic terms: expired now"
            reports = {
                "valid-first": [valid, expired],
                "expired-first": [expired, valid],
                "valid-only": [valid],
                "identical": [valid, valid.model_copy(deep=True)],
                "same-report": [valid],
            }[case]
            if case == "same-report":
                valid.coupons.append(expired.coupons[0])
            feed = await read_capture(harness, client, reports)
            candidate = feed["candidates"][0]
            coupon = candidate["offers"][0]["coupons"][0]
            output.write_text(json.dumps(feed, indent=2) + "\n")
            assert candidate["public_delivered_total"]["amount"] == "50.10"
            if case in {"valid-only", "identical"}:
                assert coupon["resulting_cost"]["total"]["amount"] == "45.10"
                assert coupon["source_conflicts"] == []
                assert coupon["issues"] == []
            else:
                assert coupon["resulting_cost"] is None
                assert "conflicting_coupon_inputs" in coupon["issues"]
                assert len(coupon["source_conflicts"]) == 1
            assert harness.deliveries == harness.blocked_edges == []


async def retained_definition(case, output):
    from .cost_workflows import read_capture
    from .history_workflows import priced_report
    from .tracking_workflows import capture, track
    from .workflows import get

    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            from pricerecon.core import notifications

            original = priced_report(harness, "68.00")
            candidate = (await read_capture(harness, client, [original]))["candidates"][0]
            saved = await track(client, candidate, notifications={"channels": ["webhook"]})
            with patch.object(
                notifications,
                "get_global_notification_config",
                lambda: {"webhook_url": "https://synthetic.invalid/captured-send"},
            ):
                await capture(harness, client, original)
                harness.clock.advance(hours=3 if case == "stale" else 0.5)
                fresh = priced_report(harness, "56.00")
                if case != "fresh":
                    fresh.claims = [
                        (
                            next(
                                c
                                for c in original.claims
                                if c.subject == claim.subject and c.field == claim.field
                            ).model_copy(deep=True)
                            if claim.subject == "configuration"
                            else claim
                        )
                        for claim in fresh.claims
                    ]
                if case == "unknown":
                    for claim in fresh.claims:
                        if claim.subject == "configuration":
                            claim.observed_at = None
                await capture(harness, client, fresh)
                after = await get(client, f"/api/discovery/tracking/{saved['id']}")
                history = await get(client, f"/api/discovery/candidates/{candidate['id']}/history")
                events = await get(client, "/api/events")
                output.write_text(
                    json.dumps(
                        {
                            "tracking": after,
                            "events": events,
                            "latest_history": history["observations"][-1],
                            "deliveries": harness.deliveries,
                            "blocked_edges": harness.blocked_edges,
                        },
                        indent=2,
                    )
                    + "\n"
                )
                if case in {"stale", "unknown"}:
                    assert after["assessment"]["state"] == "withheld"
                    assert events["total"] == len(harness.deliveries) == 0
                else:
                    assert history["observations"][-1]["validity"] == "supported_at_capture"
                    assert history["observations"][-1]["change"] == "decreased"
                    assert after["assessment"]["delivered_gbp"] == "58.10"
                    assert after["assessment"]["reasons"] == ["target_crossing"]
                    assert events["total"] == len(harness.deliveries) == 1
                    harness.clock.advance(hours=0.25)
                    await capture(harness, client, fresh)
                    assert (await get(client, "/api/events"))["total"] == 1
                    assert len(harness.deliveries) == 1
                assert harness.blocked_edges == []


async def adapter_isolation(case, output):
    from .source_evidence_workflows import admission, browse_fixture, retailer_fixture
    from .workflows import get

    source, fault = case.split("-", 1)
    fixture = retailer_fixture if source == "shopify" else browse_fixture
    with MonitoringHarness() as harness, fixture(harness):
        from pricerecon.connectors import ebay, shopify
        from pricerecon.core.collection_policy import operating_policy
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryRequest

        adapter = shopify if source == "shopify" else ebay
        original_factory = adapter.collection_http_client

        def client_factory(**kwargs):
            client = original_factory(**kwargs)
            original_handler = client._transport.handler

            def handler(request):
                response = original_handler(request)
                if fault == "control":
                    return response
                if source == "shopify" and request.url.path.endswith("/products.json"):
                    payload = response.json()
                    variant = {"id": 203, "price": "60.00", "currency": "GBP"}
                    if fault == "numeric":
                        variant["price"] = "1e101"
                    elif fault == "text":
                        payload["products"][0]["options"].append({"name": "Dial", "position": 3})
                        variant["option3"] = "x" * 501
                    elif fault == "report":
                        variant["id"] = "x" * 501
                    payload["products"][0]["variants"].append(variant)
                    return httpx.Response(200, json=payload)
                if source == "ebay" and "item_summary" in request.url.path:
                    payload = response.json()
                    item = {
                        "itemId": "bad",
                        "title": "Synthetic rejected sibling",
                        "itemWebUrl": "https://synthetic.invalid/bad",
                        "price": {
                            "value": "1e101" if fault == "numeric" else "60.00",
                            "currency": "GBP",
                        },
                    }
                    if fault == "report":
                        item["itemId"] = "x" * 501
                    payload["itemSummaries"].append(item)
                    return httpx.Response(200, json=payload)
                return response

            client._transport = httpx.MockTransport(handler)
            return client

        policy = type(harness.test_policy).model_validate(
            {
                **harness.test_policy.model_dump(),
                "provider_request_caps": {source: {"limit": 20, "tracking_reserve": 0}},
            }
        )
        config = {
            "evidence_use": {"permission_reference": "original-fixture", "retention": "synthetic"}
        }
        config.update(
            {"base_url": "https://www.sanmartin.watch"}
            if source == "shopify"
            else {"app_id": "synthetic", "cert_id": "synthetic"}
        )
        with (
            patch.object(adapter, "collection_http_client", client_factory),
            operating_policy(policy),
        ):
            async with harness.session() as (client, _):
                await execute_discovery(
                    DiscoveryRequest(
                        query="watch",
                        sources=[
                            {
                                "connector": source,
                                "config": config,
                            }
                        ],
                    ),
                    admission=admission(),
                )
                feed = await get(client, "/api/discovery/watches")
                output.write_text(json.dumps(feed, indent=2) + "\n")
                expected = {"201", "202"} if source == "shopify" else {"parent|0", "missing"}
                assert {c["source_listing_id"] for c in feed["candidates"]} == expected
                outcome = feed["captures"][0]["outcomes"][0]
                assert outcome["state"] == "partial"
                assert outcome["listing_count"] == 2
                capture = outcome["source_evidence"]
                assert capture["pages_captured"] == capture["page_limit"] == 1
                assert capture["item_limit"] == (250 if source == "shopify" else 50)
                if fault != "control":
                    assert (
                        "invalid_variant:0:2" if source == "shopify" else "invalid_item:2"
                    ) in capture["issues"]
                assert len(harness.searches) == 2
                assert all(
                    c["public_delivered_total"]["amount"] is None for c in feed["candidates"]
                )
                assert harness.deliveries == harness.blocked_edges == []


async def credential_pointer(case, output):
    from .cost_workflows import cost_report
    from .source_evidence_workflows import admission
    from .workflows import get, listing

    secret = "SYNTHETIC-CREDENTIAL-DO-NOT-KEEP"
    queries = {
        "client-secret": f"ClIeNt%5FSeCrEt={secret}",
        "aws": f"X-Amz-Credential={secret}&X-Amz-Signature={secret}",
        "aws-token": f"X-Amz-Security-Token={secret}",
        "google": f"X-Goog-Credential={secret}&X-Goog-Signature={secret}",
        "oauth": f"oauth_token={secret}",
        "aws-key": f"AWSAccessKeyId={secret}",
        "access-token": f"access_token={secret}",
        "sku": "variant=sku-123&sku=blue&quantity=1",
    }
    url = f"https://synthetic.invalid/watch?{queries[case]}#details"
    with MonitoringHarness() as harness:
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryRequest

        lead = listing(harness, "cex", "pointer", "Synthetic watch", "48.00")
        lead.url = url
        harness.outcomes["cex"] = [lead]
        report = cost_report(harness, "pointer")
        for claim in report.claims:
            claim.pointer = url
        harness.reports["cex"] = [report]
        async with harness.session() as (client, _):
            await execute_discovery(
                DiscoveryRequest(query="watch", sources=[{"connector": "cex"}]),
                admission=admission(),
            )
            # Repeat API readback: sanitization must survive persisted projections.
            for _ in range(2):
                feed = await get(client, "/api/discovery/watches")
                candidate = feed["candidates"][0]
                output.write_text(json.dumps(feed, indent=2) + "\n")
                pointers = [e["pointer"] for e in candidate["evidence"]]
                pointers += [e["pointer"] for e in candidate["offers"][0]["evidence"]]
                if case == "sku":
                    assert candidate["url"] == url.split("#")[0]
                    assert all(p == url.split("#")[0] for p in pointers)
                    assert candidate["public_delivered_total"]["amount"] == "50.10"
                else:
                    assert candidate["url"] is None
                    assert all(p is None for p in pointers)
                    assert secret not in json.dumps(feed)
                    assert candidate["public_delivered_total"]["amount"] is None
            assert harness.deliveries == harness.blocked_edges == []


if __name__ == "__main__":
    asyncio.run(globals()[sys.argv[1]](sys.argv[2], Path(sys.argv[3]).resolve()))
