"""One connected five-case story at the accepted API/execution seam.

All merchant assertions, dates and prices are invented. CEX/Scan are controlled
transport identities, not claims that these retailers sell this watch cohort.
Application imports occur only under MonitoringHarness in a fresh process.
"""

import asyncio
import json
import shutil
import sys
from pathlib import Path
from unittest.mock import patch

from .assessment_workflows import coupon_report, policy
from .correction_workflows import edit, url
from .harness import MonitoringHarness
from .history_workflows import history, priced_report
from .tracking_workflows import policy as target_policy
from .tracking_workflows import track
from .workflows import LEGACY, get, listing

CASES = {
    "militado": "Militado ML05/ML05B",
    "addies": "Addiesdive AD2066 mint",
    "san": "San Martin SN0144",
    "merkur": "Merkur Lightning salmon",
    "casio": "Casio MTP-B145D-2A2VEF",
}


def admission():
    from pricerecon.models.discovery import DiscoveryAdmission

    return DiscoveryAdmission(
        mode="offline_verification",
        policy_reference="ticket12-connected-v1",
        permission_reference="original-synthetic-test-data",
        activation_reference="temporary-audit-guarded-only",
    )


def named_report(harness, key, price="68"):
    report = priced_report(harness, price, key)
    dimensions = {
        "san": {"maker": "San Martin", "reference": "SN0144", "case_width_mm": "39"},
        "casio": {
            "maker": "Casio",
            "reference": "MTP-B145D-2A2VEF",
            "case_width_mm": "35",
            "dial": "blue",
        },
    }.get(key, {})
    for claim in report.claims:
        if claim.subject in {"configuration", "selection"} and claim.field in dimensions:
            claim.value = dimensions[claim.field]
    return report


async def capture(harness, client, reports, *, leads=False, sources=("cex",), comparison=None):
    from pricerecon.core.discovery import execute_discovery
    from pricerecon.models.discovery import DiscoveryRequest

    for source in sources:
        harness.reports[source] = reports
        harness.outcomes[source] = [
            listing(harness, source, r.source_listing_id, CASES[r.source_listing_id], "1")
            for r in reports
        ]
        if leads:
            harness.outcomes[source] += [
                listing(harness, source, key, CASES[key], "1") for key in ("militado", "merkur")
            ]
    result = await execute_discovery(
        DiscoveryRequest(
            query="compact colourful wristwatch", sources=[{"connector": s} for s in sources]
        ),
        admission=admission(),
        comparison_policy=comparison or policy(harness),
        tracking_policy=target_policy(),
    )
    return result, await get(client, "/api/discovery/watches")


def candidates(feed):
    return {c["source_listing_id"]: c for c in feed["candidates"] if c["source"] == "cex"}


