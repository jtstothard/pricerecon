"""Executable offline scenarios; no application imports before the guard."""

import asyncio
import json
import sys
from decimal import Decimal
from pathlib import Path

from .harness import IsolationViolation, MonitoringHarness

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


async def legacy(*, operating_envelope=True):
    with MonitoringHarness(operating_envelope=operating_envelope) as harness:
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


async def form_edit():
    payloads = json.load(sys.stdin)
    with MonitoringHarness() as harness:
        harness.seed_legacy(
            [(7, LEGACY), (8, {**LEGACY, "name": "Paused saved search", "enabled": False})]
        )
        harness.outcomes["cex"] = [
            listing(harness, "cex", "match", "Militado ML05B blue"),
            listing(harness, "cex", "parts", "Militado ML05B blue parts"),
        ]
        async with harness.session() as (client, scheduler):
            for watch_id, payload in zip((7, 8), payloads, strict=True):
                before = await get(client, f"/api/watches/{watch_id}")
                response = await client.put(f"/api/watches/{watch_id}", json=payload)
                assert response.status_code == 200, response.text
                after = response.json()
                for key in before.keys() - {"updated_at", "display_title"}:
                    assert after[key] == before[key], f"Watch {watch_id} lost {key}"
                assert after["display_title"] == "Edited label"
            assert [job["watch_id"] for job in scheduler.list_watches()] == [7]
            assert (await check(client, 7))["notifications_sent"] == 0
            rows = (await get(client, "/api/watches/7/listings"))["items"]
            assert [row["source_listing_id"] for row in rows] == ["match"]
            assert [entry[:2] for entry in harness.searches] == [
                ("cex", ' (ML05 OR "ML05B") -parts  '),
                ("scan", "fallback merchant query"),
            ]
            retained = [await get(client, f"/api/watches/{watch_id}") for watch_id in (7, 8)]
        async with harness.session() as (client, scheduler):
            assert [
                await get(client, f"/api/watches/{watch_id}") for watch_id in (7, 8)
            ] == retained
            assert [job["watch_id"] for job in scheduler.list_watches()] == [7]
            assert (await check(client, 7))["events"] == []
            harness.clock.advance()
            harness.outcomes["cex"] = [
                listing(harness, "cex", "match", "Militado ML05B blue", "80.00")
            ]
            assert (await check(client, 7))["notifications_sent"] == 1
            assert [delivery[0] for delivery in harness.deliveries] == [
                "webhook",
                "telegram",
                "discord",
            ]
        assert harness.blocked_edges == []
    print("PASS form_edit: UI payload retains enabled/disabled saved intent, matching and delivery")


async def partial_failure(mode="timeout"):
    import httpx

    failures = {
        "timeout": httpx.ReadTimeout("Controlled source timeout"),
        "unknown_error": RuntimeError("Controlled unexpected error"),
    }

    with MonitoringHarness() as harness:
        from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus

        failures["auth_failed"] = ConnectorDegradedError(
            status=ConnectorStatus.auth_failed,
            message="Controlled authentication failure",
            connector_id="scan",
        )
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
            harness.outcomes["scan"] = failures[mode]
            harness.outcomes["cex"] = [
                listing(harness, "cex", "cex-good", "Militado ML05 blue", "80.00")
            ]
            partial = await check(client, 7)
            assert partial["success"] is True
            states = (await get(client, "/api/health"))["connector_states"]
            assert states["scan"]["status"] == mode
            assert states["scan"]["last_error"] == str(failures[mode])
            assert partial["listings_found"] == 1  # Retained evidence is not a fresh result.
            assert partial["listings_gone"] == 0
            assert states["cex"]["status"] == "ok"
            during_failure = (await get(client, "/api/watches/7/listings"))["items"]
            partial_events = (await get(client, "/api/watches/7/events"))["items"]
            assert [delivery[2]["event_type"] for delivery in harness.deliveries] == ["price_drop"]
            if mode == "auth_failed":
                searches = list(harness.searches)
                skipped = await check(client, 7)
                assert harness.searches[len(searches) :] == [
                    ("cex", LEGACY["source_queries"]["cex"], {"price_max": Decimal("100.00")})
                ]
                assert skipped["listings_gone"] == 0
                assert (await get(client, "/api/watches/7/listings"))["items"] == during_failure
        harness.clock.advance(hours=2)  # Let fresh auth failure expire before retry.
        harness.outcomes["scan"] = [last_good]
        async with harness.session() as (client, _):
            recovered = await check(client, 7)
            assert (await get(client, "/api/health"))["connector_states"]["scan"]["status"] == "ok"
            assert (await get(client, "/api/watches/7/listings"))["total"] == 2
            assert recovered["first_run"] is False
            assert [row for row in during_failure if row["source"] == "scan"] == [
                row for row in baseline_rows if row["source"] == "scan"
            ]
            assert [event["event_type"] for event in partial_events] == ["price_drop"]
            assert recovered["new_listings"] == 0
            assert recovered["events"] == []
            assert recovered["notifications_sent"] == 0
            assert [delivery[2]["event_type"] for delivery in harness.deliveries] == ["price_drop"]
            harness.clock.advance()
            harness.outcomes["scan"] = [
                listing(harness, "scan", "scan-good", "Militado ML05 mint", "75.00")
            ]
            dropped = await check(client, 7)
            assert dropped["price_drops"] == 1
            assert dropped["notifications_sent"] == 1
            assert len(harness.deliveries) == 2
            assert harness.deliveries[-1][2]["listing"]["previous_price"] == 90.0
        assert harness.blocked_edges == []
    print(f"PASS partial_failure: {mode} preserves last-good evidence and silent recovery")


