"""Ticket12 mode for the retained guarded fixture server, never a live backend."""

import json
from typing import Literal
from unittest.mock import patch
from uuid import uuid4

import uvicorn
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from .harness import MonitoringHarness
from .watch_workflow import capture, cost_edges, named_report, seed
from .workflows import LEGACY, get


async def serve(port):
    with MonitoringHarness() as harness:
        from pricerecon.core import notifications

        assert harness.application.frontend_dist.joinpath(
            "index.html"
        ).is_file(), "Build frontend before application imports"
        harness.seed_legacy(
            [(7, LEGACY), (8, {**LEGACY, "name": "Paused saved search", "enabled": False})]
        )
        identity = uuid4().hex
        harness.stack.enter_context(
            patch.object(
                notifications,
                "get_global_notification_config",
                lambda: {"webhook_url": "https://synthetic.invalid/captured-browser-send"},
            )
        )
        async with harness.session() as (client, scheduler):
            await seed(harness, client)
            router = APIRouter()

            @router.get("/api/offline-verification")
            async def marker():
                return {
                    "fixture": "ticket12-connected-ui-v1",
                    "fixture_id": identity,
                    "temporary_storage": True,
                    "automatic_checks": False,
                    "blocked_edges": harness.blocked_edges,
                    "notifications_sent": len(harness.deliveries),
                    "clock": harness.clock.now.isoformat(),
                    "actions": [
                        "baseline",
                        "cross",
                        "duplicate",
                        "drop",
                        "coupon",
                        "costs",
                        "stale",
                    ],
                    "limitations": "synthetic only; actual buyer feedback unproven; all collection staged",
                }

            class Step(BaseModel):
                model_config = ConfigDict(extra="forbid")
                fixture_id: str
                action: Literal[
                    "baseline", "cross", "duplicate", "drop", "coupon", "costs", "stale"
                ]

            @router.post("/api/offline-workflow-step")
            async def step(request: Step):
                if request.fixture_id != identity:
                    raise HTTPException(409, "Wrong offline fixture identity")
                harness.clock.advance(hours=3 if request.action == "stale" else 0.01)
                if request.action == "costs":
                    await cost_edges(harness, client)
                elif request.action == "coupon":
                    from .assessment_workflows import coupon_report, policy

                    feed = await get(client, "/api/discovery/watches")
                    for candidate in feed["candidates"]:
                        if candidate["source_listing_id"] != "addies":
                            continue
                        report = coupon_report(
                            harness, candidate["configuration"]["revision"] + 1, "addies"
                        )
                        prior = candidate["offers"][0]["coupons"]
                        revision = prior[0]["revision"] + 1 if prior else 1
                        report.coupons[0].application.expected_coupon_revision = revision
                        report.coupons[
                            0
                        ].application.receipt.observation.expected_coupon_revision = revision
                        await capture(
                            harness,
                            client,
                            [report],
                            sources=(candidate["source"],),
                            comparison=policy(
                                harness,
                                allowed_scenario_kinds=["public_no_coupon", "public_coupon"],
                            ),
                        )
                elif request.action != "stale":
                    price = {"baseline": "68", "drop": "54"}.get(request.action, "56")
                    await capture(
                        harness,
                        client,
                        [named_report(harness, "addies", price)],
                        sources=("cex",),
                    )
                return await marker()

            harness.application.app.router.routes[0:0] = router.routes
            print(
                f"OFFLINE_UI_READY http://127.0.0.1:{port}/discover; ticket12 synthetic; temporary SQLite; paused scheduler",
                flush=True,
            )
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
                assert harness.blocked_edges == []
                assert [j["watch_id"] for j in scheduler.list_watches()] == [7]
                print(json.dumps(await marker()), flush=True)


def control():
    """Parent-only state advancement against the marked loopback toy fixture."""
    import argparse
    import urllib.request

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument(
        "--step",
        required=True,
        choices=["baseline", "cross", "duplicate", "drop", "costs", "coupon", "stale"],
    )
    args = parser.parse_args()
    origin = f"http://127.0.0.1:{args.port}"
    with urllib.request.urlopen(origin + "/api/offline-verification", timeout=5) as response:
        marker = json.load(response)
    assert marker["fixture"] == "ticket12-connected-ui-v1"
    assert marker["temporary_storage"] and not marker["automatic_checks"]
    assert marker["blocked_edges"] == []
    request = urllib.request.Request(
        origin + "/api/offline-workflow-step",
        data=json.dumps({"fixture_id": marker["fixture_id"], "action": args.step}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        print(response.read().decode())


if __name__ == "__main__":
    control()
