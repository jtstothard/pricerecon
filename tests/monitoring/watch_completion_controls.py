"""Successful empty and mixed admission controls at the Watch execution boundary."""

import asyncio
import sys

from .collection_workflows import envelope
from .harness import MonitoringHarness
from .workflows import LEGACY, get, listing


async def main(case, entrypoint):
    with MonitoringHarness(operating_envelope=False) as harness:
        from pricerecon.core.collection_policy import operating_policy

        sources = [{"connector": "cex"}]
        if case == "partial":
            sources.append({"connector": "scan"})
            harness.outcomes["cex"] = [
                listing(harness, "cex", "retained", "Militado ML05B blue", "90.00")
            ]
        harness.seed_legacy([(7, {**LEGACY, "sources": sources})])
        policy = envelope(harness, requests=1, reserve=0, spacing=0)
        async with harness.session() as (client, _):
            assert (await get(client, "/api/watches/7"))["last_check_at"] is None
            harness.clock.advance()
            with operating_policy(policy):
                if entrypoint == "api":
                    response = await client.post("/api/watches/7/check")
                    assert response.status_code == 200, response.text
                    body = response.json()
                    assert body["status"] == "completed"
                    result = body["result"]
                    assert result["success"] is True
                    expected = ["success", "capped"] if case == "partial" else ["success_empty"]
                    assert [o["state"] for o in result["acquisition_outcomes"]] == expected
                    assert result["listings_found"] == (1 if case == "partial" else 0)
                else:
                    await harness.application.check_watch(7)
            assert (await get(client, "/api/watches/7"))["last_check_at"] == "2026-10-27T13:00:00Z"
            assert len(harness.searches) == 1
            assert (await get(client, "/api/watches/7/listings"))["total"] == (
                1 if case == "partial" else 0
            )
            assert harness.deliveries == harness.blocked_edges == []
    print(f"PASS {case} {entrypoint}: completed with an acquired source and updated timestamp")


if __name__ == "__main__":
    asyncio.run(main(*sys.argv[1:]))
