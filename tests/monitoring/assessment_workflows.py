"""Original synthetic comparison data; dates are not market history."""

import asyncio
import sys

from .harness import MonitoringHarness
from .history_workflows import priced_report as history_report
from .tracking_workflows import policy as tracking_policy


def priced_report(harness, price="68.00", listing_id="assessment"):
    return history_report(harness, price, listing_id)


from .workflows import get, listing


def policy(harness, **changes):
    from datetime import timedelta

    from pricerecon.models.assessments import ComparisonPolicy

    return ComparisonPolicy(
        **{**tracking_policy().model_dump(), "version": "synthetic-comparison-v1", **changes},
        window_start=harness.clock.now - timedelta(days=1),
        window_end=harness.clock.now + timedelta(hours=1),
        sources=["cex", "scan"],
        evidence_policies={
            "identity": "watch-identity-v1",
            "selection": "watch-selection-v1",
            "offer": "offer-comparison-v1",
            "cost": "exact-scenario-cost-v1",
            "coupon": "exact-coupon-v1",
        },
    )


async def capture(harness, client, reports, supplied, target_policy=None, sources=("cex",)):
    from pricerecon.core.discovery import execute_discovery
    from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest

    for source in sources:
        harness.reports[source] = reports
        harness.outcomes[source] = [
            listing(harness, source, r.source_listing_id, "Synthetic exact watch", "1.00")
            for r in reports
        ]
    await execute_discovery(
        DiscoveryRequest(query="watch", sources=[{"connector": s} for s in sources]),
        admission=DiscoveryAdmission(
            mode="offline_verification",
            policy_reference="synthetic",
            permission_reference="original-test-data",
            activation_reference="isolated-harness",
        ),
        comparison_policy=supplied,
        tracking_policy=target_policy,
    )
    return await get(client, "/api/discovery/watches")


async def scoped():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            supplied = policy(harness)
            feed = await capture(harness, client, [priced_report(harness)], supplied)
            result = (await get(client, "/api/discovery/assessments"))["items"][-1]
            assert result["current_best"]["amount"] == "70.10", result
            assert result["observed_low"]["amount"] == "70.10"
            assert result["observed_low"]["observation_count"] == 1
            assert result["usual_price"]["state"] == "unavailable"
            assert result["personal_price"]["state"] == "unavailable"
            assert result["savings"] is None
            assert result["coverage"]["sources"] == ["cex", "scan"]
            assert "scan" in result["coverage"]["unchecked_sources"]
            assert feed["candidates"][0]["price_assessments"][0]["id"] == result["id"]
            harness.clock.advance(hours=0.1)
            await capture(harness, client, [priced_report(harness, "48.00")], supplied)
            latest = (await get(client, "/api/discovery/assessments"))["items"][-1]
            assert latest["current_best"]["amount"] == "50.10", latest
            assert latest["observed_low"]["amount"] == "50.10"
            assert latest["observed_low"]["observation_count"] == 2
            old = (await get(client, "/api/discovery/assessments"))["items"][0]
            assert old["historical"] and old["current_best"]["state"] == "historical"
            assert harness.deliveries == harness.blocked_edges == []


async def invalidation():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            supplied = policy(harness)
            feed = await capture(harness, client, [priced_report(harness)], supplied)
            harness.clock.advance(hours=3)
            stale = (await get(client, "/api/discovery/assessments"))["items"][-1]
            assert stale["current_best"]["state"] == "historical", stale
            assert stale["observed_low"]["state"] == "supported"
            assert "evidence_stale_or_expired" in stale["invalidation_reasons"]
            # Accepted correction HTTP workflow; no private database mutation.
            from .correction_workflows import edit, url

            candidate = feed["candidates"][0]
            response = await client.post(url(candidate), json=edit(candidate, value="blue"))
            assert response.status_code == 201, response.text
            withdrawn = (await get(client, "/api/discovery/assessments"))["items"][-1]
            assert withdrawn["current_best"]["state"] == "invalidated", withdrawn
            assert withdrawn["observed_low"]["state"] == "invalidated", withdrawn
            harness.clock.advance(hours=0.1)
            await capture(
                harness,
                client,
                [priced_report(harness, "48", "other")],
                supplied.model_copy(update={"max_evidence_age_seconds": 60}),
            )
            items = (await get(client, "/api/discovery/assessments"))["items"]
            assert all(a["historical"] for a in items[:-1]), items
            assert harness.blocked_edges == harness.deliveries == []


