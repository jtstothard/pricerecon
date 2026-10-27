"""Guarded loopback fixture for ticket10; no live source or sending edges."""

import argparse
import asyncio
import json

import uvicorn
from fastapi import APIRouter

from .collection_workflows import envelope
from .harness import MonitoringHarness
from .workflows import LEGACY, listing


async def main(port):
    with MonitoringHarness(operating_envelope=False) as harness:
        from pricerecon.core.collection_policy import operating_policy
        from pricerecon.core.connector_health import upsert_connector_health
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest

        harness.seed_legacy([(7, LEGACY)])
        names = [
            "Militado ML05/ML05B",
            "Addiesdive AD2066 mint",
            "San Martin SN0144",
            "Merkur Lightning salmon",
            "Casio MTP-B145D-2A2VEF",
        ]
        harness.outcomes["cex"] = [
            listing(harness, "cex", f"fixture-{i}", name, "48.00") for i, name in enumerate(names)
        ]
        async with harness.session() as (_client, scheduler):
            admission = DiscoveryAdmission(
                mode="offline_verification",
                policy_reference="synthetic",
                permission_reference="original-fixtures",
                activation_reference="isolated-ui",
            )
            with operating_policy(envelope(harness, requests=4, reserve=1, spacing=0)):
                for source in ("cex", "scan"):
                    await execute_discovery(
                        DiscoveryRequest(query="watch", sources=[{"connector": source}]),
                        admission=admission,
                    )
                harness.outcomes["scan"] = RuntimeError("synthetic partial source failure")
                await execute_discovery(
                    DiscoveryRequest(query="watch", sources=[{"connector": "scan"}]),
                    admission=admission,
                )
                harness.clock.advance()
                await execute_discovery(
                    DiscoveryRequest(query="watch", sources=[{"connector": "cex"}]),
                    admission=admission,
                )
                # Transport health cannot change acquisition/evidence dates.
                upsert_connector_health("cex", "ok")
                upsert_connector_health("amazon_uk", "auth_failed")
                await execute_discovery(
                    DiscoveryRequest(query="watch", sources=[{"connector": "amazon_uk"}]),
                    admission=admission,
                )
                fixture = APIRouter()

                @fixture.get("/api/offline-verification")
                async def marker():
                    return {
                        "fixture": "ticket10-collection-ui",
                        "temporary_storage": True,
                        "automatic_checks": False,
                        "blocked_edges": harness.blocked_edges,
                        "notifications_sent": len(harness.deliveries),
                    }

                harness.application.app.router.routes[0:0] = fixture.routes
                print(f"OFFLINE_COLLECTION_UI_READY {port}", flush=True)
                try:
                    await uvicorn.Server(
                        uvicorn.Config(
                            harness.application.app,
                            host="127.0.0.1",
                            port=port,
                            loop="asyncio",
                            lifespan="off",
                            access_log=False,
                        )
                    ).serve()
                finally:
                    assert harness.blocked_edges == harness.deliveries == []
                    assert len(scheduler.list_watches()) == 1
                    print(
                        json.dumps(
                            {
                                "blocked_edges": harness.blocked_edges,
                                "notifications_sent": len(harness.deliveries),
                                "temporary_storage": True,
                            }
                        ),
                        flush=True,
                    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True, type=int)
    args = parser.parse_args()
    asyncio.run(main(args.port))
