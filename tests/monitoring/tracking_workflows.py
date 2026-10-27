"""Ticket05 original synthetic evidence; never current merchant/buyer proof."""

import asyncio
import sys

from .cost_workflows import cost_report, read_capture
from .harness import MonitoringHarness
from .workflows import LEGACY, get


def policy():
    from pricerecon.models.tracking import TrackingPolicy

    return TrackingPolicy(
        version="synthetic-target-policy-v1",
        max_evidence_age_seconds=7200,
        allowed_conditions=["new"],
        quantity=1,
        destination_nation="England",
        destination_region="synthetic-region",
        payment_method="synthetic-gbp-debit",
    )


def priced_report(harness, item="68.00", listing_id="cost"):
    from decimal import Decimal

    report = cost_report(harness, listing_id)
    for claim in report.claims:
        if claim.field == "item_price":
            claim.value = item
    report.cost_scenarios[0].components[0].amount = Decimal(item)
    return report


async def capture(
    harness,
    client,
    report,
    *,
    supplied_policy=True,
    sources=("cex",),
    title="Synthetic exact watch",
):
    from pricerecon.core.discovery import execute_discovery
    from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest

    from .workflows import listing

    for source in sources:
        harness.reports[source] = [report]
        harness.outcomes[source] = [
            listing(harness, source, report.source_listing_id, title, "1.00")
        ]
    result = await execute_discovery(
        DiscoveryRequest(query="watch", sources=[{"connector": s} for s in sources]),
        admission=DiscoveryAdmission(
            mode="offline_verification",
            policy_reference="synthetic",
            permission_reference="original-test-data",
            activation_reference="isolated-harness",
        ),
        tracking_policy=policy() if supplied_policy else None,
    )
    feed = await get(client, "/api/discovery/watches")
    return result, feed