async def successful_empty():
    with MonitoringHarness() as harness:
        harness.seed_legacy([(7, LEGACY)])
        harness.outcomes["scan"] = [listing(harness, "scan", "gone", "Militado ML05 mint")]
        harness.outcomes["cex"] = [listing(harness, "cex", "kept", "Militado ML05 blue")]
        async with harness.session() as (client, _):
            assert (await check(client, 7))["first_run"] is True
            harness.clock.advance()
            harness.outcomes["scan"] = []
            empty = await check(client, 7)
            assert empty["listings_gone"] == 1
            rows = (await get(client, "/api/watches/7/listings"))["items"]
            assert [row["source_listing_id"] for row in rows] == ["kept"]
            events = (await get(client, "/api/watches/7/events"))["items"]
            assert [event["event_type"] for event in events] == ["listing_gone"]
            assert events[0]["data"]["source_listing_id"] == "gone"
            assert (await get(client, "/api/health"))["connector_states"]["scan"]["status"] == "ok"
            assert harness.deliveries == []
        assert harness.blocked_edges == []
    print("PASS successful_empty: empty success removes old evidence and records disappearance")


async def all_sources_failed():
    import httpx

    with MonitoringHarness() as harness:
        harness.seed_legacy([(7, LEGACY)])
        harness.outcomes["cex"] = [listing(harness, "cex", "kept", "Militado ML05 blue")]
        harness.outcomes["scan"] = [listing(harness, "scan", "retained", "Militado ML05 mint")]
        async with harness.session() as (client, _):
            assert (await check(client, 7))["first_run"] is True
            baseline = await get(client, "/api/watches/7/listings")
            harness.clock.advance()
            harness.outcomes["cex"] = httpx.ReadTimeout("Controlled cex timeout")
            harness.outcomes["scan"] = httpx.ReadTimeout("Controlled scan timeout")
            failed = await check(client, 7)
            assert failed["first_run"] is False
            assert failed["listings_found"] == 0
            assert failed["listings_gone"] == 0
            assert await get(client, "/api/watches/7/listings") == baseline
            assert (await get(client, "/api/watches/7/events"))["items"] == []
            assert harness.deliveries == []
        assert harness.blocked_edges == []
    print("PASS all_sources_failed: total acquisition failure preserves the existing baseline")


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
                        "display_title": "A label that is not a title filter",
                        "source_queries": {"cex": "  (Casio OR Seiko) blue -parts  "},
                        "sources": [{"connector": "cex"}, {"connector": "scan"}],
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
            listing(harness, "cex", "one-term", "Casio black wristwatch"),
            listing(harness, "cex", "reordered", "BLUE wristwatch CASIO"),
            listing(harness, "cex", "parts", "Casio blue parts"),
        ]
        async with harness.session() as (client, _):
            baseline = await check(client, 7)
            assert baseline["first_run"] is True
            assert harness.searches == [
                ("cex", "  (Casio OR Seiko) blue -parts  ", {}),
                ("scan", "Casio blue", {}),
            ]
            rows = (await get(client, "/api/watches/7/listings"))["items"]
            assert sorted(row["source_listing_id"] for row in rows) == ["matching", "reordered"]
            assert harness.deliveries == []
        assert harness.blocked_edges == []
    print("PASS simple_query: fallback title terms and exclusions survive raw source override")


