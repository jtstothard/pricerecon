"""Guarded ticket07 multi-configuration acceptance probe; original synthetic data."""

import asyncio
import json
import sys
from pathlib import Path

from .correction_workflows import edit
from .cost_workflows import read_capture
from .harness import MonitoringHarness
from .history_workflows import priced_report
from .workflows import get


def reports(harness, *, corrected=False):
    result = []
    for variation, dial in (("a", "salmon" if corrected else "mint"), ("b", "blue")):
        report = priced_report(harness, listing_id="multi-correction")
        report.variation_id = variation
        report.configuration_key += ":" + variation
        for claim in report.claims:
            claim.id += ":" + variation
            claim.capture_id += ":" + variation
            if claim.acquisition_capture_id is not None:
                claim.acquisition_capture_id = claim.capture_id
            claim.context.configuration_key = report.configuration_key
            if claim.context.variation_id is not None:
                claim.context.variation_id = variation
            if claim.field == "dial":
                claim.value = dial
        for scenario in report.cost_scenarios:
            scenario.context.configuration_key = report.configuration_key
            scenario.context.variation_id = variation
            for claim in scenario.context_evidence + [
                e for component in scenario.components for e in component.evidence
            ]:
                claim.id += ":" + variation
                claim.capture_id += ":" + variation
                claim.acquisition_capture_id = claim.capture_id
                claim.context.configuration_key = report.configuration_key
                claim.context.variation_id = variation
        result.append(report)
    return result


async def main(output, *, single=False):
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            initial_reports = reports(harness)
            initial = (
                await read_capture(
                    harness, client, initial_reports[:1] if single else initial_reports
                )
            )["candidates"][0]
            assert len(initial["configurations"]) == (1 if single else 2)
            assert all(c["state"] == "supported" for c in initial["configurations"])
            assert all(
                o["cost_scenarios"][0]["state"] == "verified_at_observation"
                for o in initial["offers"]
            )
            mint = next(c for c in initial["configurations"] if c["values"]["dial"] == "mint")
            blue = next(
                (c for c in initial["configurations"] if c["values"]["dial"] == "blue"), None
            )
            endpoint = f"/api/discovery/candidates/{initial['id']}/corrections/{mint['id']}"
            request = {
                **edit(initial),
                "configuration_revision": mint["revision"],
                "observed_configuration_id": mint["id"],
            }
            response = await client.post(endpoint, json=request)
            assert response.status_code == 201, response.text
            corrected = (await get(client, "/api/discovery/watches"))["candidates"][0]
            blue_after_correction = next(
                (c for c in corrected["configurations"] if blue and c["id"] == blue["id"]), None
            )
            if blue_after_correction:
                assert blue_after_correction["state"] == "supported"
            harness.clock.advance(hours=0.1)
            fresh_reports = reports(harness, corrected=True)
            fresh = (
                await read_capture(harness, client, fresh_reports[:1] if single else fresh_reports)
            )["candidates"][0]
            observed = {
                "correction": await get(client, endpoint),
                "configurations": fresh["configurations"],
                "offers": [
                    {
                        "id": offer["id"],
                        "qualification": offer["qualification"],
                        "cost": offer["cost_scenarios"][0],
                    }
                    for offer in fresh["offers"]
                ],
                "public_total": fresh["public_delivered_total"],
            }
        async with harness.session() as (client, _):
            restarted = (await get(client, "/api/discovery/watches"))["candidates"][0]
            assert restarted["configurations"] == observed["configurations"]
            assert harness.deliveries == harness.blocked_edges == []
            receipt = {
                "fixture": (
                    "ticket07-single-control" if single else "ticket07-multi-configuration-merger"
                ),
                "result": (
                    "passed"
                    if observed["correction"]["requalification"] == "supported_by_fresh_evidence"
                    and all(c["state"] == "supported" for c in restarted["configurations"])
                    else "failed"
                ),
                "initial_dials": [c["values"]["dial"] for c in initial["configurations"]],
                "blue_after_correction": (
                    blue_after_correction["state"] if blue_after_correction else None
                ),
                "after_fresh_capture_and_restart": observed,
                "guard": {
                    "temporary_storage": True,
                    "blocked_edges": harness.blocked_edges,
                    "notifications_sent": len(harness.deliveries),
                    "collection_state": "staged",
                },
            }
            output.write_text(json.dumps(receipt, indent=2) + "\n")
            assert (
                observed["correction"]["requalification"] == "supported_by_fresh_evidence"
            ), "Fresh supported salmon configuration cannot requalify alongside unrelated blue"
            assert all(
                c["state"] == "supported" for c in restarted["configurations"]
            ), "Unrelated blue configuration withdrawn during corrected salmon reacquisition"


if __name__ == "__main__":
    asyncio.run(main(Path(sys.argv[1]).resolve(), single="--single" in sys.argv[2:]))
