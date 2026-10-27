"""Executable offline scenarios; no application imports before the guard."""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

from .harness import IsolationViolation, MonitoringHarness, MonitoringRequirementGap

LEGACY = {
    "name": "Saved wristwatch search",
    "query": "fallback merchant query",
    "display_title": "My compact colourful choices",
    "synonym_groups": [["ML05", "ML05B"], ["blue", "mint"]],
    "source_queries": {"cex": ' (ML05 OR "ML05B") -parts  '},
    "sources": [
        {"connector": "cex", "enabled": True, "config": {}},
        {"connector": "scan", "enabled": True, "config": {}},
        {"connector": "not-a-real-source", "enabled": False, "config": {}},
    ],
    "filters": {
        "price_max": "100.00",
        "currency": "GBP",
        "spec_match": {"excluded_title_terms": ["parts"]},
    },
    "schedule": {
        "interval": "30m",
        "timezone": "Europe/London",
        "time_window": {
            "start": "09:00",
            "end": "18:00",
            "days": ["mon", "tue", "wed"],
        },
    },
    "notifications": {
        "events": ["price_drop"],
        "channels": ["webhook", "telegram", "discord"],
        "webhook_url": "https://notify.invalid/hook",
        "telegram_bot_token": "offline-placeholder",
        "telegram_chat_id": "offline-chat",
        "discord_webhook_url": "https://discord.invalid/hook",
    },
    "enabled": True,
}


def listing(harness, source, listing_id, title, price="90.00"):
    from pricerecon.models import NormalizedListing, SourceType

    return NormalizedListing(
        source=source,
        source_type=SourceType.RETAILER,
        source_listing_id=listing_id,
        title_raw=title,
        price=Decimal(price),
        currency="GBP",
        url=f"https://merchant.invalid/{listing_id}",
        timestamp_seen=harness.clock.now,
        in_stock=True,
    )


async def get(client, path):
    response = await client.get(path)
    assert response.status_code == 200, response.text
    return response.json()


async def check(client, watch_id):
    response = await client.post(f"/api/watches/{watch_id}/check")
    assert response.status_code == 200, response.text
    return response.json()["result"]