async def track(client, candidate, target="60.00", **extra):
    config = candidate["configurations"][0]
    response = await client.post(
        "/api/discovery/tracking",
        json={
            "candidate_id": candidate["id"],
            "capture_id": candidate["capture_id"],
            "configuration_id": config["id"],
            "configuration_revision": config["revision"],
            "target_gbp": target,
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def intent():
    with MonitoringHarness() as harness:
        harness.seed_legacy([(7, LEGACY), (8, {**LEGACY, "name": "Paused", "enabled": False})])
        async with harness.session() as (client, scheduler):
            before = await get(client, "/api/watches")
            jobs = scheduler.list_watches()
            candidate = (await read_capture(harness, client, [cost_report(harness)]))["candidates"][
                0
            ]
            saved = await track(client, candidate)
            assert saved["target_gbp"] == "60.00"
            assert saved["collection_state"] == "staged"
            assert saved["assessment"]["state"] == "withheld"
            assert "policy_required" in saved["assessment"]["reasons"]
            assert (await get(client, "/api/discovery/tracking"))["items"] == [saved]
            searches = len(harness.searches)
            response = await client.put(
                f"/api/discovery/tracking/{saved['id']}",
                json={
                    "expected_revision": saved["revision"],
                    "target_gbp": "55.25",
                    "notifications": {"channels": ["webhook"]},
                },
            )
            assert response.status_code == 200, response.text
            edited = response.json()
            assert edited["target_gbp"] == "55.25" and edited["revision"] == 2
            assert (
                await client.put(
                    f"/api/discovery/tracking/{saved['id']}",
                    json={
                        "expected_revision": 1,
                        "target_gbp": "1.00",
                    },
                )
            ).status_code == 409
            assert (
                await client.post(
                    "/api/discovery/tracking",
                    json={
                        "candidate_id": candidate["id"],
                        "capture_id": candidate["capture_id"],
                        "configuration_id": candidate["configuration"]["id"],
                        "configuration_revision": 999,
                        "target_gbp": "60",
                    },
                )
            ).status_code == 409
            for bad in ("NaN", "-1", "0", "1e999", 12.5, True):
                assert (
                    await client.put(
                        f"/api/discovery/tracking/{saved['id']}",
                        json={
                            "expected_revision": 2,
                            "target_gbp": bad,
                        },
                    )
                ).status_code == 422
            assert (
                await client.post(
                    "/api/discovery/tracking",
                    json={
                        "candidate_id": "missing",
                        "capture_id": candidate["capture_id"],
                        "configuration_id": "missing",
                        "configuration_revision": 1,
                        "target_gbp": "60",
                    },
                )
            ).status_code == 404
            assert await get(client, "/api/watches") == before
            assert scheduler.list_watches() == jobs
            assert len(harness.searches) == searches
            assert harness.deliveries == harness.blocked_edges == []


async def crossings():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, scheduler):
            candidate = (await read_capture(harness, client, [priced_report(harness)]))[
                "candidates"
            ][0]
            saved = await track(client, candidate, notifications={"channels": ["webhook"]})
            # Use the existing global notification owner, with a captured transport.
            from unittest.mock import patch

            from pricerecon.core import notifications

            with patch.object(
                notifications,
                "get_global_notification_config",
                lambda: {"webhook_url": "https://synthetic.invalid/captured-send"},
            ):
                await capture(harness, client, priced_report(harness))
                state = await get(client, f"/api/discovery/tracking/{saved['id']}")
                assert state["assessment"]["state"] == "above_target"
                assert harness.deliveries == []
                for item, expected, reason in (
                    ("56.00", 1, "target_crossing"),  # delivered £58.10, never £1 lead
                    ("56.00", 1, "duplicate_offer_price"),
                    ("55.00", 2, "further_drop"),
                    ("55.50", 2, "duplicate_offer_price"),
                    ("55.00", 2, "duplicate_offer_price"),
                    ("68.00", 2, "above_target"),
                    ("56.00", 3, "target_crossing"),
                ):
                    harness.clock.advance(hours=0.1)
                    await capture(harness, client, priced_report(harness, item))
                    assert len(harness.deliveries) == expected, (item, harness.deliveries)
                    state = await get(client, f"/api/discovery/tracking/{saved['id']}")
                    assert reason in state["assessment"]["reasons"], state
                payload = harness.deliveries[0][2]
                assert payload["event_type"] == "exact_target_crossing"
                assert payload["watch_id"] is None
                assert payload["listing"]["delivered_gbp"] == "58.10"
                assert "verified UK delivered" in payload["message"]
                events = await get(client, "/api/events")
                assert events["total"] == 3
                assert all(e["watch_id"] is None for e in events["items"])
                deliveries = await get(client, f"/api/discovery/tracking/{saved['id']}/deliveries")
                assert len(deliveries["items"]) == 3
                assert all(d["channels"] == {"webhook": "sent"} for d in deliveries["items"])
            assert scheduler.list_watches() == []
            assert harness.blocked_edges == []


async def withholding():
    from datetime import timedelta
    from unittest.mock import patch

    with MonitoringHarness() as harness:
        from pricerecon.core import notifications

        async with harness.session() as (client, _):
            candidate = (await read_capture(harness, client, [priced_report(harness)]))[
                "candidates"
            ][0]
            saved = await track(client, candidate, notifications={"channels": ["webhook"]})
            url = f"/api/discovery/tracking/{saved['id']}"
            with patch.object(
                notifications,
                "get_global_notification_config",
                lambda: {"webhook_url": "https://synthetic.invalid/capture"},
            ):
                await capture(harness, client, priced_report(harness))
                cases = [
                    "missing",
                    "conditional",
                    "stale",
                    "withdrawn",
                    "sku",
                    "identity",
                    "eligibility",
                    "policy",
                    "preferences",
                    "expired",
                ]
                for case in cases:
                    harness.clock.advance(hours=0.1)
                    report = priced_report(harness, "40")
                    if case == "missing":
                        report.cost_scenarios[0].components[1].state = "unknown"
                        report.cost_scenarios[0].components[1].amount = None
                    if case == "conditional":
                        report.cost_scenarios[0].components[1].state = "conditional"
                        report.cost_scenarios[0].components[1].assumptions = ["synthetic estimate"]
                    if case == "stale":
                        for c in report.claims:
                            c.observed_at = harness.clock.now - timedelta(days=1)
                    if case == "withdrawn":
                        next(c for c in report.claims if c.field == "availability").value = (
                            "out_of_stock"
                        )
                    if case in {"sku", "identity"}:
                        report.claims = [
                            c
                            for c in report.claims
                            if not (
                                c.subject == ("selection" if case == "sku" else "configuration")
                                and c.field == "movement"
                            )
                        ]
                    if case == "eligibility":
                        report.cost_scenarios[0].context.payment_method = "other-method"
                    if case == "expired":
                        report.cost_scenarios[0].context_evidence[0].expires_at = harness.clock.now
                    if case == "preferences":
                        profile = await get(client, "/api/discovery/watches/preferences")
                        response = await client.put(
                            "/api/discovery/watches/preferences",
                            json={
                                "expected_revision": profile["revision"],
                                "values": {**profile["values"], "compact_max_width_mm": "30"},
                            },
                        )
                        assert response.status_code == 200
                    await capture(harness, client, report, supplied_policy=case != "policy")
                    result = await get(client, url)
                    assert result["assessment"]["state"] == "withheld", (case, result)
                    assert harness.deliveries == [], (case, harness.deliveries)
                # Restoring preferences isn't a bargain. Neither failed-source
                # recovery nor re-reading the same qualified price can notify.
                profile = await get(client, "/api/discovery/watches/preferences")
                await client.put(
                    "/api/discovery/watches/preferences",
                    json={"expected_revision": profile["revision"], "values": {}},
                )
                await capture(harness, client, priced_report(harness))
                assert harness.deliveries == []
                harness.clock.advance(hours=3)
                result = await get(client, url)
                assert result["assessment"]["state"] == "withheld", result
                assert "evidence_stale_or_expired" in result["assessment"]["reasons"]
                feed = await get(client, "/api/discovery/watches")
                assert feed["tracking"][0] == result
            assert harness.blocked_edges == []


async def restart_before():
    from pathlib import Path
    from unittest.mock import patch

    with MonitoringHarness(storage_root=Path(sys.argv[2])) as harness:
        from pricerecon.core import notifications

        async with harness.session() as (client, _):
            candidate = (await read_capture(harness, client, [priced_report(harness)]))[
                "candidates"
            ][0]
            await track(client, candidate, notifications={"channels": ["webhook"]})
            with patch.object(
                notifications,
                "get_global_notification_config",
                lambda: {"webhook_url": "https://synthetic.invalid/capture"},
            ):
                await capture(harness, client, priced_report(harness))
                harness.clock.advance(hours=0.1)
                await capture(harness, client, priced_report(harness, "56"))
                assert len(harness.deliveries) == 1
            assert harness.blocked_edges == []


async def restart_after():
    from pathlib import Path
    from unittest.mock import patch

    with MonitoringHarness(storage_root=Path(sys.argv[2])) as harness:
        from pricerecon.core import notifications

        harness.clock.advance(hours=1)
        async with harness.session() as (client, _):
            intent = (await get(client, "/api/discovery/tracking"))["items"][0]
            assert intent["target_gbp"] == "60.00"
            original = await get(client, f"/api/discovery/tracking/{intent['id']}/deliveries")
            assert original["items"][0]["status"] == "sent"
            with patch.object(
                notifications,
                "get_global_notification_config",
                lambda: {"webhook_url": "https://synthetic.invalid/capture"},
            ):
                await capture(
                    harness, client, priced_report(harness, "56.000"), sources=("cex", "scan")
                )
                assert harness.deliveries == []
                assert (await get(client, "/api/events"))["total"] == 1
                harness.clock.advance(hours=0.1)
                await capture(
                    harness, client, priced_report(harness, "54"), sources=("cex", "scan")
                )
                assert len(harness.deliveries) == 1
                assert (await get(client, "/api/events"))["total"] == 2
                # Replayed old evidence, even a purported rise, cannot rearm.
                report = priced_report(harness, "100")
                from datetime import timedelta

                for claim in report.claims:
                    claim.observed_at -= timedelta(hours=1)
                for evidence in report.cost_scenarios[0].context_evidence:
                    evidence.observed_at -= timedelta(hours=1)
                await capture(harness, client, report)
                harness.clock.advance(hours=0.1)
                await capture(harness, client, priced_report(harness, "56"))
                assert len(harness.deliveries) == 1
            assert harness.blocked_edges == []


class Interrupted(BaseException):
    pass


async def interruption_before(ambiguous):
    from pathlib import Path
    from unittest.mock import patch

    with MonitoringHarness(storage_root=Path(sys.argv[2])) as harness:
        from pricerecon.core import notifications

        async with harness.session() as (client, _):
            candidate = (await read_capture(harness, client, [priced_report(harness)]))[
                "candidates"
            ][0]
            saved = await track(client, candidate, notifications={"channels": ["webhook"]})
            await capture(harness, client, priced_report(harness))
            harness.clock.advance(hours=0.1)

            def presend_crash():
                raise Interrupted("Synthetic crash before dispatch/transport claim")

            async def transport_crash(url, payload):
                harness.deliveries.append(("webhook", url, payload))
                raise Interrupted("Synthetic external accept followed by process death")

            try:
                with (
                    patch.object(
                        notifications,
                        "get_global_notification_config",
                        (
                            (lambda: {"webhook_url": "https://synthetic.invalid/capture"})
                            if ambiguous
                            else presend_crash
                        ),
                    ),
                    patch.object(notifications, "send_webhook", transport_crash),
                ):
                    await capture(harness, client, priced_report(harness, "56"))
            except Interrupted:
                pass
            else:
                raise AssertionError("Expected interrupted delivery")
            deliveries = await get(client, f"/api/discovery/tracking/{saved['id']}/deliveries")
            assert deliveries["items"][0]["status"] == ("ambiguous" if ambiguous else "pending")
            assert len(harness.deliveries) == int(ambiguous)
            assert harness.blocked_edges == []


async def presend_before():
    await interruption_before(False)


async def ambiguous_before():
    await interruption_before(True)


async def interruption_after(ambiguous):
    from pathlib import Path
    from unittest.mock import patch

    with MonitoringHarness(storage_root=Path(sys.argv[2])) as harness:
        from pricerecon.core import notifications

        harness.clock.advance(hours=1)
        async with harness.session() as (client, _):
            saved = (await get(client, "/api/discovery/tracking"))["items"][0]
            with patch.object(
                notifications,
                "get_global_notification_config",
                lambda: {"webhook_url": "https://synthetic.invalid/capture"},
            ):
                await capture(harness, client, priced_report(harness, "56"))
                assert len(harness.deliveries) == (0 if ambiguous else 1)
                deliveries = await get(client, f"/api/discovery/tracking/{saved['id']}/deliveries")
                first = deliveries["items"][0]
                assert first["status"] == ("ambiguous" if ambiguous else "sent"), first
                if ambiguous:
                    response = await client.put(
                        f"/api/discovery/tracking/{saved['id']}",
                        json={"expected_revision": saved["revision"], "target_gbp": "50"},
                    )
                    assert response.status_code == 409
                    # Resolving an attempt records operator knowledge, never a resend.
                    response = await client.post(
                        f"/api/discovery/tracking/{saved['id']}/deliveries/{first['event_id']}/resolve",
                        json={
                            "expected_revision": saved["revision"],
                            "channel": "webhook",
                            "resolution": "abandon",
                            "confirm_no_send_in_flight": True,
                        },
                    )
                    assert response.status_code == 200, response.text
                    assert response.json()["target_gbp"] == "60.00"
                harness.clock.advance(hours=0.1)
                await capture(harness, client, priced_report(harness, "56"))
                assert len(harness.deliveries) == (0 if ambiguous else 1)
            assert harness.blocked_edges == []


async def presend_after():
    await interruption_after(False)


async def ambiguous_after():
    await interruption_after(True)


async def serialized_delivery():
    from unittest.mock import patch

    with MonitoringHarness() as harness:
        import sqlite3
        from contextlib import closing

        from pricerecon.core import notifications
        from pricerecon.db.schema import DB_PATH
        from pricerecon.db.tracking import invalidate_configuration_tracking

        async with harness.session() as (client, _):
            candidate = (await read_capture(harness, client, [priced_report(harness)]))[
                "candidates"
            ][0]
            saved = await track(
                client, candidate, notifications={"channels": ["webhook", "discord"]}
            )
            await capture(harness, client, priced_report(harness))
            harness.clock.advance(hours=0.1)
            entered, release = asyncio.Event(), asyncio.Event()

            async def paused_send(url, payload):
                harness.deliveries.append(("webhook", url, payload))
                entered.set()
                await release.wait()
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
                patch.object(notifications, "send_webhook", paused_send),
            ):
                running = asyncio.create_task(
                    capture(harness, client, priced_report(harness, "56"))
                )
                await entered.wait()
                edit = await client.put(
                    f"/api/discovery/tracking/{saved['id']}",
                    json={"expected_revision": 1, "target_gbp": "1"},
                )
                assert edit.status_code == 409
                prefs = await get(client, "/api/discovery/watches/preferences")
                await client.put(
                    "/api/discovery/watches/preferences",
                    json={
                        "expected_revision": prefs["revision"],
                        "values": {"compact_max_width_mm": "30"},
                    },
                )
                release.set()
                await running
            assert len(harness.deliveries) == 1, harness.deliveries
            result = await get(client, f"/api/discovery/tracking/{saved['id']}")
            assert result["assessment"]["state"] == "withheld"
            # Programmatic correction participant, not a correction UI or a
            # second writer. Observe its effect through the accepted API seam.
            with closing(sqlite3.connect(DB_PATH)) as connection, connection:
                connection.execute("BEGIN IMMEDIATE")
                invalidate_configuration_tracking(
                    connection, saved["configuration_id"], "synthetic-withdrawal"
                )
            result = await get(client, f"/api/discovery/tracking/{saved['id']}")
            assert result["target_gbp"] == "60.00"
            assert result["configuration_id"] == saved["configuration_id"]
            assert result["invalidation_revision"] == 1
            assert "evidence_invalidated" in result["assessment"]["reasons"]
            harness.clock.advance(hours=0.1)
            await capture(harness, client, priced_report(harness, "40"))
            assert len(harness.deliveries) == 1
            assert harness.blocked_edges == []


