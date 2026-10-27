"""Guarded ticket07 merger probes; original synthetic evidence and captured sends."""

import asyncio
import json
import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from .correction_merger_probe import reports
from .correction_scope_workflows import configuration, correct, selected, with_dials
from .cost_workflows import read_capture
from .harness import MonitoringHarness
from .tracking_workflows import policy, track
from .workflows import get, listing


def guard(harness):
    return {
        "temporary_storage": True,
        "blocked_edges": harness.blocked_edges,
        "notifications_sent": len(harness.deliveries),
        "collection_state": "staged",
    }


async def independent_recorrection(output, *, reverse_journals=False, descendant_target=False):
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            initial = (await read_capture(harness, client, reports(harness)))["candidates"][0]
            saved = [
                await track(client, {**initial, "configurations": [configuration(initial, dial)]})
                for dial in ("mint", "blue")
            ]
            intended = "salmon" if descendant_target else "blue"
            if reverse_journals:
                second, response = await correct(client, initial, "blue", "red")
                assert response.status_code == 201, response.text
                first, response = await correct(client, initial, value=intended)
                assert response.status_code == 201, response.text
            else:
                first, response = await correct(client, initial, value=intended)
                assert response.status_code == 201, response.text
                second, response = await correct(client, initial, "blue", "red")
                assert response.status_code == 201, response.text
            harness.clock.advance(hours=0.1)
            current = (await read_capture(harness, client, with_dials(harness, intended, "red")))[
                "candidates"
            ][0]
            if descendant_target:
                saved.append(
                    await track(
                        client,
                        {**current, "configurations": [configuration(current, intended)]},
                    )
                )
            before = [await get(client, f"/api/discovery/tracking/{s['id']}") for s in saved]
            assert [t["intended_values"]["dial"] for t in before[:2]] == [intended, "red"]
            for endpoint in (first, second):
                assert (await get(client, endpoint))[
                    "requalification"
                ] == "supported_by_fresh_evidence"
            _, response = await correct(
                client,
                current,
                intended,
                "gold",
                root=configuration(initial, "mint")["id"],
                revision=1,
            )
            assert response.status_code == 201, response.text
            after = [await get(client, f"/api/discovery/tracking/{s['id']}") for s in saved]
            journals = [await get(client, endpoint) for endpoint in (first, second)]
        async with harness.session() as (client, _):
            restarted = [await get(client, f"/api/discovery/tracking/{s['id']}") for s in saved]
            unchanged = restarted[1]["intended_values"] == before[1]["intended_values"]
            for old, new in zip(before, restarted, strict=True):
                assert new["configuration_id"] == old["configuration_id"]
                assert new["target_gbp"] == old["target_gbp"] == "60.00"
            assert journals[1]["values"]["dial"] == "red"
            assert harness.deliveries == harness.blocked_edges == []
            output.write_text(
                json.dumps(
                    {
                        "fixture": "ticket07-independent-journal-recorrection",
                        "result": "passed" if unchanged else "failed",
                        "before": before,
                        "after": after,
                        "restarted": restarted,
                        "journals_after_recorrection": journals,
                        "guard": guard(harness),
                    },
                    indent=2,
                )
                + "\n"
            )
            assert (
                unchanged
            ), "Recorrecting mint->blue to gold rewrites independent blue->red target intent"
            assert restarted[0]["intended_values"]["dial"] == "gold"
            # A withheld assessment can reference an affected offer and gain an
            # honest withdrawal reason. The independent buyer intent and its
            # mutation/invalidation versions must nevertheless remain intact.
            for field in (
                "intended_values",
                "revision",
                "invalidation_revision",
                "invalidation_reason",
                "configuration_id",
                "target_gbp",
                "notifications",
                "created_at",
                "updated_at",
            ):
                assert (
                    after[1][field] == before[1][field] == restarted[1][field]
                ), f"Independent journal's target {field} changed during another journal's edit"
            if descendant_target:
                assert (
                    restarted[2]["intended_values"]["dial"] == "gold"
                ), "Target anchored to the corrected selection's descendant did not follow it"