def coupon_report(harness, revision, listing_id="coupon-path"):
    from .coupon_workflows import reproduced_report

    report = reproduced_report(harness, listing_id, revision)
    # Establish direct temporal acquisition at the controlled external edge.
    for claim in report.claims:
        if claim.subject == "offer":
            claim.acquisition_capture_id = claim.capture_id
    for scenario in report.cost_scenarios:
        for claim in scenario.context_evidence + [
            e for p in scenario.components for e in p.evidence
        ]:
            claim.acquisition_capture_id = claim.capture_id
    import hashlib

    coupon = report.coupons[0]
    coupon.application.expected_coupon_revision = max(1, revision - 2)
    coupon.application.receipt.observation.expected_coupon_revision = max(1, revision - 2)
    payload = report.model_dump(mode="json")

    def stamp(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"capture_id", "acquisition_capture_id"} and isinstance(item, str):
                    value[key] = item + ":" + harness.clock.now.isoformat()
                else:
                    stamp(item)
        elif isinstance(value, list):
            for item in value:
                stamp(item)

    stamp(payload)
    from pricerecon.models.qualification import MerchantEvidenceReport

    report = MerchantEvidenceReport.model_validate(payload)
    application = report.coupons[0].application
    fingerprint = hashlib.sha256(report.coupons[0].terms.model_dump_json().encode()).hexdigest()
    application.terms_fingerprint = fingerprint
    application.receipt.observation.terms_fingerprint = fingerprint
    return report


async def coupon_crossing():
    from unittest.mock import patch

    from .tracking_workflows import track

    with MonitoringHarness() as harness:
        from pricerecon.core import notifications

        async with harness.session() as (client, _):
            supplied = policy(harness, allowed_scenario_kinds=["public_no_coupon", "public_coupon"])
            target_policy = tracking_policy().model_copy(
                update={"allowed_scenario_kinds": ["public_no_coupon", "public_coupon"]}
            )
            feed = await capture(
                harness, client, [priced_report(harness, "48", "coupon-path")], supplied
            )
            saved = await track(
                client, feed["candidates"][0], target="47", notifications={"channels": ["webhook"]}
            )
            with patch.object(
                notifications,
                "get_global_notification_config",
                lambda: {"webhook_url": "https://synthetic.invalid/captured"},
            ):
                harness.clock.advance(hours=0.01)
                await capture(
                    harness,
                    client,
                    [priced_report(harness, "48", "coupon-path")],
                    supplied,
                    target_policy,
                )
                harness.clock.advance(hours=0.01)
                feed = await capture(
                    harness, client, [coupon_report(harness, 3)], supplied, target_policy
                )
                candidate = feed["candidates"][0]
                coupon = candidate["offers"][0]["coupons"][0]
                assert coupon["state"] == "reproduced_at_observation", coupon
                result = (await get(client, "/api/discovery/assessments"))["items"][-1]
                assert result["current_best"]["amount"] == "45.10", result
                assert result["current_best"]["paths"][0]["scenario_kind"] == "public_coupon"
                assert result["observed_low"]["amount"] == "45.10"
                assert candidate["public_delivered_total"]["amount"] == "50.10"
                assert len(harness.deliveries) == 1, harness.deliveries
                assert harness.deliveries[0][2]["listing"]["delivered_gbp"] == "45.10"
                state = await get(client, f"/api/discovery/tracking/{saved['id']}")
                assert state["assessment"]["coupon_id"] == coupon["id"]
                harness.clock.advance(hours=0.01)
                await capture(harness, client, [coupon_report(harness, 4)], supplied, target_policy)
                assert len(harness.deliveries) == 1
                # A legacy policy still chooses the undiscounted base, preserving opt-out.
                harness.clock.advance(hours=0.01)
                await capture(
                    harness, client, [coupon_report(harness, 5)], policy(harness), tracking_policy()
                )
                state = await get(client, f"/api/discovery/tracking/{saved['id']}")
                assert state["assessment"]["delivered_gbp"] == "50.10"
                assert state["assessment"]["coupon_id"] is None
                assert len(harness.deliveries) == 1
            assert harness.blocked_edges == []