async def legacy():
    with MonitoringHarness() as harness:
        harness.seed_legacy(
            [
                (7, LEGACY),
                (8, {**LEGACY, "name": "Paused saved search", "enabled": False}),
            ]
        )
        harness.outcomes["cex"] = [
            listing(harness, "cex", "match", "Militado ML05B blue"),
            listing(harness, "cex", "wrong-model", "Militado ML050 blue"),
            listing(harness, "cex", "wrong-dial", "Militado ML05 black"),
            listing(harness, "cex", "parts", "Militado ML05 blue parts"),
            listing(harness, "cex", "over-target", "Militado ML05 blue", "101.00"),
        ]
        async with harness.session() as (client, scheduler):
            saved = await get(client, "/api/watches/7")
            for key in (
                "name",
                "query",
                "display_title",
                "synonym_groups",
                "source_queries",
                "sources",
                "schedule",
                "notifications",
                "enabled",
            ):
                assert saved[key] == LEGACY[key], key
            assert Decimal(saved["filters"]["price_max"]) == Decimal("100.00")
            assert saved["filters"]["spec_match"]["excluded_title_terms"] == ["parts"]
            assert (await get(client, "/api/watches/8"))["enabled"] is False
            assert [job["watch_id"] for job in scheduler.list_watches()] == [7]
            baseline = await check(client, 7)
            assert baseline["first_run"] is True
            assert baseline["notifications_sent"] == 0
            rows = (await get(client, "/api/watches/7/listings"))["items"]
            assert [row["source_listing_id"] for row in rows] == ["match"]
            assert [entry[:2] for entry in harness.searches] == [
                ("cex", ' (ML05 OR "ML05B") -parts  '),
                ("scan", "fallback merchant query"),
            ]
            assert harness.searches[0][2] == {"price_max": Decimal("100.00")}
            assert harness.deliveries == []
            harness.clock.advance()
            harness.outcomes["cex"] = [
                listing(harness, "cex", "match", "Militado ML05B blue", "80.00")
            ]
            # Normal scheduler callback shares the same executor and storage.
            await harness.application.check_watch(7)
            assert (await get(client, "/api/watches/7"))["last_check_at"] == "2026-10-27T13:00:00Z"
            events = (await get(client, "/api/watches/7/events"))["items"]
            assert [event["event_type"] for event in events] == ["price_drop"]
            assert events[0]["timestamp"] == "2026-10-27T13:00:00Z"
            assert [delivery[0] for delivery in harness.deliveries] == [
                "webhook",
                "telegram",
                "discord",
            ]
            webhook = harness.deliveries[0]
            assert webhook[1] == "https://notify.invalid/hook"
            assert webhook[2]["event_type"] == "price_drop"
            assert webhook[2]["listing"]["previous_price"] == 90.0
            assert webhook[2]["listing"]["price"] == Decimal("80.00")
            assert webhook[2]["timestamp"] == "2026-10-27T13:00:00+00:00"
            assert harness.deliveries[1][1] == "offline-chat"
            # UI-style full edit omitting notifications must retain the saved transport settings.
            edited = {**LEGACY, "display_title": "Edited label"}
            edited.pop("notifications")
            response = await client.put("/api/watches/7", json=edited)
            assert response.status_code == 200, response.text
            assert response.json()["notifications"] == LEGACY["notifications"]
            before_restart = await get(client, "/api/watches/7")
            paused_before_restart = await get(client, "/api/watches/8")

        harness.clock.advance()
        searches_before_restart = len(harness.searches)
        async with harness.session() as (client, scheduler):
            await asyncio.sleep(0)
            assert len(harness.searches) == searches_before_restart
            assert await get(client, "/api/watches/7") == before_restart
            assert await get(client, "/api/watches/8") == paused_before_restart
            assert [job["watch_id"] for job in scheduler.list_watches()] == [7]
            unchanged = await check(client, 7)
            assert unchanged["first_run"] is False
            assert unchanged["events"] == []
            assert unchanged["notifications_sent"] == 0
            assert (await get(client, "/api/watches/7/events"))["items"] == events
            assert len(harness.deliveries) == 3
            assert (await get(client, "/api/watches/7/history"))["total"] == 0
            harness.clock.advance()
            harness.outcomes["cex"].append(
                listing(harness, "cex", "new-match", "Militado ML05 mint", "85.00")
            )
            newly_found = await check(client, 7)
            assert [event["type"] for event in newly_found["events"]] == ["new_listing"]
            assert newly_found["notifications_sent"] == 0
            assert len(harness.deliveries) == 3  # Only price drops were selected for delivery.
        assert harness.blocked_edges == []
    print("PASS legacy: saved intent, matching, queries, baseline, drop transports and restart")


async def partial_failure():
    import httpx

    with MonitoringHarness() as harness:
        notifications = {
            **LEGACY["notifications"],
            "events": ["new_listing", "price_drop"],
            "channels": ["webhook"],
        }
        harness.seed_legacy([(7, {**LEGACY, "notifications": notifications})])
        last_good = listing(harness, "scan", "scan-good", "Militado ML05 mint")
        harness.outcomes["scan"] = [last_good]
        harness.outcomes["cex"] = [listing(harness, "cex", "cex-good", "Militado ML05 blue")]
        async with harness.session() as (client, _):
            assert (await check(client, 7))["first_run"] is True
            baseline_rows = (await get(client, "/api/watches/7/listings"))["items"]
            assert len(baseline_rows) == 2
            harness.clock.advance()
            harness.outcomes["scan"] = httpx.ReadTimeout("Controlled source timeout")
            harness.outcomes["cex"] = [
                listing(harness, "cex", "cex-good", "Militado ML05 blue", "80.00")
            ]
            partial = await check(client, 7)
            assert partial["success"] is True
            states = (await get(client, "/api/health"))["connector_states"]
            assert states["scan"]["status"] == "timeout"
            assert states["scan"]["last_error"] == "Controlled source timeout"
            assert states["cex"]["status"] == "ok"
            during_failure = (await get(client, "/api/watches/7/listings"))["items"]
            partial_events = (await get(client, "/api/watches/7/events"))["items"]
            assert [delivery[2]["event_type"] for delivery in harness.deliveries] == ["price_drop"]
        harness.clock.advance()
        harness.outcomes["scan"] = [last_good]
        async with harness.session() as (client, _):
            recovered = await check(client, 7)
            assert (await get(client, "/api/health"))["connector_states"]["scan"]["status"] == "ok"
            assert (await get(client, "/api/watches/7/listings"))["total"] == 2
            assert recovered["first_run"] is False
            # Ticket requirement: failed collection must retain last-good evidence,
            # and restarting/recovering the same listing must not make it new.
            gaps = []
            if [row for row in during_failure if row["source"] == "scan"] != [
                row for row in baseline_rows if row["source"] == "scan"
            ]:
                gaps.append("Failed source lost its last-good listing")
            event_types = sorted(event["event_type"] for event in partial_events)
            if event_types != ["price_drop"]:
                gaps.append(f"Partial failure emitted events {event_types}")
            if recovered["new_listings"] != 0:
                gaps.append(f"Recovery treated {recovered['new_listings']} retained listing as new")
            delivered_events = [delivery[2]["event_type"] for delivery in harness.deliveries]
            if delivered_events != ["price_drop"]:
                gaps.append(f"Recovery caused duplicate notification: {delivered_events}")
        assert harness.blocked_edges == []
        if gaps:
            raise MonitoringRequirementGap("; ".join(gaps))


