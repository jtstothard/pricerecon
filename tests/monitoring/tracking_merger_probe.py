"""Ticket05 delivery-boundary probes using guarded application workflows.

Each invocation is a fresh process with original synthetic evidence. Withdrawal
uses06's committed input contract; it does not accept or repair06's history.
"""

import asyncio
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from .cost_workflows import read_capture
from .harness import MonitoringHarness
from .tracking_workflows import capture, policy, priced_report, track
from .workflows import get


async def probe(case: str, output: Path) -> None:
    assert case in {"configuration", "binding", "offer", "cost", "expiry", "false_ack"}
    with MonitoringHarness() as harness:
        from pricerecon.core import notifications
        from pricerecon.core.exact_tracking import deliver_pending_targets
        from pricerecon.db.history import append_history_invalidation
        from pricerecon.models.history import HistoryInvalidation

        async with harness.session() as (client, _):
            candidate = (await read_capture(harness, client, [priced_report(harness)]))[
                "candidates"
            ][0]
            channels = ["webhook"] if case == "false_ack" else ["webhook", "discord"]
            saved = await track(client, candidate, notifications={"channels": channels})
            url = f"/api/discovery/tracking/{saved['id']}"
            await capture(harness, client, priced_report(harness))
            harness.clock.advance(hours=0.1)

            async def first_channel(endpoint, payload):
                # The first recipient may already have accepted. It cannot be
                # retracted; only later channels/recovery can be withheld.
                harness.deliveries.append(("webhook", endpoint, payload))
                if case == "false_ack":
                    return False
                if case == "expiry":
                    harness.clock.advance(hours=3)
                    return True
                current = await get(client, url)
                assessment = current["assessment"]
                feed = await get(client, "/api/discovery/watches")
                latest = next(c for c in feed["candidates"] if c["id"] == candidate["id"])
                binding = next(
                    b
                    for b in latest["bindings"]
                    if b["configuration_id"] == saved["configuration_id"]
                )
                target_id, revision = {
                    "configuration": (
                        saved["configuration_id"],
                        assessment["configuration_revision"],
                    ),
                    "binding": (binding["id"], assessment["binding_revision"]),
                    "offer": (assessment["offer_id"], assessment["offer_revision"]),
                    "cost": (assessment["scenario_id"], assessment["scenario_revision"]),
                }[case]
                with closing(sqlite3.connect(harness.database)) as connection, connection:
                    connection.execute("BEGIN IMMEDIATE")
                    append_history_invalidation(
                        connection,
                        HistoryInvalidation(
                            id="synthetic-between-channels",
                            target={"kind": case, "id": target_id, "revision": revision},
                            recorded_at=harness.clock.now,
                            reason="Synthetic exact revision withdrawn between channels",
                            correction_reference="synthetic-only",
                        ),
                    )
                return True

            with (
                patch.object(
                    notifications,
                    "get_global_notification_config",
                    lambda: {
                        "webhook_url": "https://synthetic.invalid/capture",
                        "discord_webhook_url": "https://synthetic.invalid/discord",
                    },
                ),
                patch.object(notifications, "send_webhook", first_channel),
            ):
                await capture(harness, client, priced_report(harness, "56"))
                # Neither repeat recovery nor a failed ACK may retry a claim.
                await deliver_pending_targets(policy=policy())
                await deliver_pending_targets(policy=policy())
            intent = await get(client, url)
            delivery = (await get(client, url + "/deliveries"))["items"][0]
            receipt = {
                "case": case,
                "fixture": "original synthetic target evidence / captured transport",
                "expected": "One first-channel attempt; no second send or automatic retry",
                "captured_attempts": len(harness.deliveries),
                "assessment": intent["assessment"],
                "delivery": delivery,
                "target_retained": intent["target_gbp"] == saved["target_gbp"],
                "configuration_retained": intent["configuration_id"] == saved["configuration_id"],
                "collection_state": intent["collection_state"],
                "blocked_edges": harness.blocked_edges,
                "temporary_storage": True,
            }
            output.write_text(json.dumps(receipt, indent=2) + "\n")
            assert len(harness.deliveries) == 1, receipt
            assert receipt["target_retained"] and receipt["configuration_retained"], receipt
            assert intent["collection_state"] == "staged"
            assert harness.blocked_edges == []
            if case == "false_ack":
                assert delivery["channels"] == {"webhook": "failed"}, receipt
                assert delivery["status"] == "ambiguous", receipt
            else:
                assert delivery["channels"] == {"webhook": "sent", "discord": "withheld"}, receipt
                assert delivery["status"] == "withheld", receipt
                reason = (
                    "evidence_stale_or_expired"
                    if case == "expiry"
                    else "evidence_revision_withdrawn"
                )
                assert intent["assessment"]["state"] == "withheld", receipt
                assert reason in intent["assessment"]["reasons"], receipt


if __name__ == "__main__":
    asyncio.run(probe(sys.argv[1], Path(sys.argv[2]).resolve()))
