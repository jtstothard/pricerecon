"""Finite synthetic envelopes only; no production policy or merchant acquisition."""

import asyncio
import sys

from .harness import MonitoringHarness
from .workflows import get


async def missing_policy():
    with MonitoringHarness(operating_envelope=False) as harness:
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest

        async with harness.session() as (client, _):
            capture = await execute_discovery(
                DiscoveryRequest(query="watch", sources=[{"connector": "cex"}]),
                admission=DiscoveryAdmission(
                    mode="offline_verification",
                    policy_reference="labels-are-not-budgets",
                    permission_reference="fixtures",
                    activation_reference="isolated",
                ),
            )
            assert capture.outcomes[0].state == "blocked"
            assert capture.outcomes[0].reason == "operating_policy_required"
            assert harness.searches == []
            state = await get(client, "/api/discovery/collection")
            assert state["state"] == "blocked"
            assert "operating_policy_required" in state["gates"]
            assert state["activation"] == "staged"
            assert harness.deliveries == harness.blocked_edges == []


def envelope(harness, *, requests=3, reserve=1, spacing=1, **changes):
    from datetime import timedelta

    from pricerecon.models.collection import OperatingPolicy

    values = {
        "scope_id": "synthetic-finite-study",
        "version": "fixture-v1",
        "owner_reference": "test-only",
        "permission_reference": "original-fixtures",
        "retention_reference": "temporary-test-directory",
        "starts_at": harness.clock.now,
        "stops_at": harness.clock.now + timedelta(hours=24),
        "provider_request_caps": {
            source: {"limit": requests, "tracking_reserve": reserve}
            for source in ("cex", "scan", "ebay", "amazon_uk")
        },
        "recovery_spacing_seconds": spacing,
        "run_timeout_seconds": 10,
        "caps": {
            resource: {"limit": limit, "tracking_reserve": held}
            for resource, limit, held in (
                ("requests", requests, reserve),
                ("pages", 20, 1),
                ("details", 20, 1),
                ("retries", 20, 1),
                ("fallbacks", 20, 1),
                ("storage_bytes", 10_000_000, 100_000),
                ("elapsed_seconds", 1000, 100),
            )
        },
    }
    values.update(changes)
    return OperatingPolicy.model_validate(values)


async def shared_priority():
    with MonitoringHarness(operating_envelope=False) as harness:
        from pricerecon.core.collection_policy import operating_policy
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.core.watch_executor import execute_watch
        from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest

        from .workflows import LEGACY, listing

        harness.seed_legacy([(7, LEGACY)])
        harness.outcomes["cex"] = [listing(harness, "cex", "mint", "ML05 mint watch")]
        async with harness.session() as (client, _):
            before = await get(client, "/api/watches/7")
            with operating_policy(envelope(harness)):
                admission = DiscoveryAdmission(
                    mode="offline_verification",
                    policy_reference="test",
                    permission_reference="fixtures",
                    activation_reference="isolated",
                )
                request = DiscoveryRequest(query="watch", sources=[{"connector": "cex"}])
                first = await execute_discovery(request, admission=admission)
                assert first.outcomes[0].state == "success"
                harness.clock.advance(hours=0.01)
                second = await execute_discovery(request, admission=admission)
                assert second.outcomes[0].state == "success"
                harness.clock.advance(hours=0.01)
                third = await execute_discovery(request, admission=admission)
                assert third.outcomes[0].state == "capped"
                assert third.outcomes[0].reason == "tracking_capacity_reserved:requests"
                result = await execute_watch(7)
                assert result["acquisition_outcomes"][0]["state"] == "success"
                harness.clock.advance(hours=0.01)
                result = await execute_watch(7)
                assert result["acquisition_outcomes"][0]["state"] == "capped"
                status = await get(client, "/api/discovery/collection")
                assert next(u for u in status["usage"] if u["resource"] == "requests")["used"] == 3
                assert len(harness.searches) == 3
                assert (
                    next(a for a in status["attempts"] if a["source"] == "cex")[
                        "last_good_age_seconds"
                    ]
                    == 36
                )
                assert status["attempts"][0]["evidence_state"] == "unrefreshed"
                assert len((await get(client, "/api/discovery/watches"))["candidates"]) == 1
                after = await get(client, "/api/watches/7")
                for key in (
                    "enabled",
                    "query",
                    "source_queries",
                    "filters",
                    "schedule",
                    "notifications",
                ):
                    assert before[key] == after[key]
                assert harness.deliveries == harness.blocked_edges == []


