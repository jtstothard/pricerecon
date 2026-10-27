"""Ticket05-only controlled browser steps, mounted by the retained UI fixture."""

from typing import Literal
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict

from .tracking_workflows import capture, priced_report


def configure_tracking_fixture(harness, router):
    from pricerecon.core import notifications

    identity = uuid4().hex
    harness.stack.enter_context(
        patch.object(
            notifications,
            "get_global_notification_config",
            lambda: {"webhook_url": "https://synthetic.invalid/captured-browser-send"},
        )
    )

    class Step(BaseModel):
        model_config = ConfigDict(extra="forbid")
        fixture_id: str
        action: Literal["baseline", "cross", "duplicate", "drop", "stale"]

    @router.post("/api/offline-tracking-step")
    async def step(request: Step):
        if request.fixture_id != identity:
            raise HTTPException(409, "Wrong offline fixture identity")
        harness.clock.advance(hours=3 if request.action == "stale" else 0.1)
        if request.action != "stale":
            item = {"baseline": "68", "cross": "56", "duplicate": "56", "drop": "54"}[
                request.action
            ]
            # Keep the source listing/merchant selection stable across captures.
            await capture(
                harness,
                harness.ui_client,
                priced_report(harness, item, listing_id="fixture-1"),
                title="Addiesdive AD2066 mint",
                sources=("cex", "scan") if request.action == "duplicate" else ("cex",),
            )
        return {
            "fixture_id": identity,
            "notifications_sent": len(harness.deliveries),
            "blocked_edges": harness.blocked_edges,
        }

    return identity
