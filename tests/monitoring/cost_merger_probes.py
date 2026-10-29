"""Ticket04 merger probe: equivalent FX quanta must preserve payable outcomes.

Run in a fresh process with the documented cleared environment. This exercises
normal acquisition, persisted API readback and budget fit under the existing
isolated harness. All quotes are synthetic; no legal or live evidence.
"""

import asyncio
import json
import sys
from decimal import Decimal
from pathlib import Path

from .cost_workflows import cost_report, read_capture
from .harness import MonitoringHarness


async def probe():
    observations = []
    with MonitoringHarness() as harness:
        from pricerecon.models.qualification import MerchantEvidenceReport

        async with harness.session() as (client, _):
            response = await client.put(
                "/api/discovery/watches/preferences",
                json={"expected_revision": 0, "values": {"budget_gbp": "49.00"}},
            )
            assert response.status_code == 200
            previous = []
            for quantum in ("0.01", "0.010", "1E+1", "10", "10.0"):
                payload = cost_report(harness, "fx-quantum").model_dump(mode="json")
                scenario = payload["cost_scenarios"][0]
                scenario["components"][1]["currency"] = "USD"
                scenario["fx_quotes"] = [
                    {
                        "purpose": "buyer_payment",
                        "from_currency": "USD",
                        "to_currency": "GBP",
                        "rate": "0.741",
                        "direction": "target_per_source",
                        "converter": "synthetic-provider",
                        "spread_included": True,
                        "quantum": quantum,
                        "rounding": "ROUND_HALF_UP",
                        "state": "observed",
                        "evidence": scenario["context_evidence"],
                    }
                ]
                report = MerchantEvidenceReport.model_validate(payload)
                feed = await read_capture(harness, client, [report])
                candidate = feed["candidates"][0]
                offer = candidate["offers"][0]
                cost = offer["cost_scenarios"][0]
                history = (await client.get(f"/api/discovery/offers/{offer['id']}/costs")).json()
                assert history["scenarios"][:-1] == previous
                assert history["scenarios"][-1] == cost
                previous = history["scenarios"]
                observations.append(
                    {
                        "quantum": quantum,
                        "state": cost["state"],
                        "total": cost["total"],
                        "public_total": candidate["public_delivered_total"]["amount"],
                        "budget_fit": next(
                            fit["state"]
                            for fit in candidate["preference_fit"]
                            if fit["field"] == "budget"
                        ),
                        "history_revisions": len(previous),
                        "comparison": offer["comparison"]["state"],
                        "alert_eligible": candidate["alert_eligible"],
                    }
                )
            assert harness.blocked_edges == harness.deliveries == []
    return {
        "date": "2026-10-27",
        "fixture": "synthetic GBP item 48; USD shipping 2.10; GBP/USD rate 0.741; budget GBP 49",
        "observations": observations,
        "historical_rows_unchanged": True,
        "blocked_edges": [],
        "notifications": [],
    }


if __name__ == "__main__":
    receipt = asyncio.run(probe())
    output = json.dumps(receipt, indent=2) + "\n"
    print(output, end="")
    if len(sys.argv) == 2:
        Path(sys.argv[1]).write_text(output)
    rows = receipt["observations"]
    failures = []
    for first, second in ((0, 1), (2, 3), (2, 4)):
        a, b = rows[first], rows[second]
        assert Decimal(a["quantum"]) == Decimal(b["quantum"])
        if Decimal(a["total"]["amount"]) != Decimal(b["total"]["amount"]):
            failures.append(f"{a['quantum']} versus {b['quantum']}: {a['total']} != {b['total']}")
    assert not failures, "Equivalent FX quanta change verified payable outcomes: " + "; ".join(
        failures
    )