async def real_attempts():
    from unittest.mock import patch

    import httpx

    with MonitoringHarness(operating_envelope=False) as harness:
        from pricerecon import connectors
        from pricerecon.connectors import ebay
        from pricerecon.core import collection_transport
        from pricerecon.core.collection_policy import operating_policy
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest

        sent = []

        def transport(request):
            sent.append(str(request.url))
            if "oauth2" in request.url.path:
                return httpx.Response(
                    200,
                    json={
                        "access_token": "synthetic-token",
                        "token_type": "Bearer",
                        "expires_in": 7200,
                    },
                )
            return httpx.Response(401, json={})

        factory = collection_transport.collection_http_client
        with (
            patch.object(connectors, "discover_connectors", lambda: {"ebay": ebay.eBayConnector}),
            patch.object(
                ebay,
                "collection_http_client",
                lambda **kw: factory(transport=httpx.MockTransport(transport), **kw),
            ),
        ):
            async with harness.session() as (client, _):
                # 401 -> auth retry is itself charged. Fourth send cannot bypass
                # the three-request shared ceiling or zero retry grant.
                policy = envelope(harness, requests=3, reserve=0)
                caps = dict(policy.caps)
                caps["retries"] = {"limit": 0, "tracking_reserve": 0}
                policy = type(policy).model_validate({**policy.model_dump(), "caps": caps})
                with operating_policy(policy):
                    result = await execute_discovery(
                        DiscoveryRequest(
                            query="watch",
                            sources=[
                                {
                                    "connector": "ebay",
                                    "config": {"app_id": "fictional", "cert_id": "fictional"},
                                }
                            ],
                        ),
                        admission=DiscoveryAdmission(
                            mode="offline_verification",
                            policy_reference="synthetic",
                            permission_reference="fixtures",
                            activation_reference="isolated",
                        ),
                    )
                    assert result.outcomes[0].state == "capped", result
                    assert len(sent) == 2, sent
                    assert result.outcomes[0].reason == "resource_exhausted:retries"
                    status = await get(client, "/api/discovery/collection")
                    used = {u["resource"]: u["used"] for u in status["usage"]}
                    assert used["requests"] == 2
                    assert used["pages"] == 1
                    assert used["retries"] == 0
                    assert status["attempts"][0]["state"] == "capped"
                    assert harness.deliveries == harness.blocked_edges == []


async def storage_exhaustion():
    with MonitoringHarness(operating_envelope=False) as harness:
        from pricerecon.core.collection_policy import operating_policy
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest

        from .workflows import listing

        harness.outcomes["cex"] = [listing(harness, "cex", "mint", "Synthetic mint watch")]
        async with harness.session() as (client, _):
            policy = envelope(harness)
            caps = dict(policy.caps)
            caps["storage_bytes"] = {"limit": 0, "tracking_reserve": 0}
            policy = type(policy).model_validate({**policy.model_dump(), "caps": caps})
            with operating_policy(policy):
                result = await execute_discovery(
                    DiscoveryRequest(query="watch", sources=[{"connector": "cex"}]),
                    admission=DiscoveryAdmission(
                        mode="offline_verification",
                        policy_reference="fixture",
                        permission_reference="fixture",
                        activation_reference="isolated",
                    ),
                )
                assert result.outcomes[0].state == "capped"
                assert result.outcomes[0].reason == "resource_exhausted:storage_bytes"
                feed = await get(client, "/api/discovery/watches")
                assert feed["candidates"] == []
                status = await get(client, "/api/discovery/collection")
                assert status["attempts"][0]["state"] == "capped"
                assert status["attempts"][0]["last_good_at"] is None
                assert harness.deliveries == harness.blocked_edges == []


async def verification_priority():
    from unittest.mock import patch

    with MonitoringHarness(operating_envelope=False) as harness:
        from pricerecon.core import notifications
        from pricerecon.core.collection_policy import operating_policy

        from .tracking_workflows import capture, priced_report, track

        async with harness.session() as (client, _):
            with operating_policy(envelope(harness, requests=3, reserve=2)):
                _, feed = await capture(harness, client, priced_report(harness, "68.00"))
                await track(client, feed["candidates"][0], notifications={"channels": ["webhook"]})
                harness.clock.advance(hours=0.01)
                await capture(harness, client, priced_report(harness, "68.00"))
                harness.clock.advance(hours=0.01)
                with patch.object(
                    notifications,
                    "get_global_notification_config",
                    lambda: {"webhook_url": "https://synthetic.invalid/capture"},
                ):
                    result, feed = await capture(harness, client, priced_report(harness, "48.00"))
                assert result.outcomes[0].state == "success", result
                assert len(harness.deliveries) == 1
                assert feed["tracking"][0]["assessment"]["state"] == "eligible"
                status = await get(client, "/api/discovery/collection")
                assert status["attempts"][0]["purpose"] == "verification"
                assert harness.blocked_edges == []


