"""Bounded ticket08 review probes at API/execution and external send/config edges.

Run each mode in a fresh child; no private storage writes or evaluator patches.
"""
import asyncio
import json
import sys
from datetime import UTC, datetime
from unittest.mock import patch

from tests.monitoring.assessment_workflows import capture, coupon_report, policy, priced_report
from tests.monitoring.harness import MonitoringHarness
from tests.monitoring.tracking_workflows import policy as tracking_policy, track
from tests.monitoring.workflows import get


async def probe(mode):
    with MonitoringHarness() as harness:
        from pricerecon.core import exact_tracking, notifications

        async with harness.session() as (client, _):
            supplied = policy(harness, allowed_scenario_kinds=["public_no_coupon", "public_coupon"])
            opted_in = tracking_policy().model_copy(
                update={"allowed_scenario_kinds": ["public_no_coupon", "public_coupon"]}
            )
            feed = await capture(harness, client, [priced_report(harness, "48", "coupon-path")], supplied)
            channels = ["webhook", "discord"] if mode == "channel_expiry" else ["webhook"]
            saved = await track(client, feed["candidates"][0], target="47", notifications={"channels": channels})
            harness.clock.advance(hours=0.01)
            await capture(harness, client, [priced_report(harness, "48", "coupon-path")], supplied, opted_in)
            harness.clock.advance(hours=0.01)
            with patch.object(notifications, "get_global_notification_config", side_effect=RuntimeError("review-config-edge")):
                try:
                    await capture(harness, client, [coupon_report(harness, 3)], supplied, opted_in)
                except RuntimeError as exc:
                    assert str(exc) == "review-config-edge"
                else:
                    raise AssertionError("Expected external configuration interruption")
            before = await get(client, f"/api/discovery/tracking/{saved['id']}/deliveries")
            assert before["items"][0]["status"] == "pending", before
            assert before["items"][0]["delivered_gbp"] == "45.10", before
            assert not harness.deliveries

            async def webhook(url, payload):
                harness.deliveries.append(("webhook", url, payload))
                if mode == "channel_expiry":
                    harness.clock.now = datetime(2026, 10, 27, 13, tzinfo=UTC)
                return True

            with patch.object(notifications, "send_webhook", webhook), patch.object(
                notifications, "get_global_notification_config", lambda: {
                    "webhook_url": "https://synthetic.invalid/captured",
                    "discord_webhook_url": "https://synthetic.invalid/discord",
                }
            ):
                await exact_tracking.deliver_pending_targets(policy=tracking_policy() if mode == "opt_out" else opted_in)
            after = await get(client, f"/api/discovery/tracking/{saved['id']}/deliveries")
            if mode == "opt_out":
                assert not harness.deliveries, harness.deliveries
                assert after["items"][0]["status"] == "withheld", after
            else:
                assert len(harness.deliveries) == 1, harness.deliveries
                payload = harness.deliveries[0][2]
                assert payload["listing"]["coupon_codes"] == "TEN", payload
                assert payload["listing"]["base_delivered_gbp"] == "50.10", payload
                assert "TEN" in payload["message"] and "50.10" in payload["message"], payload
                if mode == "channel_expiry":
                    assert after["items"][0]["channels"] == {"webhook": "sent", "discord": "withheld"}, after
            assert not harness.blocked_edges, harness.blocked_edges
            print(json.dumps({"mode": mode, "before": before, "after": after, "deliveries": harness.deliveries,
                              "blocked_edges": harness.blocked_edges, "result": "passed"}, indent=2))


asyncio.run(probe(sys.argv[1]))
