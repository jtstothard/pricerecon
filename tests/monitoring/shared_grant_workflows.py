"""API/execution probes with controlled transport/time and temporary SQLite only."""

import asyncio
import sqlite3
import sys
from contextlib import closing
from contextvars import Context
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import httpx

from .collection_workflows import envelope
from .harness import MonitoringHarness
from .workflows import LEGACY, check, get, listing


async def main(case, storage=None):
    if case.startswith("migration_"):
        await migrated_policy(case)
        return
    if case == "legacy_intent":
        # Run every retained intent/filter/baseline/notification/restart assertion
        # on a genuinely never-configured database, without weakening any check.
        from .workflows import legacy

        await legacy(operating_envelope=False)
        return
    with MonitoringHarness(storage_root=storage, operating_envelope=False) as harness:
        from pricerecon import connectors
        from pricerecon.core.collection_policy import operating_policy
        from pricerecon.core.collection_transport import (
            collection_http_client,
            debit_resources,
            require_bounded_browser,
        )
        from pricerecon.core.rate_limiter import AdmissionDenied
        from pricerecon.models import SourceType

        sends = []

        async def transport(request):
            sends.append(str(request.url))
            await asyncio.sleep(0)
            return httpx.Response(200, json={})

        class HTTPFixture:
            source_role = SourceType.RETAILER
            collection_accounting = "http_v1"

            async def initialize(self):
                self.client = collection_http_client(transport=httpx.MockTransport(transport))

            async def cleanup(self):
                await self.client.aclose()

            async def search(self, query, filters):
                await self.client.get("https://fixture.invalid/search")
                return [listing(harness, "cex", "retained", "Militado ML05B blue", "90.00")]

        if case not in {"zero_resume", "concurrent_resume", "concurrent_inspect"}:
            harness.seed_legacy([(7, {**LEGACY, "sources": [{"connector": "cex"}]})])
        policy = envelope(harness, requests=2 if case == "remaining_none" else 1,
                          reserve=0, spacing=0)
        if case in {"zero_elapsed", "zero_seed", "zero_resume", "zero_requests"}:
            caps = dict(policy.caps)
            caps["requests" if case == "zero_requests" else "elapsed_seconds"] = {
                "limit": 0, "tracking_reserve": 0,
            }
            policy = type(policy).model_validate({**policy.model_dump(), "caps": caps})
        elif case == "zero_provider":
            providers = dict(policy.provider_request_caps)
            providers["cex"] = {"limit": 0, "tracking_reserve": 0}
            policy = type(policy).model_validate({**policy.model_dump(), "provider_request_caps": providers})
        elif case == "expired_first":
            policy = type(policy).model_validate({
                **policy.model_dump(), "starts_at": harness.clock.now - timedelta(hours=2),
                "stops_at": harness.clock.now - timedelta(hours=1),
            })
        with patch.object(connectors, "discover_connectors", lambda: {"cex": HTTPFixture}):
            async with harness.session() as (client, _):
                before = await get(client, "/api/watches/7")

                async def outside():
                    with operating_policy(None):
                        response = await client.post("/api/watches/7/check")
                        assert response.status_code == 200, response.text
                        body = response.json()
                        if body["result"].get("collection_state"):
                            assert body["status"] == body["result"]["collection_state"]
                            assert body["message"] == body["result"]["error"]
                        return body["result"]

                if case == "concurrent_seed":
                    with operating_policy(policy):
                        state = await get(client, "/api/discovery/collection")
                        assert state["scope_id"] == policy.scope_id
                    assert sends == []
                elif case == "concurrent_resume":
                    await outside()
                    assert len(sends) <= 1
                elif case == "concurrent_inspect":
                    state = await get(client, "/api/discovery/collection")
                    assert usage(state)["requests"] == 1
                    assert state["provider_usage"][0]["used"] == 1
                    assert len(state["attempts"]) == 2
                    assert any(a["state"] == "capped" for a in state["attempts"])
                    assert any(a["state"] == "success" for a in state["attempts"])
                elif case == "zero_resume":
                    result = await outside()
                    assert result["acquisition_outcomes"][0]["reason"] == "resource_exhausted:elapsed_seconds"
                    assert sends == []
                    state = await get(client, "/api/discovery/collection")
                    assert state["scope_id"] == policy.scope_id
                    assert len(state["attempts"]) == 2
                    assert usage(state)["elapsed_seconds"] == 0
                elif case == "concurrent_none":
                    with operating_policy(policy):
                        await get(client, "/api/discovery/collection")
                    await asyncio.gather(*[
                        asyncio.create_task(outside(), context=Context()) for _ in range(2)
                    ])
                    assert len(sends) == 1
                    state = await get(client, "/api/discovery/collection")
                    assert usage(state)["requests"] == 1
                    assert len(state["attempts"]) == 2
                    assert any(a["state"] == "capped" for a in state["attempts"])
                else:
                    with operating_policy(policy):
                        first = await check(client, 7)
                    if case.startswith("zero_") or case == "expired_first":
                        assert sends == []
                        expected_state = "blocked" if case == "expired_first" else "capped"
                        assert first["acquisition_outcomes"][0]["state"] == expected_state
                        if case == "zero_seed":
                            assert harness.deliveries == harness.blocked_edges == []
                            return
                        second = await outside()
                        assert second["acquisition_outcomes"][0]["state"] == expected_state
                        assert sends == []
                        state = await get(client, "/api/discovery/collection")
                        assert state["scope_id"] == policy.scope_id
                        assert len(state["attempts"]) == 2
                        assert usage(state)["requests"] == 0
                        if case == "expired_first":
                            assert state["state"] == "expired"
                            assert state["gates"][0] == "operating_policy_expired"
                    else:
                        assert len(sends) == 1
                        old_rows = await get(client, "/api/watches/7/listings")
                        last_check = (await get(client, "/api/watches/7"))["last_check_at"]
                        assert old_rows["items"][0]["source_listing_id"] == "retained"
                        if case == "remaining_none":
                            await outside()
                            denied = await outside()
                            assert len(sends) == 2
                            assert denied["acquisition_outcomes"][0]["reason"] == "resource_exhausted:requests"
                            state = await get(client, "/api/discovery/collection")
                            assert usage(state)["requests"] == 2
                            assert usage(state)["storage_bytes"] > 0
                            assert state["provider_usage"][0]["used"] == 2
                        elif case == "transport":
                            async with collection_http_client(transport=httpx.MockTransport(transport)) as edge:
                                try:
                                    await edge.get("https://fixture.invalid/search")
                                except AdmissionDenied as exc:
                                    assert exc.reason == "collection_attempt_required"
                                else:
                                    raise AssertionError("Transport without an admitted run sent")
                            for operation in (lambda: debit_resources(ai_calls=1), require_bounded_browser):
                                try:
                                    operation()
                                except AdmissionDenied as exc:
                                    assert exc.state == "blocked"
                                else:
                                    raise AssertionError("Unadmitted resource work was allowed")
                        else:
                            expected = "operating_policy_expired"
                            if case == "expired":
                                harness.clock.advance(hours=25)
                            elif case == "scope_change":
                                changed = type(policy).model_validate({
                                    **policy.model_dump(), "scope_id": "new-scope-cannot-refill",
                                    "version": "different", "caps": envelope(harness).caps,
                                })
                                with operating_policy(changed):
                                    result = await check(client, 7)
                                    state = await get(client, "/api/discovery/collection")
                                expected = "operating_policy_changed"
                                assert state["scope_id"] == policy.scope_id
                                assert usage(state)["requests"] == 1
                            else:
                                # Prepare damaged/old persisted-policy fixtures, never
                                # fabricate usage or mutate admission to make a pass.
                                with closing(sqlite3.connect(harness.database)) as conn, conn:
                                    if case == "missing":
                                        conn.execute("DELETE FROM collection_policies")
                                    elif case == "invalid":
                                        conn.execute("UPDATE collection_policies SET payload_json='{}'")
                                    else:
                                        other = type(policy).model_validate({**policy.model_dump(), "scope_id": "ambiguous"})
                                        conn.execute("INSERT INTO collection_policies VALUES (?,?)", (other.scope_id, other.model_dump_json()))
                                expected = {"missing": "operating_policy_required", "invalid": "operating_policy_invalid", "ambiguous": "operating_policy_ambiguous"}[case]
                            if case != "scope_change":
                                result = await outside()
                                state = await get(client, "/api/discovery/collection")
                            assert expected in state["gates"]
                            assert result["acquisition_outcomes"][0]["reason"] == expected
                            assert state["state"] == ("expired" if case == "expired" else "blocked")
                            assert len(sends) == 1
                            assert await get(client, "/api/watches/7/listings") == old_rows
                            assert (await get(client, "/api/watches/7"))["last_check_at"] == last_check
                            # Discovery uses the same durable selection even
                            # when no caller supplies an operating context.
                            from pricerecon.core.discovery import execute_discovery
                            from pricerecon.models.discovery import (
                                DiscoveryAdmission,
                                DiscoveryRequest,
                            )

                            old_feed = await get(client, "/api/discovery/watches")
                            capture = await execute_discovery(
                                DiscoveryRequest(query="watch", sources=[{"connector": "cex"}]),
                                admission=DiscoveryAdmission(
                                    mode="offline_verification", policy_reference="fixture",
                                    permission_reference="fixture", activation_reference="isolated",
                                ),
                            )
                            # Outside the deliberately mismatched supplied context,
                            # scope_change resolves the original exhausted grant.
                            assert capture.outcomes[0].reason == (
                                "resource_exhausted:requests" if case == "scope_change" else expected
                            )
                            assert len(sends) == 1
                            new_feed = await get(client, "/api/discovery/watches")
                            if case == "scope_change":
                                assert {**new_feed, "captures": old_feed["captures"]} == old_feed
                                assert len(new_feed["captures"]) == len(old_feed["captures"]) + 1
                                assert new_feed["captures"][0]["outcomes"][0]["reason"] == "resource_exhausted:requests"
                            else:
                                assert new_feed == old_feed
                            assert harness.deliveries == []
                after = await get(client, "/api/watches/7")
                for key in ("enabled", "query", "source_queries", "sources", "filters", "notifications", "schedule"):
                    assert before[key] == after[key], key
                assert harness.deliveries == harness.blocked_edges == []
        print(f"PASS {case}: sends={len(sends)}, intent retained, no live edges or notifications")