async def restart_before():
    import os
    from pathlib import Path
    from unittest.mock import patch

    import httpx

    with MonitoringHarness(storage_root=Path(sys.argv[2]), operating_envelope=False) as harness:
        from pricerecon import connectors
        from pricerecon.core.collection_policy import operating_policy
        from pricerecon.core.collection_transport import collection_http_client
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models import SourceType
        from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest

        class InterruptedHTTP:
            source_role = SourceType.RETAILER
            collection_accounting = "http_v1"

            async def initialize(self):
                pass

            async def cleanup(self):
                pass

            async def search(self, query, filters):
                def interrupted_send(request):
                    os._exit(0)  # actual pre-send debit survives a killed process

                async with collection_http_client(
                    transport=httpx.MockTransport(interrupted_send)
                ) as client:
                    await client.get("https://fixture.invalid/search")
                return []

        with patch.object(connectors, "discover_connectors", lambda: {"cex": InterruptedHTTP}):
            async with harness.session():
                with operating_policy(envelope(harness, requests=2, reserve=0)):
                    await execute_discovery(
                        DiscoveryRequest(query="watch", sources=[{"connector": "cex"}]),
                        admission=DiscoveryAdmission(
                            mode="offline_verification",
                            policy_reference="fixture",
                            permission_reference="fixture",
                            activation_reference="isolated",
                        ),
                    )
        raise AssertionError("The process was expected to stop at its controlled transport")


async def restart_after():
    from pathlib import Path

    with MonitoringHarness(storage_root=Path(sys.argv[2]), operating_envelope=False) as harness:
        from pricerecon.core.collection_policy import operating_policy
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest

        async with harness.session() as (client, _):
            policy = envelope(harness, requests=2, reserve=0)
            request = DiscoveryRequest(query="watch", sources=[{"connector": "cex"}])
            admission = DiscoveryAdmission(
                mode="offline_verification",
                policy_reference="fixture",
                permission_reference="fixture",
                activation_reference="isolated",
            )
            with operating_policy(policy):
                blocked = await execute_discovery(request, admission=admission)
                assert blocked.outcomes[0].reason == "recovery_spacing"
                assert harness.searches == []
                harness.clock.advance(hours=1)
                resumed = await execute_discovery(request, admission=admission)
                assert resumed.outcomes[0].state == "success_empty"
                again = await execute_discovery(request, admission=admission)
                assert again.outcomes[0].reason == "recovery_spacing"
                harness.clock.advance(hours=1)
                exhausted = await execute_discovery(request, admission=admission)
                assert exhausted.outcomes[0].reason == "resource_exhausted:requests"
                state = await get(client, "/api/discovery/collection")
                assert next(u for u in state["usage"] if u["resource"] == "requests")["used"] == 2
                assert any(a["state"] == "interrupted" for a in state["attempts"])
                assert len(harness.searches) == 1
                # Changing a version label in the same envelope cannot reset usage.
                changed = type(policy).model_validate({**policy.model_dump(), "version": "changed"})
                with operating_policy(changed):
                    result = await execute_discovery(request, admission=admission)
                    assert result.outcomes[0].reason == "operating_policy_changed"
                assert harness.deliveries == harness.blocked_edges == []