async def coupon_guards():
    from unittest.mock import patch

    from .tracking_workflows import track

    with MonitoringHarness() as harness:
        from pricerecon.core import exact_tracking, notifications

        async with harness.session() as (client, _):
            supplied = policy(harness, allowed_scenario_kinds=["public_no_coupon", "public_coupon"])
            target_policy = tracking_policy().model_copy(
                update={"allowed_scenario_kinds": ["public_no_coupon", "public_coupon"]}
            )
            feed = await capture(
                harness, client, [priced_report(harness, "48", "coupon-path")], supplied
            )
            saved = await track(
                client, feed["candidates"][0], target="47", notifications={"channels": ["webhook"]}
            )
            harness.clock.advance(hours=0.01)
            await capture(
                harness,
                client,
                [priced_report(harness, "48", "coupon-path")],
                supplied,
                target_policy,
            )

            async def interrupted(**kwargs):
                return None

            with patch.object(exact_tracking, "deliver_pending_targets", interrupted):
                harness.clock.advance(hours=0.01)
                await capture(harness, client, [coupon_report(harness, 3)], supplied, target_policy)
            pending = await get(client, f"/api/discovery/tracking/{saved['id']}/deliveries")
            assert pending["items"][0]["status"] == "pending", pending
            with patch.object(
                notifications,
                "get_global_notification_config",
                lambda: {"webhook_url": "https://synthetic.invalid/captured"},
            ):
                harness.clock.advance(hours=1)
                await exact_tracking.deliver_pending_targets(policy=target_policy)
                assert harness.deliveries == []
            state = await get(client, f"/api/discovery/tracking/{saved['id']}")
            assert state["assessment"]["state"] == "withheld", state
            assessments = (await get(client, "/api/discovery/assessments"))["items"]
            assert assessments[-1]["current_best"]["state"] == "historical"
            assert assessments[-1]["observed_low"]["amount"] == "45.10"
            assert harness.blocked_edges == []


async def siblings():
    from .correction_merger_probe import reports
    from .correction_scope_workflows import correct

    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            supplied = policy(harness)
            feed = await capture(harness, client, reports(harness), supplied)
            assert len(feed["candidates"]) == 1
            items = (await get(client, "/api/discovery/assessments"))["items"]
            assert len(items) == 2 and all(
                a["current_best"]["amount"] == "50.10" for a in items
            ), items
            candidate = feed["candidates"][0]
            _, response = await correct(client, candidate)
            assert response.status_code == 201, response.text
            items = (await get(client, "/api/discovery/assessments"))["items"]
            mint = next(a for a in items if '"dial": "mint"' in a["cohort"]["configuration"])
            blue = next(a for a in items if '"dial": "blue"' in a["cohort"]["configuration"])
            assert mint["current_best"]["state"] == mint["observed_low"]["state"] == "invalidated"
            assert (
                blue["current_best"]["state"] == blue["observed_low"]["state"] == "supported"
            ), blue
        async with harness.session() as (client, _):
            assert (await get(client, "/api/discovery/assessments"))["items"] == items
            harness.clock.advance(hours=0.1)
            fresh = await capture(harness, client, reports(harness, corrected=True), supplied)
            current = [
                a for a in fresh["candidates"][0]["price_assessments"] if not a["historical"]
            ]
            assert any(
                '"dial": "blue"' in a["cohort"]["configuration"]
                and a["current_best"]["amount"] == "50.10"
                for a in current
            ), current
            assert harness.blocked_edges == harness.deliveries == []


async def contradictions():
    with MonitoringHarness() as harness:
        from pricerecon.models.qualification import EvidenceSearchReport

        async with harness.session() as (client, _):
            report = priced_report(harness, "68")
            harness.report_overrides["scan"] = EvidenceSearchReport(
                listings=[listing(harness, "scan", "assessment", "Conflicting exact watch", "1")],
                evidence=[priced_report(harness, "48")],
            )
            await capture(harness, client, [report], policy(harness), sources=("cex", "scan"))
            result = (await get(client, "/api/discovery/assessments"))["items"][-1]
            assert result["current_best"]["state"] == "unavailable", result
            assert result["observed_low"]["state"] == "unavailable", result
            assert any("conflicting_route_totals" in e["reasons"] for e in result["exclusions"])
            assert harness.deliveries == harness.blocked_edges == []


