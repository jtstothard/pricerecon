"""Guarded shared-admission acceptance probes; no merchant or live transport."""

import argparse
import asyncio
import json
from contextvars import Context
from pathlib import Path
from unittest.mock import patch

import httpx

from .collection_workflows import envelope
from .harness import MonitoringHarness
from .workflows import LEGACY, check, get


async def main(case, output, storage=None):
    with MonitoringHarness(storage_root=storage, operating_envelope=False) as harness:
        from pricerecon import connectors
        from pricerecon.core.collection_policy import operating_policy, supplied_policy
        from pricerecon.core.collection_transport import collection_http_client
        from pricerecon.models import SourceType

        sends = []

        def transport(request):
            sends.append(str(request.url))
            if case == "redirect" and request.url.path == "/search":
                return httpx.Response(302, headers={"Location": "/item/one"})
            return httpx.Response(200, json={})

        class HTTPFixture:
            source_role = SourceType.RETAILER
            collection_accounting = "http_v1"

            async def initialize(self):
                self.client = collection_http_client(transport=httpx.MockTransport(transport))

            async def cleanup(self):
                await self.client.aclose()

            async def search(self, query, filters):
                await self.client.get("https://fixture.invalid/search", follow_redirects=True)
                return []

        if case != "process_resume":
            harness.seed_legacy([(7, {**LEGACY, "sources": [{"connector": "cex"}]})])
        policy = envelope(harness, requests=1, reserve=0, spacing=0)
        with patch.object(connectors, "discover_connectors", lambda: {"cex": HTTPFixture}):
            async with harness.session() as (client, scheduler):
                before = await get(client, "/api/watches/7")
                assert supplied_policy() is None
                if case == "legacy_no_grant":
                    await check(client, 7)
                    assert len(sends) == 1
                    expected_sends = 1
                    observed_status = await get(client, "/api/discovery/collection")
                    ledger = observed_status
                elif case == "process_resume":
                    with operating_policy(policy):
                        ledger_before = await get(client, "/api/discovery/collection")
                        assert ledger_before["state"] == "supplied"
                        assert next(u for u in ledger_before["usage"] if u["resource"] == "requests")["used"] == 1
                    assert supplied_policy() is None
                    await check(client, 7)
                    expected_sends = 0
                    observed_status = await get(client, "/api/discovery/collection")
                    with operating_policy(policy):
                        ledger = await get(client, "/api/discovery/collection")
                    assert_denied(ledger_before, ledger, observed_status)
                elif case == "redirect":
                    with operating_policy(policy):
                        result = await check(client, 7)
                        assert result["acquisition_outcomes"][0]["reason"] == "resource_exhausted:requests"
                        ledger = await get(client, "/api/discovery/collection")
                    observed_status = ledger
                    used = {u["resource"]: u["used"] for u in ledger["usage"]}
                    assert (used["requests"], used["pages"], used["details"]) == (1, 1, 0)
                    expected_sends = 1
                else:
                    with operating_policy(policy):
                        if case != "process_resume":
                            first = await check(client, 7)
                            assert first["acquisition_outcomes"][0]["state"] == "success_empty"
                            capped = await check(client, 7)
                            assert capped["acquisition_outcomes"][0]["reason"] == "resource_exhausted:requests"
                            assert len(sends) == 1
                        ledger_before = await get(client, "/api/discovery/collection")
                        assert ledger_before["state"] == "supplied"
                        assert next(u for u in ledger_before["usage"] if u["resource"] == "requests")["used"] == 1
                        expected_sends = len(sends)
                        if case == "process_seed":
                            observed_status = ledger_before
                        else:
                            async def outside_entry():
                                assert supplied_policy() is None
                                if case == "context_scheduler":
                                    job = scheduler.scheduler.get_job("watch_7")
                                    assert job is not None
                                    await job.func(*job.args, **job.kwargs)
                                else:
                                    await check(client, 7)
                                return await get(client, "/api/discovery/collection")

                            # Models an independently established request/job context,
                            # while the supplied grant remains active in this task.
                            observed_status = await asyncio.create_task(
                                outside_entry(), context=Context()
                            )
                        ledger = await get(client, "/api/discovery/collection")
                        if case != "process_seed":
                            assert_denied(ledger_before, ledger, observed_status)
                after = await get(client, "/api/watches/7")
                for key in ("enabled", "query", "source_queries", "sources", "filters", "notifications", "schedule"):
                    assert before[key] == after[key], key
                assert harness.blocked_edges == harness.deliveries == []
                passed = len(sends) == expected_sends
                receipt = {
                    "case": case,
                    "result": "passed" if passed else "failed",
                    "expected_transport_sends": expected_sends,
                    "actual_transport_sends": len(sends),
                    "sends": sends,
                    "outside_status": observed_status,
                    "supplied_ledger": ledger,
                    "operating_policy": policy.model_dump(mode="json"),
                    "temporary_storage": True,
                    "blocked_edges": harness.blocked_edges,
                    "notifications_sent": len(harness.deliveries),
                    "legacy_intent_preserved": True,
                    "activation": "staged",
                }
                output.write_text(json.dumps(receipt, indent=2) + "\n")
                assert passed, "Provider transport ran outside shared exhausted grant without a debit"


def assert_denied(before, after, outside):
    assert outside == after, "Independent callers must see the governing grant and usage"
    assert after["state"] == "supplied"
    assert after["scope_id"] == before["scope_id"]
    old = {u["resource"]: u["used"] for u in before["usage"]}
    new = {u["resource"]: u["used"] for u in after["usage"]}
    assert new == {**old, "elapsed_seconds": old["elapsed_seconds"] + 10}
    assert after["provider_usage"] == before["provider_usage"]
    assert len(after["attempts"]) == len(before["attempts"]) + 1
    assert after["attempts"][0]["state"] == "capped"
    assert after["attempts"][0]["reason"] == "resource_exhausted:requests"
    assert after["attempts"][0]["evidence_state"] == "unrefreshed"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("case", choices=["context_api", "context_scheduler", "process_seed", "process_resume", "legacy_no_grant", "redirect"])
    parser.add_argument("output", type=Path)
    parser.add_argument("--storage", type=Path)
    args = parser.parse_args()
    asyncio.run(main(args.case, args.output.resolve(), args.storage))