async def concurrent():
    from unittest.mock import patch

    import httpx

    with MonitoringHarness(operating_envelope=False) as harness:
        from pricerecon import connectors
        from pricerecon.core.collection_policy import operating_policy
        from pricerecon.core.collection_transport import collection_http_client
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models import SourceType
        from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest

        sends = []
        entered = asyncio.Event()
        release = asyncio.Event()

        async def transport(request):
            sends.append(str(request.url))
            entered.set()
            await release.wait()
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
                return []

        with patch.object(
            connectors, "discover_connectors", lambda: {"cex": HTTPFixture, "scan": HTTPFixture}
        ):
            async with harness.session() as (client, _):
                with operating_policy(envelope(harness, requests=1, reserve=0)):
                    admission = DiscoveryAdmission(
                        mode="offline_verification",
                        policy_reference="fixture",
                        permission_reference="fixture",
                        activation_reference="isolated",
                    )
                    first = asyncio.create_task(
                        execute_discovery(
                            DiscoveryRequest(query="watch", sources=[{"connector": "cex"}]),
                            admission=admission,
                        )
                    )
                    await asyncio.wait_for(entered.wait(), timeout=1)
                    same = await execute_discovery(
                        DiscoveryRequest(query="watch", sources=[{"connector": "cex"}]),
                        admission=admission,
                    )
                    other = await execute_discovery(
                        DiscoveryRequest(query="watch", sources=[{"connector": "scan"}]),
                        admission=admission,
                    )
                    assert same.outcomes[0].reason == "recovery_spacing"
                    assert other.outcomes[0].reason == "resource_exhausted:requests"
                    release.set()
                    assert (await first).outcomes[0].state == "success_empty"
                    status = await get(client, "/api/discovery/collection")
                    assert (
                        next(u for u in status["usage"] if u["resource"] == "requests")["used"] == 1
                    )
                    assert len(sends) == 1
                    assert harness.deliveries == harness.blocked_edges == []


async def legacy_storage():
    with MonitoringHarness(operating_envelope=False) as harness:
        from pricerecon.core.collection_policy import operating_policy
        from pricerecon.core.watch_executor import execute_watch

        from .workflows import LEGACY, listing

        harness.seed_legacy([(7, LEGACY)])
        harness.outcomes["cex"] = [listing(harness, "cex", "mint", "ML05 mint watch")]
        async with harness.session() as (client, _):
            policy = envelope(harness, requests=5, reserve=0)
            caps = dict(policy.caps)
            caps["storage_bytes"] = {"limit": 0, "tracking_reserve": 0}
            policy = type(policy).model_validate({**policy.model_dump(), "caps": caps})
            with operating_policy(policy):
                result = await execute_watch(7)
                assert result["success"] is False
                assert (
                    result["acquisition_outcomes"][0]["reason"]
                    == "resource_exhausted:storage_bytes"
                )
                assert (await get(client, "/api/watches/7/listings"))["items"] == []
                assert (await get(client, "/api/watches/7/events"))["items"] == []
                assert harness.deliveries == harness.blocked_edges == []


async def fallback_detail():
    from unittest.mock import patch

    import httpx

    with MonitoringHarness(operating_envelope=False) as harness:
        from pricerecon import connectors
        from pricerecon.core.collection_policy import operating_policy
        from pricerecon.core.collection_transport import collection_http_client
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models import SourceType
        from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest

        sends = []

        def transport(request):
            sends.append(str(request.url))
            return httpx.Response(200, json={})

        class FallbackFixture:
            collection_accounting = "http_v1"
            source_role = SourceType.RETAILER

            async def initialize(self):
                self.client = collection_http_client(transport=httpx.MockTransport(transport))

            async def cleanup(self):
                await self.client.aclose()

            async def search(self, query, filters):
                await self.client.get("https://fixture.invalid/search")
                await self.client.get("https://fixture.invalid/item/one")
                await self.client.get(
                    "https://fixture.invalid/item/two", extensions={"collection_fallback": True}
                )
                return []

        with patch.object(connectors, "discover_connectors", lambda: {"cex": FallbackFixture}):
            async with harness.session() as (client, _):
                policy = envelope(harness, requests=5, reserve=0)
                caps = dict(policy.caps)
                caps["fallbacks"] = {"limit": 0, "tracking_reserve": 0}
                policy = type(policy).model_validate({**policy.model_dump(), "caps": caps})
                with operating_policy(policy):
                    result = await execute_discovery(
                        DiscoveryRequest(query="watch", sources=[{"connector": "cex"}]),
                        admission=DiscoveryAdmission(
                            mode="offline_verification",
                            policy_reference="fixture",
                            permission_reference="fixture",
                            activation_reference="isolated",
                        ),
                    )
                    assert result.outcomes[0].reason == "resource_exhausted:fallbacks"
                    assert len(sends) == 2
                    used = {
                        u["resource"]: u["used"]
                        for u in (await get(client, "/api/discovery/collection"))["usage"]
                    }
                    assert (
                        used["requests"],
                        used["pages"],
                        used["details"],
                        used["fallbacks"],
                    ) == (2, 1, 1, 0)
                    assert harness.deliveries == harness.blocked_edges == []