def usage(state):
    return {entry["resource"]: entry["used"] for entry in state["usage"]}


async def migrated_policy(case):
    with MonitoringHarness(operating_envelope=False) as harness:
        from pricerecon.core.collection_policy import operating_policy

        harness.seed_legacy([(7, {**LEGACY, "sources": [{"connector": "cex"}]})])
        policy = envelope(harness, requests=1, reserve=0, spacing=0)
        async with harness.session() as (client, _):
            with operating_policy(policy):
                await check(client, 7)
                before = await get(client, "/api/discovery/collection")
            intent = await get(client, "/api/watches/7")
        # Prepare the retained pre-2.1 schema, without changing usage/attempts.
        # App startup owns the actual migration and all observations use its API.
        with closing(sqlite3.connect(harness.database)) as connection, connection:
            connection.execute("DROP TABLE collection_policy_selection")
            connection.execute("DELETE FROM schema_migrations WHERE version='2.1'")
            if case == "migration_ambiguous":
                other = type(policy).model_validate({**policy.model_dump(), "scope_id": "old-second-grant"})
                connection.execute("INSERT INTO collection_policies VALUES (?,?)", (other.scope_id, other.model_dump_json()))
        async with harness.session() as (client, _):
            result = await check(client, 7)
            state = await get(client, "/api/discovery/collection")
            assert len(harness.searches) == 1
            assert await get(client, "/api/watches/7") == intent
            if case == "migration_single":
                assert state["scope_id"] == policy.scope_id
                assert state["provider_usage"] == before["provider_usage"]
                assert usage(state)["requests"] == 1
                assert len(state["attempts"]) == 2
                assert result["acquisition_outcomes"][0]["reason"] == "resource_exhausted:requests"
            else:
                assert state["state"] == "blocked"
                assert "operating_policy_ambiguous" in state["gates"]
                assert state["attempts"] == before["attempts"]
                assert result["acquisition_outcomes"][0]["reason"] == "operating_policy_ambiguous"
            assert harness.deliveries == harness.blocked_edges == []


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], Path(sys.argv[2]) if len(sys.argv) > 2 else None))
