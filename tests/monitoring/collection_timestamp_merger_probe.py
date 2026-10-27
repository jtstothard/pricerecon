"""Offline acceptance of denied Watch status and retained evidence timestamps."""

import argparse
import asyncio
import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import httpx

from .collection_workflows import envelope
from .harness import MonitoringHarness
from .workflows import LEGACY, get, listing


async def main(case, output, entrypoint="api"):
    with MonitoringHarness(operating_envelope=False) as harness:
        from pricerecon import connectors
        from pricerecon.core.collection_policy import operating_policy
        from pricerecon.core.collection_transport import collection_http_client
        from pricerecon.models import SourceType

        sends = []

        def transport(request):
            sends.append(str(request.url))
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

        harness.seed_legacy([(7, {**LEGACY, "sources": [{"connector": "cex"}]})])
        policy = envelope(harness, requests=1, reserve=0, spacing=0)
        if case == "zero_elapsed":
            caps = dict(policy.caps)
            caps["elapsed_seconds"] = {"limit": 0, "tracking_reserve": 0}
            policy = type(policy).model_validate({**policy.model_dump(), "caps": caps})
        elif case == "zero_provider":
            caps = dict(policy.provider_request_caps)
            caps["cex"] = {"limit": 0, "tracking_reserve": 0}
            policy = type(policy).model_validate({**policy.model_dump(), "provider_request_caps": caps})

        expected_reason = {
            "request_cap": "resource_exhausted:requests",
            "zero_elapsed": "resource_exhausted:elapsed_seconds",
            "zero_provider": "provider_requests_exhausted:cex",
            "expired": "operating_policy_expired",
        }[case]
        expected_state = "blocked" if case == "expired" else "capped"
        with patch.object(connectors, "discover_connectors", lambda: {"cex": HTTPFixture}):
            async with harness.session() as (client, _):
                with operating_policy(policy):
                    if case in {"request_cap", "expired"}:
                        first = await client.post("/api/watches/7/check")
                        assert first.status_code == 200
                        assert first.json()["result"]["acquisition_outcomes"][0]["state"] == "success"
                    else:
                        await get(client, "/api/discovery/collection")
                before = await get(client, "/api/watches/7")
                rows_before = await get(client, "/api/watches/7/listings")
                sends_before = len(sends)
                harness.clock.advance(hours=25 if case == "expired" else 1)
                scheduler_log = StringIO()
                with operating_policy(None):
                    if entrypoint == "scheduler":
                        with redirect_stdout(scheduler_log):
                            await harness.application.check_watch(7)
                        body = None
                    else:
                        response = await client.post("/api/watches/7/check")
                        assert response.status_code == 200, response.text
                        body = response.json()
                after = await get(client, "/api/watches/7")
                rows_after = await get(client, "/api/watches/7/listings")
                ledger = await get(client, "/api/discovery/collection")
                assert len(sends) == sends_before
                if body is not None:
                    assert body["result"]["acquisition_outcomes"][0]["reason"] == expected_reason
                assert rows_before == rows_after
                assert harness.deliveries == harness.blocked_edges == []
                for key in ("enabled", "query", "source_queries", "sources", "filters", "notifications", "schedule"):
                    assert before[key] == after[key], key
                failures = []
                if body is not None and body["status"] != expected_state:
                    failures.append(f"denied Watch status is {body['status']}, expected {expected_state}")
                if body is not None and body["result"]["success"]:
                    failures.append("denied Watch reports success=true")
                if entrypoint == "scheduler" and expected_state not in scheduler_log.getvalue():
                    failures.append("scheduler did not report the denied state")
                if entrypoint == "scheduler" and " done:" in scheduler_log.getvalue():
                    failures.append("scheduler reported denied work as done")
                if before["last_check_at"] != after["last_check_at"]:
                    failures.append("denied Watch advanced last_check_at")
                output.write_text(json.dumps({
                    "case": case,
                    "entrypoint": entrypoint,
                    "scheduler_log": scheduler_log.getvalue(),
                    "result": "failed" if failures else "passed",
                    "failures": failures,
                    "before": before,
                    "after": after,
                    "api_response": body,
                    "collection": ledger,
                    "rows_preserved": rows_before == rows_after,
                    "additional_transport_sends": len(sends) - sends_before,
                    "notifications_sent": len(harness.deliveries),
                    "blocked_edges": harness.blocked_edges,
                    "temporary_storage": True,
                    "activation": "staged",
                }, indent=2) + "\n")
                assert not failures, "; ".join(failures)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("case", choices=["request_cap", "zero_elapsed", "zero_provider", "expired"])
    parser.add_argument("output", type=Path)
    parser.add_argument("--entrypoint", choices=["api", "scheduler"], default="api")
    args = parser.parse_args()
    asyncio.run(main(args.case, args.output.resolve(), args.entrypoint))
