"""Final SPEC review: original synthetic inputs, guarded temporary DB only."""
import asyncio
import json
import sys
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.monitoring.harness import MonitoringHarness
from tests.monitoring.coupon_workflows import reproduced_report
from tests.monitoring.cost_workflows import read_capture


async def main():
    mode = sys.argv[1]
    with TemporaryDirectory(prefix="pricerecon-offline-final-spec-") as root, ExitStack() as stack:
        Path(root, ".offline-monitoring").write_text("ticket01-test-storage\n")
        harness = stack.enter_context(MonitoringHarness(storage_root=Path(root)))
        async with harness.session() as (client, _):
            valid = reproduced_report(harness)
            expired = valid.model_copy(deep=True)
            expired.coupons[0].terms.ends_at = harness.clock.now
            expired.coupons[0].terms.literal = "Contradictory synthetic terms: expired now, exclusive end"
            reports = {
                "valid-first": [valid, expired],
                "expired-first": [expired, valid],
                "expired-only": [expired],
                "same-report-conflict": [valid],
            }[mode]
            if mode == "same-report-conflict":
                valid.coupons.append(expired.coupons[0])
            feed = await read_capture(harness, client, reports)
            candidate = feed["candidates"][0]
            offer = candidate["offers"][0]
            history = (await client.get(f"/api/discovery/offers/{offer['id']}/coupons")).json()
            coupon = offer["coupons"][0]
            print(json.dumps({
                "mode": mode,
                "marked_temporary_storage": str(harness.database),
                "input_reports": len(reports),
                "input_term_end_times": [str(r.coupons[0].terms.ends_at) for r in reports],
                "state": coupon["state"],
                "issues": coupon["issues"],
                "retained_terms": coupon["terms"]["literal"],
                "source_conflicts_count": len(coupon["source_conflicts"]),
                "result_total": coupon["resulting_cost"]["total"] if coupon["resulting_cost"] else None,
                "no_coupon": candidate["public_delivered_total"],
                "coupon_history_count": len(history["assessments"]),
                "blocked_edges": harness.blocked_edges,
                "deliveries": harness.deliveries,
            }, indent=2))


asyncio.run(main())