def write_receipt(harness, receipt):
    receipt["guard"] = {
        "blocked_edges": harness.blocked_edges,
        "captured_deliveries": harness.deliveries,
    }
    assert harness.blocked_edges == []
    (harness.root / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


async def seed(harness, client):
    """Shared actual application seed used by both proof and buyer fixture."""
    from pricerecon.models.costs import ConditionalBenefit

    addies = named_report(harness, "addies")
    cashback = addies.cost_scenarios[0].model_copy(deep=True)
    cashback.key, cashback.kind = "cashback", "cashback"
    cashback.assumptions = ["Synthetic cashback eligibility and later payment are unproven"]
    cashback.benefits = [
        ConditionalBenefit(
            kind="cashback",
            amount="10",
            currency="GBP",
            state="conditional",
            reason="Excluded from payable",
            evidence=cashback.context_evidence,
        )
    ]
    addies.cost_scenarios.append(cashback)
    san = named_report(harness, "san")
    next(c for c in san.claims if c.subject == "selection" and c.field == "dial").value = (
        "Space Gray"
    )
    casio = named_report(harness, "casio", "48")
    casio.cost_scenarios[0].components[1].state = "unknown"
    casio.cost_scenarios[0].components[1].amount = None
    casio.cost_scenarios[0].components[1].currency = None
    _, feed = await capture(harness, client, [addies, san, casio], leads=True)
    return feed


async def cost_edges(harness, client):
    """Same named San Martin/Casio candidates, exact scenario changes retained."""
    from pricerecon.models.costs import FxQuote

    san = named_report(harness, "san", "68")
    shipping = san.cost_scenarios[0].components[1]
    shipping.state, shipping.amount, shipping.currency = "unknown", None, None
    casio = named_report(harness, "casio", "48")
    casio.cost_scenarios[0].components[1].currency = "USD"
    harness.clock.advance(hours=0.01)
    _, missing = await capture(harness, client, [san, casio])
    for key in ("san", "casio"):
        assert candidates(missing)[key]["public_delivered_total"]["amount"] is None
    san = named_report(harness, "san", "68")
    shipping = san.cost_scenarios[0].components[1]
    shipping.state = "conditional"
    shipping.assumptions = ["Synthetic regional shipping quote requires confirmation"]
    casio = named_report(harness, "casio", "48")
    scenario = casio.cost_scenarios[0]
    scenario.components[1].currency = "USD"
    scenario.fx_quotes = [
        FxQuote(
            purpose="buyer_payment",
            from_currency="USD",
            to_currency="GBP",
            rate="0.8",
            direction="target_per_source",
            converter="synthetic-provider",
            spread_included=True,
            quantum="0.01",
            rounding="ROUND_HALF_UP",
            state="observed",
            evidence=scenario.context_evidence,
        )
    ]
    harness.clock.advance(hours=0.01)
    _, resolved = await capture(harness, client, [san, casio])
    by = candidates(resolved)
    assert by["san"]["offers"][0]["cost_scenarios"][0]["state"] == "conditional"
    assert by["casio"]["public_delivered_total"]["amount"] == "49.68"
    return {"missing": missing, "conditional_and_fx": resolved}


async def connected(storage):
    from datetime import timedelta

    with MonitoringHarness(storage_root=storage) as harness:
        from pricerecon.core import notifications
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryRequest
        from pricerecon.models.qualification import EvidenceSearchReport

        harness.test_policy.caps["requests"] = harness.test_policy.caps["requests"].model_copy(
            update={"limit": 12}
        )
        harness.test_policy.provider_request_caps["cex"] = (
            harness.test_policy.provider_request_caps["cex"].model_copy(update={"limit": 12})
        )
        harness.seed_legacy([(7, LEGACY), (8, {**LEGACY, "name": "Paused", "enabled": False})])
        receipt = {
            "schema_version": 1,
            "fixture_version": "ticket12-connected-v1",
            "provenance": "original synthetic assertions; no real market evidence or retained live history",
            "gates": {},
            "checkpoints": {},
        }
        async with harness.session() as (client, scheduler):
            before = await get(client, "/api/watches")
            assert [j["watch_id"] for j in scheduler.list_watches()] == [7]
            feed = await seed(harness, client)
            by = candidates(feed)
            assert set(by) == set(CASES)
            assert await get(client, "/api/watches") == before
            assert all(c["origin"] == "category_discovery" for c in by.values())
            for key in ("militado", "merkur"):
                assert by[key]["configuration"]["state"] == "unresolved"
                assert by[key]["public_delivered_total"]["amount"] is None
                assert not by[key]["alert_eligible"]
            assert by["san"]["bindings"][0]["resolution"]["state"] != "supported"
            assert by["casio"]["public_delivered_total"]["amount"] is None
            assert by["casio"]["offers"][0]["cost_scenarios"][0]["known_subtotal"] == {"GBP": "48"}
            assert by["addies"]["public_delivered_total"]["amount"] == "70.10"
            receipt["checkpoints"]["five_case_seed"] = feed
            prefs = await client.put(
                "/api/discovery/watches/preferences",
                json={
                    "expected_revision": 0,
                    "values": {
                        "compact_max_width_mm": "38",
                        "colourful_dials": ["mint", "salmon"],
                        "budget_gbp": "150",
                    },
                },
            )
            assert prefs.status_code == 200, prefs.text
            by = candidates(await get(client, "/api/discovery/watches"))
            assert all(f["state"] == "unknown" for f in by["militado"]["preference_fit"])
            receipt["preferences"] = prefs.json()
            receipt["checkpoints"]["cost_edges"] = await cost_edges(harness, client)
            by = candidates(await get(client, "/api/discovery/watches"))
            saved = await track(client, by["addies"], notifications={"channels": ["webhook"]})
            independent = await track(client, by["casio"], target="40")
            receipt["target_ids"] = [saved["id"], independent["id"]]
            with patch.object(
                notifications,
                "get_global_notification_config",
                lambda: {"webhook_url": "https://synthetic.invalid/captured"},
            ):
                supplied = policy(harness).model_copy(
                    update={"window_end": harness.clock.now + timedelta(hours=12)}
                )
                for item, count in (("68", 0), ("78", 0), ("56", 1), ("56", 1), ("54", 2)):
                    harness.clock.advance(hours=0.01)
                    _, feed = await capture(
                        harness,
                        client,
                        [named_report(harness, "addies", item)],
                        comparison=supplied,
                    )
                    assert len(harness.deliveries) == count, harness.deliveries
                addies = candidates(feed)["addies"]
                retained = await history(client, addies)
                assert [o["change"] for o in retained["observations"]] == [
                    "initial",
                    "unchanged",
                    "increased",
                    "decreased",
                    "unchanged",
                    "decreased",
                ]
                assert all(not o["market_history_eligible"] for o in retained["observations"])
                assert retained["observations"][0]["costs"][0]["total"]["amount"] == "70.10"
                receipt["checkpoints"]["history_and_crossings"] = retained
                # The real persisted application also sees cache, failure and cap gaps.
                request = DiscoveryRequest(
                    query="compact colourful wristwatch", sources=[{"connector": "cex"}]
                )
                harness.report_overrides["cex"] = EvidenceSearchReport(
                    listings=harness.outcomes["cex"],
                    evidence=harness.reports["cex"],
                    acquisition_state="cache_reuse",
                    acquisition_reason="Synthetic cached fallback",
                    reused_capture_id=harness.reports["cex"][0].claims[0].capture_id,
                )
                harness.clock.advance(hours=0.01)
                await execute_discovery(request, admission=admission())
                del harness.report_overrides["cex"]
                harness.outcomes["cex"] = RuntimeError("Synthetic source outage")
                harness.clock.advance(hours=0.01)
                await execute_discovery(request, admission=admission())
                # Resume under original retained policy: no duplicate recovery send.
                harness.clock.advance(hours=0.1)
                _, feed = await capture(
                    harness, client, [named_report(harness, "addies", "54")], comparison=supplied
                )
                assert len(harness.deliveries) == 2
                # A distinct verified public receipt uses the same cost/comparison owner.
                harness.clock.advance(hours=0.01)
                addies = candidates(feed)["addies"]
                report = coupon_report(harness, addies["configuration"]["revision"] + 1, "addies")
                report.coupons[0].application.expected_coupon_revision = 1
                report.coupons[0].application.receipt.observation.expected_coupon_revision = 1
                _, feed = await capture(
                    harness,
                    client,
                    [report],
                    comparison=policy(
                        harness, allowed_scenario_kinds=["public_no_coupon", "public_coupon"]
                    ),
                )
                addies = candidates(feed)["addies"]
                assert addies["public_delivered_total"]["amount"] == "50.10"
                assert (
                    addies["offers"][0]["coupons"][0]["resulting_cost"]["total"]["amount"]
                    == "45.10"
                )
                assert any(
                    not a["historical"] and a["current_best"]["amount"] == "45.10"
                    for a in addies["price_assessments"]
                ), addies["price_assessments"]
                assert addies["usual_price"]["state"] == "unavailable" and addies["savings"] is None
                assert len(harness.deliveries) == 3
                assert harness.deliveries[-1][2]["listing"]["delivered_gbp"] == "50.10"
                receipt["checkpoints"]["coupon_separate_from_base"] = feed
                # Exhaust the one durable grant; it cannot be replaced by a new label.
                for _ in range(13):
                    harness.clock.advance(hours=0.01)
                    capped = await execute_discovery(request, admission=admission())
                    if capped.outcomes[0].state == "capped":
                        break
                assert capped.outcomes[0].state == "capped"
                assert capped.outcomes[0].reason == "resource_exhausted:requests"
                collection = await get(client, "/api/discovery/collection")
                assert (
                    next(u for u in collection["usage"] if u["resource"] == "requests")["used"]
                    == 12
                )
                receipt["checkpoints"]["exhausted_collection"] = collection
                gaps = await history(client, addies)
                assert {"cache_reuse", "failed", "capped"} <= {a["state"] for a in gaps["attempts"]}
                receipt["checkpoints"]["gaps"] = gaps
                addies = candidates(await get(client, "/api/discovery/watches"))["addies"]
                original = await history(client, addies)
                response = await client.post(url(addies), json=edit(addies))
                assert response.status_code == 201, response.text
                changed = candidates(await get(client, "/api/discovery/watches"))["addies"]
                assert changed["public_delivered_total"]["amount"] is None
                assert changed["offers"][0]["coupons"][0]["state"] == "invalidated"
                intent = await get(client, f"/api/discovery/tracking/{saved['id']}")
                assert intent["intended_values"]["dial"] == "salmon"
                assert (
                    intent["target_gbp"] == "60.00" and intent["assessment"]["state"] == "withheld"
                )
                other = await get(client, f"/api/discovery/tracking/{independent['id']}")
                assert other["intended_values"] == independent["intended_values"]
                assert other["configuration_id"] == independent["configuration_id"]
                assert other["target_gbp"] == "40"
                after = await history(client, addies)
                assert (
                    after["observations"][0]["configuration"]
                    == original["observations"][0]["configuration"]
                )
                receipt["checkpoints"]["corrected"] = changed
                receipt["events"] = await get(client, "/api/events")
            assert await get(client, "/api/watches") == before
            receipt["legacy"] = before
            receipt["policies"] = {
                "operating": harness.test_policy.model_dump(mode="json"),
                "comparison": supplied.model_dump(mode="json"),
                "target": target_policy().model_dump(mode="json"),
            }
            receipt["gates"] = dict.fromkeys(
                [
                    "five_cases",
                    "independent_discovery",
                    "preferences_unknowns",
                    "variation_abstention",
                    "no_coupon",
                    "synthetic_coupon_receipt",
                    "history_gaps",
                    "crossing_dedup",
                    "correction_independent_target",
                    "legacy_configuration",
                ],
                "passed",
            )
            receipt["gates"].update(
                dict.fromkeys(
                    [
                        "buyer_feedback",
                        "live_coupon",
                        "real_history",
                        "live_source_rights",
                        "live_operating_policy",
                        "activation",
                    ],
                    "unproven",
                )
            )
            receipt["resume_at"] = harness.clock.now.isoformat()
            write_receipt(harness, receipt)


async def resume(storage):
    from datetime import datetime

    receipt = json.loads((storage / "receipt.json").read_text())
    with MonitoringHarness(storage_root=storage) as harness:
        harness.clock.now = datetime.fromisoformat(receipt["resume_at"])
        harness.test_policy.caps["requests"] = harness.test_policy.caps["requests"].model_copy(
            update={"limit": 12}
        )
        harness.test_policy.provider_request_caps["cex"] = (
            harness.test_policy.provider_request_caps["cex"].model_copy(update={"limit": 12})
        )
        async with harness.session() as (client, scheduler):
            assert await get(client, "/api/watches") == receipt["legacy"]
            assert [j["watch_id"] for j in scheduler.list_watches()] == [7]
            assert await get(client, "/api/discovery/watches/preferences") == receipt["preferences"]
            events = await get(client, "/api/events")
            assert events == receipt["events"]
            state = await get(client, f"/api/discovery/tracking/{receipt['target_ids'][0]}")
            assert state["assessment"]["state"] == "withheld"
            harness.clock.advance(hours=0.01)
            await capture(harness, client, [named_report(harness, "addies", "54")])
            assert await get(client, "/api/events") == events
            assert harness.deliveries == harness.searches == []
            collection = await get(client, "/api/discovery/collection")
            assert next(u for u in collection["usage"] if u["resource"] == "requests")["used"] == 12
            receipt["gates"]["fresh_process_withholding"] = "passed"
            receipt["restart_guard"] = {
                "blocked_edges": harness.blocked_edges,
                "deliveries": harness.deliveries,
            }
            (storage / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


async def recovery(storage):
    """Closed temporary SQLite copies only; never a production rollback recipe."""
    with MonitoringHarness(storage_root=storage) as harness:
        harness.seed_legacy([(7, LEGACY), (8, {**LEGACY, "name": "Paused", "enabled": False})])
        backup = storage / "pre-migration.sqlite-copy"
        shutil.copy2(harness.database, backup)
        async with harness.session() as (client, scheduler):
            original = await get(client, "/api/watches")
            await seed(harness, client)
            assert [j["watch_id"] for j in scheduler.list_watches()] == [7]
            assert (await get(client, "/api/discovery/watches"))["candidates"]
        assert not Path(str(harness.database) + "-wal").exists()
        migrated = storage / "post-migration.sqlite-copy"
        shutil.copy2(harness.database, migrated)
        shutil.copy2(backup, harness.database)
        async with harness.session() as (client, _):
            assert await get(client, "/api/watches") == original
            assert not (await get(client, "/api/discovery/watches"))["candidates"]
        assert not Path(str(harness.database) + "-wal").exists()
        shutil.copy2(migrated, harness.database)
        async with harness.session() as (client, _):
            assert await get(client, "/api/watches") == original
            assert len((await get(client, "/api/discovery/watches"))["candidates"]) == 5
        (storage / "recovery.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "gate": "passed",
                    "temporary_storage": True,
                    "closed_database_copy": True,
                    "rollback": "pre-migration bytes restored then additive migration repeated",
                    "recovery": "post-migration snapshot restores five candidates and legacy intent",
                    "blocked_edges": harness.blocked_edges,
                    "limitations": "no live migration approval; no online/WAL backup qualification",
                },
                indent=2,
            )
            + "\n"
        )
        assert harness.blocked_edges == harness.deliveries == []


if __name__ == "__main__":
    asyncio.run(
        {"connected": connected, "resume": resume, "recovery": recovery}[sys.argv[1]](
            Path(sys.argv[2])
        )
    )