async def changed_policy():
    from unittest.mock import patch

    with MonitoringHarness() as harness:
        from pricerecon.core import notifications
        from pricerecon.core.exact_tracking import deliver_pending_targets

        async with harness.session() as (client, _):
            candidate = (await read_capture(harness, client, [priced_report(harness)]))[
                "candidates"
            ][0]
            await track(client, candidate, notifications={"channels": ["webhook"]})
            await capture(harness, client, priced_report(harness))
            harness.clock.advance(hours=0.1)

            def crash():
                raise Interrupted()

            with patch.object(notifications, "get_global_notification_config", crash):
                try:
                    await capture(harness, client, priced_report(harness, "56"))
                except Interrupted:
                    pass
            changed = policy()
            changed.allowed_conditions = ["used"]
            with patch.object(
                notifications,
                "get_global_notification_config",
                lambda: {"webhook_url": "https://synthetic.invalid/capture"},
            ):
                await deliver_pending_targets(policy=changed)
            assert harness.deliveries == []
            assert harness.blocked_edges == []


async def route_conflict():
    from unittest.mock import patch

    with MonitoringHarness() as harness:
        from pricerecon.core import notifications

        async with harness.session() as (client, _):
            candidate = (await read_capture(harness, client, [priced_report(harness)]))[
                "candidates"
            ][0]
            saved = await track(client, candidate, notifications={"channels": ["webhook"]})
            await capture(harness, client, priced_report(harness))
            harness.clock.advance(hours=0.1)
            from pricerecon.models.qualification import EvidenceSearchReport

            from .workflows import listing

            conflicting = priced_report(harness, "40")
            harness.report_overrides["scan"] = EvidenceSearchReport(
                listings=[listing(harness, "scan", "cost", "Duplicate source", "1")],
                evidence=[conflicting],
            )
            with patch.object(
                notifications,
                "get_global_notification_config",
                lambda: {
                    "webhook_url": "https://synthetic.invalid/capture",
                    "defaults": [{"event": "exact_target_crossing", "channels": ["webhook"]}],
                },
            ):
                await capture(
                    harness, client, priced_report(harness, "56"), sources=("cex", "scan")
                )
                assert harness.deliveries == []
                result = await get(client, f"/api/discovery/tracking/{saved['id']}")
                assert "conflicting_route_totals" in result["assessment"]["reasons"], result
                response = await client.put(
                    f"/api/discovery/tracking/{saved['id']}",
                    json={"expected_revision": 1, "target_gbp": "60"},
                )
                assert response.status_code == 200
                harness.clock.advance(hours=0.1)
                await capture(harness, client, priced_report(harness))
                harness.clock.advance(hours=0.1)
                await capture(harness, client, priced_report(harness, "56"))
                assert harness.deliveries == []
            assert harness.blocked_edges == []


