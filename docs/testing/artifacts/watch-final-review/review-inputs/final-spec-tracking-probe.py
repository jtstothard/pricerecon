"""Final SPEC review: fresh prices with still-valid manufacturer definitions."""
import asyncio
import json
import sys
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from tests.monitoring.harness import MonitoringHarness
from tests.monitoring.history_workflows import priced_report
from tests.monitoring.tracking_workflows import capture, track
from tests.monitoring.cost_workflows import read_capture
from tests.monitoring.workflows import get


async def main():
    mode = sys.argv[1]
    with TemporaryDirectory(prefix="pricerecon-offline-final-spec-") as root, ExitStack() as stack:
        Path(root, ".offline-monitoring").write_text("ticket01-test-storage\n")
        harness = stack.enter_context(MonitoringHarness(storage_root=Path(root)))
        async with harness.session() as (client, _):
            from pricerecon.core import notifications
            original = priced_report(harness, "68.00")
            candidate = (await read_capture(harness, client, [original]))["candidates"][0]
            saved = await track(client, candidate, notifications={"channels": ["webhook"]})
            with patch.object(notifications, "get_global_notification_config", lambda: {
                "webhook_url": "https://synthetic.invalid/captured-send"
            }):
                await capture(harness, client, original)
                before = await get(client, f"/api/discovery/tracking/{saved['id']}")
                harness.clock.advance(hours=0.5)
                fresh = priced_report(harness, "56.00")
                if mode == "retained-definition":
                    fresh.claims = [
                        next(c for c in original.claims if c.subject == claim.subject and c.field == claim.field).model_copy(deep=True)
                        if claim.subject == "configuration" else claim
                        for claim in fresh.claims
                    ]
                await capture(harness, client, fresh)
                after = await get(client, f"/api/discovery/tracking/{saved['id']}")
                history = await get(client, f"/api/discovery/candidates/{candidate['id']}/history")
                events = await get(client, "/api/events")
                print(json.dumps({
                    "mode": mode,
                    "marked_temporary_storage": str(harness.database),
                    "definition_observed_at": str(next(c.observed_at for c in fresh.claims if c.subject == "configuration")),
                    "price_observed_at": str(next(c.observed_at for c in fresh.claims if c.subject == "offer" and c.field == "item_price")),
                    "before": before["assessment"],
                    "after": after["assessment"],
                    "latest_history_validity": history["observations"][-1]["validity"],
                    "latest_history_change": history["observations"][-1]["change"],
                    "event_count": events["total"],
                    "delivery_count": len(harness.deliveries),
                    "blocked_edges": harness.blocked_edges,
                }, indent=2))


asyncio.run(main())
