"""Reproduce ticket06's derived-copy gap through the guarded application seam.

Run in a fresh process. This is an intentionally failing merger probe, outside
pytest collection; it does not supply another source or real market history.
"""

import asyncio
import json
import sys
from pathlib import Path

from .cost_workflows import read_capture
from .harness import MonitoringHarness
from .history_workflows import history, priced_report


async def probe(output: Path) -> None:
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            original = priced_report(harness)
            candidate = (await read_capture(harness, client, [original]))["candidates"][0]
            before = await history(client, candidate)
            harness.clock.advance()
            copied = original.model_copy(deep=True)
            claims = copied.claims + [
                evidence
                for scenario in copied.cost_scenarios
                for evidence in scenario.context_evidence
                + [e for component in scenario.components for e in component.evidence]
            ]
            for claim in claims:
                old_capture = claim.capture_id
                claim.derived_from = [old_capture]
                claim.capture_id = "re-extracted:" + old_capture
                claim.retrieved_at = harness.clock.now
                claim.extractor = "synthetic-re-extractor"
            # Values, observed times and purchase context are unchanged. Every
            # new extraction explicitly names the original retained acquisition.
            await read_capture(harness, client, [copied])
            after = await history(client, candidate)
            first, second = after["observations"]
            fields = ("id", "validity", "change", "duplicate_of", "observed_at", "lineage")
            receipt = {
                "fixture": "ticket06-merger-derived-copy",
                "expected": "Derived re-extraction is unqualified and names its original owner",
                "first": {key: first[key] for key in fields},
                "derived_copy": {key: second[key] for key in fields},
                "original_offer_preserved": first["offer"] == before["observations"][0]["offer"],
                "last_good_age_seconds": after["last_good"]["age_seconds"],
                "savings": after["savings"],
                "usual_price": after["usual_price"],
                "collection_state": "staged",
                "temporary_storage": True,
                "blocked_edges": harness.blocked_edges,
                "notifications_sent": len(harness.deliveries),
            }
            output.write_text(json.dumps(receipt, indent=2) + "\n")
            assert receipt["original_offer_preserved"]
            assert harness.deliveries == harness.blocked_edges == []
            assert second["duplicate_of"] == first["id"], (
                "Derived re-extraction counted as a new supported observation"
            )
            assert second["validity"] == "unqualified"


if __name__ == "__main__":
    asyncio.run(probe(Path(sys.argv[1]).resolve()))