async def target_storage_readback():
    with MonitoringHarness(operating_envelope=False) as harness:
        from pricerecon.core.collection_policy import operating_policy

        from .tracking_workflows import capture, priced_report, track

        async with harness.session() as (client, _):
            initial = envelope(harness, requests=10, reserve=0)
            with operating_policy(initial):
                _, feed = await capture(harness, client, priced_report(harness, "68.00"))
                saved = await track(client, feed["candidates"][0])
                harness.clock.advance(hours=0.01)
                await capture(harness, client, priced_report(harness, "68.00"))
                assert (await get(client, f"/api/discovery/tracking/{saved['id']}"))["assessment"][
                    "state"
                ] == "above_target"
            harness.clock.advance(hours=0.01)
            caps = dict(initial.caps)
            caps["storage_bytes"] = {"limit": 0, "tracking_reserve": 0}
            limited = type(initial).model_validate(
                {
                    **initial.model_dump(),
                    "scope_id": "explicit-second-synthetic-grant",
                    "caps": caps,
                }
            )
            with operating_policy(limited):
                result, _ = await capture(harness, client, priced_report(harness, "48.00"))
                assert result.outcomes[0].state == "capped"
                current = await get(client, f"/api/discovery/tracking/{saved['id']}")
                assert current["assessment"]["state"] == "withheld"
                assert "source_refresh_unavailable" in current["assessment"]["reasons"]
                assert harness.deliveries == harness.blocked_edges == []


async def optional_resources():
    from unittest.mock import patch

    import httpx

    with MonitoringHarness(operating_envelope=False) as harness:
        from pricerecon import connectors
        from pricerecon.connectors.external_browser import ExternalBrowserAdapter
        from pricerecon.core.collection_policy import operating_policy
        from pricerecon.core.collection_transport import collection_http_client, debit_resources
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models import SourceType
        from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest

        sends = []

        async def transport(request):
            sends.append(str(request.url))
            await asyncio.sleep(5)
            return httpx.Response(200, json={})

        class ResourceFixture:
            collection_accounting = "http_v1"
            source_role = SourceType.RETAILER

            async def initialize(self):
                self.client = collection_http_client(transport=httpx.MockTransport(transport))

            async def cleanup(self):
                await self.client.aclose()

            async def search(self, query, filters):
                if query == "ai":
                    debit_resources(ai_calls=1, ai_tokens=5)
                elif query == "browser":
                    adapter = ExternalBrowserAdapter.from_config(
                        {
                            "browser_backends": {
                                "fixture": {
                                    "type": "cloakbrowser",
                                    "endpoint": "http://fixture.invalid",
                                }
                            },
                            "browser_default": "fixture",
                        },
                        client_factory=lambda **kw: httpx.AsyncClient(
                            transport=httpx.MockTransport(transport), **kw
                        ),
                    )
                    await adapter.navigate("https://merchant.invalid/")
                else:
                    await self.client.get("https://fixture.invalid/search")
                raise AssertionError("Gated work must not complete")

        with patch.object(connectors, "discover_connectors", lambda: {"cex": ResourceFixture}):
            async with harness.session() as (client, _):
                policy = envelope(harness, run_timeout_seconds=1)
                with operating_policy(policy):
                    admission = DiscoveryAdmission(
                        mode="offline_verification",
                        policy_reference="fixture",
                        permission_reference="fixture",
                        activation_reference="isolated",
                    )
                    for query, state, reason in (
                        ("ai", "blocked", "resource_policy_required:ai_calls"),
                        ("browser", "blocked", "browser_origin_accounting_unavailable"),
                        ("slow", "failed", "run_timeout"),
                    ):
                        result = await execute_discovery(
                            DiscoveryRequest(query=query, sources=[{"connector": "cex"}]),
                            admission=admission,
                        )
                        assert (result.outcomes[0].state, result.outcomes[0].reason) == (
                            state,
                            reason,
                        ), result
                        harness.clock.advance(hours=0.01)
                    assert len(sends) == 1
                    assert (await get(client, "/api/discovery/watches"))["candidates"] == []
                    assert harness.deliveries == harness.blocked_edges == []


if __name__ == "__main__":
    asyncio.run(globals()[sys.argv[1]]())