async def advanced_query(location="watch"):
    with MonitoringHarness() as harness:
        groups = [["sea gull", "ST19+"], ["38mm"]]
        spec = {"excluded_title_terms": ["parts", "leather strap"]}
        watch = {
            **LEGACY,
            "synonym_groups": groups if location != "spec" else [],
            "filters": {"spec_match": spec},
        }
        if location == "spec":
            spec["synonym_groups"] = groups
        elif location == "defaults":
            watch.pop("filters")  # Watch-level groups apply even with default filters.
        harness.seed_legacy([(7, watch)])
        harness.outcomes["cex"] = [
            listing(harness, "cex", "phrase", "Sea-Gull 38mm watch"),
            listing(harness, "cex", "symbol", "ST19+ 38mm chronograph"),
            listing(harness, "cex", "wrong-model", "ST190 38mm chronograph"),
            listing(harness, "cex", "wrong-size", "ST19+ 138mm clock"),
            listing(harness, "cex", "split-phrase", "Sea mechanical Gull 38mm watch"),
        ]
        if location != "defaults":
            harness.outcomes["cex"] += [
                listing(harness, "cex", "parts", "ST19+ 38mm parts"),
                listing(harness, "cex", "strap", "Sea Gull 38mm leather strap"),
            ]
        async with harness.session() as (client, _):
            assert (await check(client, 7))["first_run"] is True
            assert [entry[:2] for entry in harness.searches] == [
                ("cex", LEGACY["source_queries"]["cex"]),
                ("scan", LEGACY["query"]),
            ]
            rows = (await get(client, "/api/watches/7/listings"))["items"]
            assert sorted(row["source_listing_id"] for row in rows) == ["phrase", "symbol"]
            assert harness.deliveries == []
        assert harness.blocked_edges == []
    print(
        f"PASS advanced_query: {location} groups replace fallback matching with token/phrase rules"
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
                            "notifications": {**LEGACY["notifications"], "channels": ["webhook"]},
                        },
                    )
                ]
            )
        harness.outcomes["scan"] = [listing(harness, "scan", "retained", "Militado ML05 mint")]
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
                import httpx

                harness.outcomes["scan"] = httpx.ReadTimeout("Controlled pre-restart failure")
                assert (await check(client, 7))["notifications_sent"] == 1
                assert (await get(client, "/api/watches/7/listings"))["total"] == 2
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
                assert (await get(client, "/api/watches/7/listings"))["total"] == 2
                assert (await get(client, "/api/health"))["connector_states"]["scan"][
                    "status"
                ] == "ok"
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
        from curl_cffi import Curl
        from curl_cffi.requests import AsyncSession, Session

        from pricerecon.connectors.browser_client import BrowserClient

        assert harness.application.settings.api_key is None
        assert harness.application.settings.database_path == "pricerecon.db"

        for attempt in (
            lambda: sqlite3.connect(harness.root.parent / "must-not-open.db"),
            lambda: socket.getaddrinfo("example.invalid", 443),
            lambda: subprocess.run([sys.executable, "-c", "pass"], check=False),
            lambda: httpx.get("https://must-not-connect.invalid/"),
            lambda: Session().get("https://must-not-connect.invalid/"),
            lambda: Curl().perform(),
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
        async with AsyncSession() as curl_session:
            for attempt in (
                lambda: curl_session.get("https://must-not-connect.invalid/"),
                lambda: BrowserClient().start(),
            ):
                try:
                    await attempt()
                except IsolationViolation:
                    pass
                else:
                    raise AssertionError("Isolation guard allowed native curl/browser I/O")
        assert harness.blocked_edges == [
            "sqlite3.connect",
            "socket.getaddrinfo",
            "subprocess.Popen",
            "httpx.sync_transport",
            "curl_cffi.transport",
            "curl_cffi.transport",
            "httpx.async_transport",
            "curl_cffi.transport",
            "browser.start",
        ]
        assert harness.deliveries == []
    print("PASS isolation: startup suppressed; explicit API check; DB/network/process guards")


if __name__ == "__main__":
    asyncio.run(
        {
            "isolation": isolation,
            "legacy": legacy,
            "form_edit": form_edit,
            "partial_failure": partial_failure,
            "unexpected_failure": lambda: partial_failure("unknown_error"),
            "auth_failure": lambda: partial_failure("auth_failed"),
            "successful_empty": successful_empty,
            "all_sources_failed": all_sources_failed,
            "advanced_query": advanced_query,
            "spec_groups": lambda: advanced_query("spec"),
            "default_groups": lambda: advanced_query("defaults"),
            "automatic_startup": automatic_startup,
            "simple_query": simple_query,
            "schedule_window": schedule_window,
            "before_process_restart": lambda: process_restart(before=True),
            "after_process_restart": lambda: process_restart(before=False),
        }[sys.argv[1]]()
    )