async def migration():
    import sqlite3
    from contextlib import closing
    from unittest.mock import patch

    with MonitoringHarness() as harness:
        harness.seed_legacy([(7, LEGACY)])
        # Fixture input: pre-1.6 storage with retained event/log IDs and a
        # deleted high event ID. Observations use only API/execution results.
        with closing(sqlite3.connect(harness.database)) as connection, connection:
            connection.executescript("""
                CREATE TABLE events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, watch_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL, listing_key TEXT, severity TEXT NOT NULL,
                    event_json TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(watch_id) REFERENCES watches(id) ON DELETE CASCADE
                );
                CREATE TABLE notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, event_id INTEGER NOT NULL,
                    channel TEXT NOT NULL, status TEXT NOT NULL, message TEXT, error_message TEXT,
                    sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(event_id) REFERENCES events(id)
                );
                INSERT INTO events VALUES (15,7,'price_drop','cex:old','notice',
                    '{"sentinel":"retained legacy event"}','2026-01-02T10:00:00Z');
                INSERT INTO notifications(event_id,channel,status,message)
                    VALUES(15,'webhook','sent','Retained notification');
                INSERT INTO events VALUES (25,7,'no_change',NULL,'debug','{}','2026-01-02T11:00:00Z');
                DELETE FROM events WHERE id=25;
            """)
        from pricerecon.core import notifications

        async with harness.session() as (client, _):
            events = await get(client, "/api/events")
            assert events["total"] == 1
            assert events["items"][0]["id"] == 15
            assert events["items"][0]["data"] == {"sentinel": "retained legacy event"}
            candidate = (await read_capture(harness, client, [priced_report(harness)]))[
                "candidates"
            ][0]
            await track(client, candidate, notifications={"channels": ["webhook"]})
            await capture(harness, client, priced_report(harness))
            harness.clock.advance(hours=0.1)
            with patch.object(
                notifications,
                "get_global_notification_config",
                lambda: {"webhook_url": "https://synthetic.invalid/capture"},
            ):
                await capture(harness, client, priced_report(harness, "56"))
            events = await get(client, "/api/events")
            assert events["total"] == 2
            assert max(e["id"] for e in events["items"]) > 25
            assert (await get(client, "/api/watches/7/events"))["total"] == 1
            assert len(harness.deliveries) == 1
            assert harness.blocked_edges == []