async def restricted_coupons():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            supplied = policy(harness, allowed_scenario_kinds=["public_no_coupon", "public_coupon"])
            reports = []
            for category in (
                "personal",
                "payment",
                "cashback",
                "app",
                "advertised",
                "receipt-changed",
            ):
                report = coupon_report(harness, 1, category)
                coupon = report.coupons[0]
                if category in {"personal", "payment", "cashback"}:
                    coupon.category = category
                elif category == "app":
                    # Reproduction alone must not upgrade app-conditional eligibility.
                    import hashlib

                    coupon.terms.channel = "app"
                    coupon.eligibility.channel = "app"
                    coupon.application.receipt.observation.eligibility.channel = "app"
                    fingerprint = hashlib.sha256(
                        coupon.terms.model_dump_json().encode()
                    ).hexdigest()
                    coupon.application.terms_fingerprint = fingerprint
                    coupon.application.receipt.observation.terms_fingerprint = fingerprint
                elif category == "advertised":
                    coupon.application = None
                else:
                    coupon.application.receipt.observation.quoted_total = "1.00"
                reports.append(report)
            feed = await capture(harness, client, reports, supplied)
            latest = (await get(client, "/api/discovery/assessments"))["items"][-1]
            assert (
                latest["current_best"]["amount"] == latest["observed_low"]["amount"] == "50.10"
            ), latest
            assert all(
                p["scenario_kind"] == "public_no_coupon" for p in latest["current_best"]["paths"]
            )
            assert len(feed["candidates"]) == 6
            assert harness.deliveries == harness.blocked_edges == []


async def coupon_replaced():
    from unittest.mock import patch

    from .tracking_workflows import track

    with MonitoringHarness() as harness:
        from pricerecon.core import exact_tracking, notifications

        async with harness.session() as (client, _):
            supplied = policy(harness, allowed_scenario_kinds=["public_no_coupon", "public_coupon"])
            target_policy = tracking_policy().model_copy(
                update={"allowed_scenario_kinds": ["public_no_coupon", "public_coupon"]}
            )
            feed = await capture(
                harness, client, [priced_report(harness, "48", "coupon-path")], supplied
            )
            saved = await track(
                client, feed["candidates"][0], target="47", notifications={"channels": ["webhook"]}
            )
            harness.clock.advance(hours=0.01)
            await capture(
                harness,
                client,
                [priced_report(harness, "48", "coupon-path")],
                supplied,
                target_policy,
            )

            async def interrupted(**kwargs):
                return None

            with patch.object(exact_tracking, "deliver_pending_targets", interrupted):
                harness.clock.advance(hours=0.01)
                await capture(harness, client, [coupon_report(harness, 3)], supplied, target_policy)
                # New terms without matching direct receipt are retained, never a new public payable.
                report = coupon_report(harness, 4)
                report.coupons[0].terms.literal = "Changed terms after reservation"
                harness.clock.advance(hours=0.01)
                await capture(harness, client, [report], supplied, target_policy)
            with patch.object(
                notifications,
                "get_global_notification_config",
                lambda: {"webhook_url": "https://synthetic.invalid/captured"},
            ):
                await exact_tracking.deliver_pending_targets(policy=target_policy)
            delivery = (await get(client, f"/api/discovery/tracking/{saved['id']}/deliveries"))[
                "items"
            ][0]
            assert delivery["status"] == "withheld", delivery
            assert harness.deliveries == harness.blocked_edges == []


async def cohorts():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            reports = [priced_report(harness, "68", "new")]
            for kind, field, value in (
                ("used", "condition", "used"),
                ("auction", "purchase_mode", "auction"),
                ("destination", "destination_region", "elsewhere"),
            ):
                report = priced_report(harness, "1", kind)
                for claim in report.claims:
                    if claim.subject == "offer" and claim.field == field:
                        claim.value = value
                cost = report.cost_scenarios[0]
                setattr(cost.context, field, value)
                for claim in cost.context_evidence + [
                    e for p in cost.components for e in p.evidence
                ]:
                    setattr(claim.context, field, value)
                reports.append(report)
            reports.append(history_report(harness, "1", "quantity", quantity=2))
            unknown = priced_report(harness, "1", "unknown")
            unknown.cost_scenarios[0].components = [
                p for p in unknown.cost_scenarios[0].components if p.kind != "carrier_fee"
            ]
            reports.append(unknown)
            conditional = priced_report(harness, "1", "conditional")
            shipping = next(
                p for p in conditional.cost_scenarios[0].components if p.kind == "shipping"
            )
            shipping.state, shipping.assumptions = "conditional", ["Unproven shipping assumption"]
            reports.append(conditional)
            await capture(harness, client, reports, policy(harness))
            items = (await get(client, "/api/discovery/assessments"))["items"]
            winners = [a for a in items if a["current_best"]["state"] == "supported"]
            assert len(winners) == 1 and winners[0]["current_best"]["amount"] == "70.10", items
            assert len(items) == 5, items
            assert all(
                a["current_best"]["state"] == "unavailable" for a in items if a not in winners
            )
            assert harness.deliveries == harness.blocked_edges == []