async def automatic_startup():
    with MonitoringHarness() as harness:
        harness.seed_legacy(
            [
                (7, {**LEGACY, "sources": [{"connector": "cex"}], "schedule": {"interval": "4h"}}),
                (8, {**LEGACY, "name": "Paused", "enabled": False}),
            ]
        )
        async with harness.session(automatic_checks=True) as (client, scheduler):
            await asyncio.wait_for(harness.search_started.wait(), timeout=2)
            assert len(harness.searches) == 1
            assert (await get(client, "/api/watches/7"))["last_check_at"] == "2026-10-27T12:00:00Z"
            assert (await get(client, "/api/watches/8"))["last_check_at"] is None
            assert [job["watch_id"] for job in scheduler.list_watches()] == [7]
            assert harness.deliveries == []
        assert harness.blocked_edges == []
    print("PASS automatic_startup: normal defaults still execute enabled saved searches")


async def simple_query():
    with MonitoringHarness() as harness:
        harness.seed_legacy(
            [
                (
                    7,
                    {
                        "name": "Simple saved search",
                        "query": "Casio blue",
                        "sources": [{"connector": "cex"}],
                        "filters": {"spec_match": {"excluded_title_terms": ["parts"]}},
                        "notifications": {
                            "events": ["price_drop"],
                            "channels": ["webhook"],
                            "webhook_url": "https://notify.invalid/hook",
                        },
                    },
                )
            ]
        )
        harness.outcomes["cex"] = [
            listing(harness, "cex", "matching", "Casio blue wristwatch"),
            listing(harness, "cex", "unrelated", "Unrelated black wristwatch"),
            listing(harness, "cex", "parts", "Casio blue parts"),
        ]
        async with harness.session() as (client, _):
            baseline = await check(client, 7)
            assert baseline["first_run"] is True
            assert harness.searches == [("cex", "Casio blue", {})]
            rows = (await get(client, "/api/watches/7/listings"))["items"]
            if [row["source_listing_id"] for row in rows] != ["matching"]:
                raise MonitoringRequirementGap(
                    "ADR fallback query-title filter admitted unrelated listings: "
                    f"{[row['source_listing_id'] for row in rows]}"
                )


async def schedule_window():
    with MonitoringHarness() as harness:
        harness.seed_legacy(
            [
                (
                    7,
                    {
                        **LEGACY,
                        "sources": [{"connector": "cex"}],
                        "schedule": {
                            "interval": "4h",
                            "timezone": "UTC",
                            "time_window": {
                                "start": "12:00",
                                "end": "12:59",
                                "days": ["tue"],
                            },
                        },
                    },
                )
            ]
        )
        async with harness.session(automatic_checks=True) as (client, _):
            await asyncio.wait_for(harness.search_started.wait(), timeout=0.5)
            assert (await get(client, "/api/watches/7"))["last_check_at"] == "2026-10-27T12:00:00Z"
        harness.clock.advance(hours=2)
        async with harness.session(automatic_checks=True) as (client, scheduler):
            await asyncio.sleep(0.1)
            assert len(harness.searches) == 1, "Out-of-window startup ran a check"
            assert (await get(client, "/api/watches/7"))["last_check_at"] == "2026-10-27T12:00:00Z"
            assert [job["watch_id"] for job in scheduler.list_watches()] == [7]
        assert harness.blocked_edges == []
    print("PASS schedule_window: startup respects saved window and controlled UTC clock")