async def combined_acquisition():
    from unittest.mock import patch

    with MonitoringHarness() as harness:
        from pricerecon.core import notifications
        from pricerecon.models.qualification import EvidenceSearchReport

        from .workflows import listing

        async with harness.session() as (client, _):
            candidate = (await read_capture(harness, client, [priced_report(harness)]))[
                "candidates"
            ][0]
            saved = await track(client, candidate, notifications={"channels": ["webhook"]})
            original, _ = await capture(harness, client, priced_report(harness))
            with patch.object(
                notifications,
                "get_global_notification_config",
                lambda: {"webhook_url": "https://synthetic.invalid/capture"},
            ):
                for state in ("cache_reuse", "partial"):
                    harness.clock.advance(hours=0.1)
                    harness.report_overrides["cex"] = EvidenceSearchReport(
                        acquisition_state=state,
                        acquisition_reason="synthetic incomplete check",
                        reused_capture_id=original.capture_id if state == "cache_reuse" else None,
                        listings=[listing(harness, "cex", "cost", "Synthetic partial", "1")],
                        evidence=[priced_report(harness, "56")],
                    )
                    await capture(harness, client, priced_report(harness, "56"))
                    assert harness.deliveries == [], (state, harness.deliveries)
                    result = await get(client, f"/api/discovery/tracking/{saved['id']}")
                    assert "acquisition_partial_or_reused" in result["assessment"]["reasons"]
            assert harness.blocked_edges == []


