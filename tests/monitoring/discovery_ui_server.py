"""Repeatable local UI fixture. Run only with the guarded temporary application.

    PYTHONPATH="$PWD/src:$PWD" <existing-venv>/bin/python -m tests.monitoring.discovery_ui_server --port 8877

Build frontend first. No merchant/browser backend, credentials or production DB.
The server accepts inbound loopback UI traffic; all acquisition/sending edges stay
guarded by MonitoringHarness. Ctrl-C prints the guard/sending receipt.
"""

import argparse
import asyncio
import json

import uvicorn
from fastapi import APIRouter

from .harness import MonitoringHarness
from .workflows import LEGACY, listing


async def main(port, qualification=False, costs=False, tracking=False, history=False, coupons=False, corrections=False, assessments=False):
    with MonitoringHarness() as harness:
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest

        assert harness.application.frontend_dist.joinpath("index.html").is_file(), (
            "Build frontend first"
        )
        harness.seed_legacy(
            [(7, LEGACY), (8, {**LEGACY, "name": "Paused saved search", "enabled": False})]
        )
        names = [
            "Militado ML05/ML05B",
            "Addiesdive AD2066 mint",
            "San Martin SN0144",
            "Merkur Lightning salmon",
            "Casio MTP-B145D-2A2VEF",
        ]
        harness.outcomes["cex"] = [
            listing(harness, "cex", f"fixture-{i}", name, "48.00") for i, name in enumerate(names)
        ]
        if qualification or costs:
            from .qualification_workflows import synthetic_report

            harness.reports["cex"] = [
                synthetic_report(harness, "fixture-1"),
                synthetic_report(
                    harness, "fixture-2", reference="SN0144", maker="San Martin", width="39"
                ),
                synthetic_report(
                    harness,
                    "fixture-4",
                    reference="MTP-B145D-2A2VEF",
                    maker="Casio",
                    width="35",
                    condition="used",
                    mode="auction",
                ),
            ]
            # A selected dial conflict must appear as a rejected binding.
            next(
                c
                for c in harness.reports["cex"][1].claims
                if c.subject == "selection" and c.field == "dial"
            ).value = "Space Gray"
        if costs:
            from pricerecon.models.costs import ConditionalBenefit

            from .cost_workflows import cost_report

            verified = cost_report(harness, "fixture-1")
            personal = verified.cost_scenarios[0].model_copy(deep=True)
            personal.key, personal.kind = "cashback", "cashback"
            personal.assumptions = ["Synthetic cashback eligibility and payment remain conditional"]
            personal.benefits = [
                ConditionalBenefit(
                    kind="cashback",
                    amount="10.00",
                    currency="GBP",
                    state="conditional",
                    reason="Synthetic estimate excluded from payable",
                    evidence=personal.context_evidence,
                )
            ]
            verified.cost_scenarios.append(personal)
            conditional = cost_report(harness, "fixture-2")
            conditional.cost_scenarios[0].components[1].state = "conditional"
            conditional.cost_scenarios[0].components[1].assumptions = [
                "Synthetic shipping quote assumes the stated region"
            ]
            unknown = cost_report(harness, "fixture-4")
            unknown.cost_scenarios[0].components[1].state = "unknown"
            unknown.cost_scenarios[0].components[1].amount = None
            unknown.cost_scenarios[0].components[1].currency = None
            harness.reports["cex"] = [verified, conditional, unknown]
            if tracking:
                from .tracking_workflows import priced_report

                harness.reports["cex"][0] = priced_report(harness, listing_id="fixture-1")
        if coupons or corrections:
            from .coupon_workflows import advertised_report, reproduced_report

            harness.reports["cex"] = [
                reproduced_report(harness, "fixture-1"),
                advertised_report(harness, "fixture-2"),
                cost_report(harness, "fixture-4"),
            ]
        async with harness.session() as (client, scheduler):
            fixture_router = APIRouter()
            fixture_id = None
            if tracking:
                from .tracking_ui_fixture import configure_tracking_fixture

                harness.ui_client = client
                fixture_id = configure_tracking_fixture(harness, fixture_router)

            @fixture_router.get("/api/offline-verification")
            async def fixture_identity():
                return {
                    "fixture": (
                        "ticket08-assessment-ui" if assessments else
                        "ticket07-correction-ui" if corrections else
                        "ticket05-tracking-ui" if tracking else
                        "ticket09-coupon-ui" if coupons else
                        "ticket06-history-ui" if history else "ticket04-cost-ui"
                        if costs
                        else (
                            "ticket03-qualification-ui"
                            if qualification
                            else "ticket02-discovery-ui"
                        )
                    ),
                    "temporary_storage": True,
                    "automatic_checks": False,
                    "blocked_edges": harness.blocked_edges,
                    "notifications_sent": len(harness.deliveries),
                    "fixture_id": fixture_id,
                }

            # Test-server-only marker precedes the SPA fallback. The driver
            # verifies it before any edits, so a reused port fails closed.
            harness.application.app.router.routes[0:0] = fixture_router.routes
            await execute_discovery(
                DiscoveryRequest(
                    query="wristwatch", sources=[{"connector": "cex"}, {"connector": "scan"}]
                ),
                admission=DiscoveryAdmission(
                    mode="offline_verification",
                    policy_reference="fixture-policy-v1",
                    permission_reference="original-test-data",
                    activation_reference="offline-ui-harness",
                ),
            )
            if history:
                from .history_ui_fixture import populate_history

                await populate_history(harness)
            harness.outcomes["scan"] = RuntimeError("offline simulated acquisition failure")
            harness.clock.advance(hours=0.1 if assessments else 1)
            await execute_discovery(
                DiscoveryRequest(query="wristwatch", sources=[{"connector": "scan"}]),
                admission=DiscoveryAdmission(
                    mode="offline_verification",
                    policy_reference="fixture-policy-v1",
                    permission_reference="original-test-data",
                    activation_reference="offline-ui-harness",
                ),
            )
            if assessments:
                from .assessment_workflows import capture as assessment_capture, coupon_report, policy, priced_report

                supplied = policy(harness, allowed_scenario_kinds=["public_no_coupon", "public_coupon"])
                feed = await assessment_capture(harness, client, [priced_report(harness, "68", "fixture-1")], supplied)
                harness.clock.advance(hours=0.01)
                report = coupon_report(harness, 3, "fixture-1")
                candidate = next(c for c in feed["candidates"] if c["source_listing_id"] == "fixture-1")
                revision = candidate["configurations"][0]["revision"] + 1
                report.coupons[0].application.expected_configuration_revision = revision
                report.coupons[0].application.receipt.observation.expected_configuration_revision = revision
                await assessment_capture(harness, client, [report], supplied)
            print(
                f"OFFLINE_UI_READY http://127.0.0.1:{port}/discover; fictional connector leads; temporary SQLite; paused scheduler",
                flush=True,
            )
            try:
                await uvicorn.Server(
                    uvicorn.Config(
                        harness.application.app,
                        host="127.0.0.1",
                        port=port,
                        loop="asyncio",
                        lifespan="off",
                        access_log=False,
                    )
                ).serve()
            finally:
                assert harness.blocked_edges == []
                if not tracking:
                    assert harness.deliveries == []
                assert len(scheduler.list_watches()) == 1
                print(
                    json.dumps(
                        {
                            "blocked_edges": harness.blocked_edges,
                            "notifications_sent": len(harness.deliveries),
                            "searches": len(harness.searches),
                            "temporary_storage": True,
                        }
                    ),
                    flush=True,
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8877)
    parser.add_argument("--qualification", action="store_true")
    parser.add_argument("--costs", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--tracking", action="store_true")
    mode.add_argument("--coupons", action="store_true")
    mode.add_argument("--history", action="store_true")
    mode.add_argument("--corrections", action="store_true")
    mode.add_argument("--assessments", action="store_true")
    args = parser.parse_args()
    try:
        asyncio.run(main(args.port, qualification=args.qualification,
            costs=args.costs or args.tracking or args.history or args.coupons or args.corrections or args.assessments,
            tracking=args.tracking, history=args.history, coupons=args.coupons, corrections=args.corrections, assessments=args.assessments))
    except KeyboardInterrupt:
        print("OFFLINE_UI_STOPPED", flush=True)