async def process_restart(*, before):
    with MonitoringHarness(storage_root=Path(sys.argv[2])) as harness:
        if before:
            harness.seed_legacy(
                [
                    (
                        7,
                        {
                            **LEGACY,
                            "sources": [{"connector": "cex"}],
                            "notifications": {**LEGACY["notifications"], "channels": ["webhook"]},
                        },
                    )
                ]
            )
        harness.outcomes["cex"] = [listing(harness, "cex", "saved", "Militado ML05 blue", "80.00")]
        async with harness.session() as (client, scheduler):
            if before:
                harness.outcomes["cex"] = [
                    listing(harness, "cex", "saved", "Militado ML05 blue", "90.00")
                ]
                assert (await check(client, 7))["first_run"] is True
                harness.clock.advance()
                harness.outcomes["cex"] = [
                    listing(harness, "cex", "saved", "Militado ML05 blue", "80.00")
                ]
                assert (await check(client, 7))["notifications_sent"] == 1
                assert len(harness.deliveries) == 1
            else:
                assert (await get(client, "/api/watches/7"))[
                    "last_check_at"
                ] == "2026-10-27T13:00:00Z"
                assert [
                    event["event_type"]
                    for event in (await get(client, "/api/watches/7/events"))["items"]
                ] == ["price_drop"]
                harness.clock.advance(hours=2)
                unchanged = await check(client, 7)
                assert unchanged["first_run"] is False
                assert unchanged["events"] == []
                assert unchanged["notifications_sent"] == 0
                assert harness.deliveries == []
            assert [job["watch_id"] for job in scheduler.list_watches()] == [7]
        assert harness.blocked_edges == []
    print(f"PASS process_restart: {'before' if before else 'after'} cold process")


async def isolation():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, scheduler):
            response = await client.post(
                "/api/watches",
                json={
                    "name": "Offline search",
                    "query": "Casio",
                    "sources": [{"connector": "cex"}],
                    "schedule": {"interval": "1s"},
                },
            )
            assert response.status_code == 201, response.text
            await asyncio.sleep(1.1)
            assert harness.searches == [], "Startup/interval jobs ran without an explicit check"
            watch_id = response.json()["id"]
            checked = await client.post(f"/api/watches/{watch_id}/check")
            assert checked.status_code == 200, checked.text
            assert harness.searches == [("cex", "Casio", {})]
            assert scheduler.list_watches()[0]["watch_id"] == watch_id
        import socket
        import sqlite3
        import subprocess

        import httpx

        assert harness.application.settings.api_key is None
        assert harness.application.settings.database_path == "pricerecon.db"

        for attempt in (
            lambda: sqlite3.connect(harness.root.parent / "must-not-open.db"),
            lambda: socket.getaddrinfo("example.invalid", 443),
            lambda: subprocess.run([sys.executable, "-c", "pass"], check=False),
        ):
            try:
                attempt()
            except IsolationViolation:
                pass
            else:
                raise AssertionError("Isolation guard allowed an unsafe edge")
        try:
            async with httpx.AsyncClient() as real_client:
                await real_client.get("https://must-not-connect.invalid/")
        except IsolationViolation:
            pass
        else:
            raise AssertionError("Isolation guard allowed a real HTTP transport")
        assert harness.blocked_edges == [
            "sqlite3.connect",
            "socket.getaddrinfo",
            "subprocess.Popen",
            "httpx.async_transport",
        ]
        assert harness.deliveries == []
    print("PASS isolation: startup suppressed; explicit API check; DB/network/process guards")


if __name__ == "__main__":
    try:
        asyncio.run(
            {
                "isolation": isolation,
                "legacy": legacy,
                "partial_failure": partial_failure,
                "automatic_startup": automatic_startup,
                "simple_query": simple_query,
                "schedule_window": schedule_window,
                "before_process_restart": lambda: process_restart(before=True),
                "after_process_restart": lambda: process_restart(before=False),
            }[sys.argv[1]]()
        )
    except MonitoringRequirementGap as gap:
        print(f"UNMET_REQUIREMENT: {gap}")
        sys.exit(3)