async def combined_withdrawal():
    import sqlite3
    from contextlib import closing
    from unittest.mock import patch

    with MonitoringHarness() as harness:
        from pricerecon.core import notifications
        from pricerecon.core.exact_tracking import deliver_pending_targets
        from pricerecon.db.history import append_history_invalidation
        from pricerecon.models.history import HistoryInvalidation

        async with harness.session() as (client, _):
            candidate = (await read_capture(harness, client, [priced_report(harness)]))[
                "candidates"
            ][0]
            saved = await track(client, candidate, notifications={"channels": ["webhook"]})
            await capture(harness, client, priced_report(harness))
            harness.clock.advance(hours=0.1)

            def crash():
                raise Interrupted()

            with patch.object(notifications, "get_global_notification_config", crash):
                try:
                    await capture(harness, client, priced_report(harness, "56"))
                except Interrupted:
                    pass
            intent = await get(client, f"/api/discovery/tracking/{saved['id']}")
            assessment = intent["assessment"]
            # Use06's committed revision-withdrawal contract as input, without
            # implementing its history projection or07's correction UI.
            with closing(sqlite3.connect(harness.database)) as connection, connection:
                connection.execute("BEGIN IMMEDIATE")
                append_history_invalidation(
                    connection,
                    HistoryInvalidation(
                        id="synthetic-withdrawal",
                        target={
                            "kind": "cost",
                            "id": assessment["scenario_id"],
                            "revision": assessment["scenario_revision"],
                        },
                        recorded_at=harness.clock.now,
                        reason="Synthetic cost withdrawn",
                        correction_reference="synthetic-only",
                    ),
                )
            with patch.object(
                notifications,
                "get_global_notification_config",
                lambda: {"webhook_url": "https://synthetic.invalid/capture"},
            ):
                await deliver_pending_targets(policy=policy())
            assert harness.deliveries == []
            result = await get(client, f"/api/discovery/tracking/{saved['id']}")
            assert "evidence_revision_withdrawn" in result["assessment"]["reasons"]
            assert harness.blocked_edges == []


if __name__ == "__main__":
    asyncio.run(globals()[sys.argv[1]]())