async def restart_before():
    import json
    from pathlib import Path
    from unittest.mock import patch

    from .tracking_workflows import track

    with MonitoringHarness(storage_root=Path(sys.argv[2])) as harness:
        from pricerecon.core import notifications

        async with harness.session() as (client, _):
            supplied = policy(harness, allowed_scenario_kinds=["public_no_coupon", "public_coupon"])
            target_policy = tracking_policy().model_copy(
                update={"allowed_scenario_kinds": ["public_no_coupon", "public_coupon"]}
            )
            feed = await capture(
                harness, client, [priced_report(harness, "48", "coupon-path")], supplied
            )
            saved = await track(
                client, feed["candidates"][0], target="47", notifications={"channels": ["webhook"]}
            )
            with patch.object(
                notifications,
                "get_global_notification_config",
                lambda: {"webhook_url": "https://synthetic.invalid/captured"},
            ):
                harness.clock.advance(hours=0.01)
                await capture(
                    harness,
                    client,
                    [priced_report(harness, "48", "coupon-path")],
                    supplied,
                    target_policy,
                )
                harness.clock.advance(hours=0.01)
                await capture(harness, client, [coupon_report(harness, 3)], supplied, target_policy)
            assert len(harness.deliveries) == 1
            Path(sys.argv[2], "expected.json").write_text(
                json.dumps(
                    {
                        "assessments": await get(client, "/api/discovery/assessments"),
                        "tracking_id": saved["id"],
                        "policy": supplied.model_dump(mode="json"),
                    }
                )
            )
            assert harness.blocked_edges == []


async def restart_after():
    import json
    from pathlib import Path
    from unittest.mock import patch

    with MonitoringHarness(storage_root=Path(sys.argv[2])) as harness:
        from pricerecon.core import notifications
        from pricerecon.models.assessments import ComparisonPolicy

        expected = json.loads(Path(sys.argv[2], "expected.json").read_text())
        harness.clock.advance(hours=0.02)
        async with harness.session() as (client, _):
            assert await get(client, "/api/discovery/assessments") == expected["assessments"]
            supplied = ComparisonPolicy.model_validate(expected["policy"])
            target_policy = tracking_policy().model_copy(
                update={"allowed_scenario_kinds": ["public_no_coupon", "public_coupon"]}
            )
            with patch.object(
                notifications,
                "get_global_notification_config",
                lambda: {"webhook_url": "https://synthetic.invalid/captured"},
            ):
                harness.clock.advance(hours=0.01)
                await capture(harness, client, [coupon_report(harness, 4)], supplied, target_policy)
            assert harness.deliveries == []
            deliveries = await get(
                client, f"/api/discovery/tracking/{expected['tracking_id']}/deliveries"
            )
            assert (
                len(deliveries["items"]) == 1 and deliveries["items"][0]["status"] == "sent"
            ), deliveries
            assert harness.blocked_edges == []


async def duplicates_and_gaps():
    with MonitoringHarness() as harness:
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest

        async with harness.session() as (client, _):
            supplied = policy(harness)
            report = priced_report(harness)
            await capture(harness, client, [report], supplied)
            harness.clock.advance(hours=0.01)
            await capture(harness, client, [report], supplied)
            result = (await get(client, "/api/discovery/assessments"))["items"][-1]
            assert result["observed_low"]["observation_count"] == 1
            assert result["current_best"]["state"] == "unavailable"
            harness.outcomes["cex"] = RuntimeError("Synthetic acquisition failure")
            harness.clock.advance(hours=0.01)
            await execute_discovery(
                DiscoveryRequest(query="watch", sources=[{"connector": "cex"}]),
                admission=DiscoveryAdmission(
                    mode="offline_verification",
                    policy_reference="synthetic",
                    permission_reference="original-test-data",
                    activation_reference="isolated-harness",
                ),
                comparison_policy=supplied,
            )
            result = (await get(client, "/api/discovery/assessments"))["items"][-1]
            assert result["observed_low"]["amount"] == "70.10"
            assert result["current_best"]["state"] == "unavailable"
            assert any(a["state"] == "failed" for a in result["coverage"]["attempts"])
            assert any(g["state"] == "failed" for g in result["coverage"]["gaps"])
            assert harness.deliveries == harness.blocked_edges == []


if __name__ == "__main__":
    asyncio.run(globals()[sys.argv[1]]())
