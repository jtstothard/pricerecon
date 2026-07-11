from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from pricerecon.connectors import discover_connectors
from pricerecon.core import watch_executor
from pricerecon.core.diff_engine import DiffResult
from pricerecon.models import NormalizedListing, SourceConfig, SourceType, Watch
from pricerecon.models.watches import ConditionFilter, EventType, SpecMatch, WatchFilters, WatchGrouping, WatchNotification, WatchSchedule


class DummyConnector:
    def __init__(self, **config):
        self.config = config
        self.initialized = False
        self.cleaned_up = False

    @property
    def source_role(self):
        return SourceType.SIGNAL

    async def initialize(self):
        self.initialized = True

    async def cleanup(self):
        self.cleaned_up = True

    async def search(self, query: str, filters: dict | None = None):
        return [
            NormalizedListing(
                source="hotukdeals",
                source_type=SourceType.SIGNAL,
                source_listing_id="abc-123",
                title_raw=f"{query} deal",
                price=Decimal("9.99"),
                currency="GBP",
                url="https://example.test/deal",
                timestamp_seen=datetime.now(timezone.utc),
                product_normalized=None,
                variant_normalized={"query": query},
                condition=None,
                condition_raw=None,
                shipping_cost=None,
                total_landed_cost=None,
                seller_or_store=None,
                seller_feedback_score=None,
                seller_feedback_pct=None,
                location=None,
                in_stock=None,
                stock_state=None,
                image_url=None,
                exact_variant_confirmed=None,
                variant_match_confidence=None,
                mismatch_flags=None,
                risk_flags=None,
                category=None,
            )
        ]


@pytest.mark.asyncio
async def test_discover_connectors_includes_template_and_standard_ids():
    connectors = discover_connectors()
    assert "hotukdeals" in connectors
    assert "reddit_hardwareswapuk" in connectors
    assert "cex" in connectors
    assert "amazon_uk" in connectors


@pytest.mark.asyncio
async def test_execute_watch_uses_discovered_connectors(monkeypatch):
    watch = Watch(
        id=42,
        name="HotUKDeals watch",
        query="rtx 4070",
        category=None,
        sources=[SourceConfig(connector="hotukdeals")],
        filters=WatchFilters(
            price_max=None,
            currency="GBP",
            condition_filter=ConditionFilter(),
            exclude_patterns=[],
            spec_match=SpecMatch(),
            min_seller_feedback=None,
            min_seller_feedback_pct=None,
        ),
        schedule=WatchSchedule(interval="4h", timezone="UTC", time_window=None),
        grouping=WatchGrouping(enabled=False, product_key=None),
        notifications=WatchNotification(
            events=[EventType.NEW_LISTING, EventType.PRICE_DROP, EventType.STOCK_CHANGE],
            channels=["webhook"],
            webhook_url=None,
            telegram_bot_token=None,
            telegram_chat_id=None,
            discord_webhook_url=None,
        ),
        enabled=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        last_check_at=None,
        status="active",
    )

    health_events: list[tuple[tuple, dict]] = []

    monkeypatch.setattr(watch_executor, "get_watch", lambda watch_id: watch)
    monkeypatch.setattr(watch_executor, "discover_connectors", lambda: {"hotukdeals": DummyConnector, "cex": DummyConnector})

    def fake_run_check(watch_id, listings):
        return True, DiffResult([], [], [], [], []), []

    monkeypatch.setattr(watch_executor, "run_check", fake_run_check)
    monkeypatch.setattr(watch_executor, "upsert_connector_health", lambda *args, **kwargs: health_events.append((args, kwargs)))

    result = await watch_executor.execute_watch(42)
    assert result["success"] is True
    assert result["listings_found"] == 1
    assert health_events


def test_frontend_build_artifact_present():
    frontend_dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
    assert (frontend_dist / "index.html").exists()
    assert (frontend_dist / "assets").exists()


def test_dockerfile_packages_frontend_and_serves_assets():
    dockerfile = Path(__file__).resolve().parents[1] / "Dockerfile"
    contents = dockerfile.read_text()
    assert "COPY --from=frontend-build /frontend/dist ./frontend/dist/" in contents
    assert "npm run build" in contents
    assert "CMD [\"python\", \"-m\", \"pricerecon\"]" in contents