async def sibling_control(output):
    with MonitoringHarness() as harness:
        from pricerecon.core import notifications
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest

        captures = []

        async def capture(client, inputs):
            harness.reports["cex"] = inputs
            harness.outcomes["cex"] = [
                listing(harness, "cex", r.source_listing_id, "Synthetic watch", "1.00")
                for r in inputs
            ]
            await execute_discovery(
                DiscoveryRequest(query="watch", sources=[{"connector": "cex"}]),
                admission=DiscoveryAdmission(
                    mode="offline_verification",
                    policy_reference="synthetic",
                    permission_reference="original-test-data",
                    activation_reference="isolated-harness",
                ),
                tracking_policy=policy(),
            )
            feed = await get(client, "/api/discovery/watches")
            captures.append(feed["captures"][0])
            return feed["candidates"][0]

        def priced(inputs, amount):
            for report in inputs:
                for claim in report.claims:
                    if claim.subject == "offer" and claim.field == "item_price":
                        claim.value = amount
                report.cost_scenarios[0].components[0].amount = Decimal(amount)
            return inputs

        async with harness.session() as (client, _):
            originals = priced(reports(harness), "68.00")
            initial = await capture(client, originals)
            saved = [
                await track(
                    client,
                    {**initial, "configurations": [configuration(initial, dial)]},
                    notifications={"channels": ["webhook"]},
                )
                for dial in ("mint", "blue")
            ]
            harness.clock.advance(hours=0.1)
            initial = await capture(client, priced(reports(harness), "68.00"))
            endpoint, response = await correct(client, initial)
            assert response.status_code == 201, response.text
            harness.clock.advance(hours=0.1)
            fresh = priced(reports(harness, corrected=True), "56.00")
            fresh[0].cost_scenarios[0].context_evidence[0].derived_from = [
                originals[0].cost_scenarios[0].context_evidence[0].capture_id
            ]
            with patch.object(
                notifications,
                "get_global_notification_config",
                lambda: {
                    "webhook_url": "https://synthetic.invalid/captured",
                },
            ):
                current = await capture(client, fresh)
            assert captures[-1]["publication_state"] == "withdrawn"
            binding, offer = selected(current, "a")
            assert binding["resolution"]["state"] != "supported"
            assert offer["cost_scenarios"][0]["withdrawn"] is True
            assert offer["cost_scenarios"][0]["total"] is None
            assert (await get(client, endpoint))["requalification"] == "required"
            assert len(harness.deliveries) == 1
            sent = harness.deliveries[0][2]["listing"]
            assert sent["tracking_id"] == saved[1]["id"]
            assert sent["configuration_id"] == configuration(current, "blue")["id"]
            assert sent["delivered_gbp"] == "58.10"
        async with harness.session() as (client, _):
            assert (await get(client, endpoint))["requalification"] == "required"
            intents = [await get(client, f"/api/discovery/tracking/{s['id']}") for s in saved]
            assert intents[0]["assessment"]["state"] == "withheld"
            assert len(harness.deliveries) == 1 and harness.blocked_edges == []
            output.write_text(
                json.dumps(
                    {
                        "fixture": "ticket07-withdrawn-capture-valid-sibling-crossing",
                        "result": "passed",
                        "candidate": current,
                        "capture": captures[-1],
                        "intents_after_restart": intents,
                        "captured_notifications": harness.deliveries,
                        "guard": guard(harness),
                    },
                    indent=2,
                )
                + "\n"
            )


if __name__ == "__main__":
    if "--sibling-control" in sys.argv[2:]:
        asyncio.run(sibling_control(Path(sys.argv[1]).resolve()))
    else:
        asyncio.run(
            independent_recorrection(
                Path(sys.argv[1]).resolve(),
                reverse_journals="--reverse-journals" in sys.argv[2:],
                descendant_target="--descendant-target" in sys.argv[2:],
            )
        )
