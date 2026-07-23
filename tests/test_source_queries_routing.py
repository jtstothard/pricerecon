"""Test per-connector query routing in watch_executor."""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from pricerecon.core import watch_executor
from pricerecon.models import (
    Watch,
    SourceConfig,
    WatchFilters,
    SpecMatch,
    WatchSchedule,
    WatchGrouping,
    WatchNotification,
    NormalizedListing,
    SourceType,
)


class FakeDiffResult:
    """Mock diff result for testing."""
    has_events = False
    new_listings: list[Any] = []
    price_drops: list[Any] = []
    stock_changes: list[Any] = []
    listings_gone: list[Any] = []


class FakeConnector:
    """Mock connector that records the query it receives."""

    def __init__(self, connector_id: str) -> None:
        self.connector_id = connector_id
        self.queries_received: list[str] = []
        self.filters_received: list[Any] = []

    async def initialize(self) -> Any:
        return None

    async def search(self, query: Any, connector_filters: Any) -> Any:
        self.queries_received.append(query)
        self.filters_received.append(connector_filters)
        return [
            NormalizedListing(
                source=self.connector_id,
                source_type=SourceType.MARKETPLACE,
                source_listing_id=f"{self.connector_id}_1",
                title_raw=f"Listing {self.connector_id}",
                price=Decimal("99.99"),
                currency="GBP",
                url=f"https://example.com/{self.connector_id}/1",
                timestamp_seen=datetime.now(timezone.utc),
                product_normalized=None,
                variant_normalized=None,
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
                category="test",
            )
        ]

    async def cleanup(self) -> Any:
        return None


class FakeCursor:
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        return None

    def fetchone(self) -> Any:
        return None


class FakeConn:
    def cursor(self) -> Any:
        return FakeCursor()

    def commit(self) -> Any:
        return None

    def close(self) -> Any:
        return None


@pytest.mark.asyncio
async def test_source_queries_override_per_connector(monkeypatch: Any) -> None:
    """Each connector receives its override from source_queries[connector_id]."""
    now = datetime.now(timezone.utc)

    # Track connector instances
    connector_instances: dict[str, FakeConnector] = {}

    class EbayConnectorClass:
        def __init__(self, **kwargs: Any) -> None:
            connector_instances["ebay"] = FakeConnector("ebay")
            self._inner = connector_instances["ebay"]

        async def initialize(self) -> Any:
            return await self._inner.initialize()

        async def search(self, query: Any, connector_filters: Any) -> Any:
            return await self._inner.search(query, connector_filters)

        async def cleanup(self) -> Any:
            return await self._inner.cleanup()

    class AliexpressConnectorClass:
        def __init__(self, **kwargs: Any) -> None:
            connector_instances["aliexpress"] = FakeConnector("aliexpress")
            self._inner = connector_instances["aliexpress"]

        async def initialize(self) -> Any:
            return await self._inner.initialize()

        async def search(self, query: Any, connector_filters: Any) -> Any:
            return await self._inner.search(query, connector_filters)

        async def cleanup(self) -> Any:
            return await self._inner.cleanup()

    watch = Watch(
        id=1,
        name="Mixed source watch",
        query="default query",
        display_title=None,
        category="test",
        synonym_groups=[],
        source_queries={
            "ebay": "ebay-specific query",
            "aliexpress": "aliexpress-specific query",
        },
        sources=[
            SourceConfig(connector="ebay", config={}),
            SourceConfig(connector="aliexpress", config={}),
        ],
        filters=WatchFilters(
            price_max=None,
            spec_match=SpecMatch(ram_gb=None),
            min_seller_feedback=None,
            min_seller_feedback_pct=None,
        ),
        schedule=WatchSchedule(time_window=None),
        grouping=WatchGrouping(product_key=None),
        notifications=WatchNotification(
            webhook_url=None,
            telegram_bot_token=None,
            telegram_chat_id=None,
            discord_webhook_url=None,
        ),
        enabled=True,
        created_at=now,
        updated_at=now,
        last_check_at=None,
        status="active",
    )

    # Mock dependencies
    monkeypatch.setattr(watch_executor, "get_watch", lambda watch_id: watch)
    monkeypatch.setattr(
        watch_executor, "run_check", lambda *_args, **_kwargs: (True, FakeDiffResult(), [])
    )
    monkeypatch.setattr(watch_executor, "get_db", lambda: FakeConn())
    monkeypatch.setattr(
        "pricerecon.connectors.discover_connectors",
        lambda: {"ebay": EbayConnectorClass, "aliexpress": AliexpressConnectorClass},
    )

    # Mock connector health
    health_records: list[tuple[str, str, str | None, dict[str, object] | None]] = []
    monkeypatch.setattr(
        watch_executor,
        "upsert_connector_health",
        lambda connector_id, status, last_error=None, details=None: health_records.append(
            (connector_id, status, last_error, details)
        ),
    )

    result = await watch_executor.execute_watch(1)

    assert result["success"] is True
    assert len(health_records) == 2

    # Verify each connector got its specific query
    assert connector_instances["ebay"].queries_received == ["ebay-specific query"]
    assert connector_instances["aliexpress"].queries_received == ["aliexpress-specific query"]


@pytest.mark.asyncio
async def test_source_queries_fallback_to_default(monkeypatch: Any) -> None:
    """Connectors without overrides fall back to watch.query."""
    now = datetime.now(timezone.utc)

    connector_instances: dict[str, FakeConnector] = {}

    class EbayConnectorClass:
        def __init__(self, **kwargs: Any) -> None:
            connector_instances["ebay"] = FakeConnector("ebay")
            self._inner = connector_instances["ebay"]

        async def initialize(self) -> Any:
            return await self._inner.initialize()

        async def search(self, query: Any, connector_filters: Any) -> Any:
            return await self._inner.search(query, connector_filters)

        async def cleanup(self) -> Any:
            return await self._inner.cleanup()

    class AliexpressConnectorClass:
        def __init__(self, **kwargs: Any) -> None:
            connector_instances["aliexpress"] = FakeConnector("aliexpress")
            self._inner = connector_instances["aliexpress"]

        async def initialize(self) -> Any:
            return await self._inner.initialize()

        async def search(self, query: Any, connector_filters: Any) -> Any:
            return await self._inner.search(query, connector_filters)

        async def cleanup(self) -> Any:
            return await self._inner.cleanup()

    watch = Watch(
        id=2,
        name="Partial overrides watch",
        query="default query",
        display_title=None,
        category="test",
        synonym_groups=[],
        source_queries={
            "ebay": "ebay-specific query",
        },
        sources=[
            SourceConfig(connector="ebay", config={}),
            SourceConfig(connector="aliexpress", config={}),
        ],
        filters=WatchFilters(
            price_max=None,
            spec_match=SpecMatch(ram_gb=None),
            min_seller_feedback=None,
            min_seller_feedback_pct=None,
        ),
        schedule=WatchSchedule(time_window=None),
        grouping=WatchGrouping(product_key=None),
        notifications=WatchNotification(
            webhook_url=None,
            telegram_bot_token=None,
            telegram_chat_id=None,
            discord_webhook_url=None,
        ),
        enabled=True,
        created_at=now,
        updated_at=now,
        last_check_at=None,
        status="active",
    )

    monkeypatch.setattr(watch_executor, "get_watch", lambda watch_id: watch)
    monkeypatch.setattr(
        watch_executor, "run_check", lambda *_args, **_kwargs: (True, FakeDiffResult(), [])
    )
    monkeypatch.setattr(watch_executor, "get_db", lambda: FakeConn())
    monkeypatch.setattr(
        "pricerecon.connectors.discover_connectors",
        lambda: {"ebay": EbayConnectorClass, "aliexpress": AliexpressConnectorClass},
    )

    health_records: list[tuple[str, str, str | None, dict[str, object] | None]] = []
    monkeypatch.setattr(
        watch_executor,
        "upsert_connector_health",
        lambda connector_id, status, last_error=None, details=None: health_records.append(
            (connector_id, status, last_error, details)
        ),
    )

    result = await watch_executor.execute_watch(2)

    assert result["success"] is True

    # ebay got its override
    assert connector_instances["ebay"].queries_received == ["ebay-specific query"]
    # aliexpress fell back to default
    assert connector_instances["aliexpress"].queries_received == ["default query"]


@pytest.mark.asyncio
async def test_source_queries_no_overrides_all_fallback(monkeypatch: Any) -> None:
    """When source_queries is empty, all connectors use default query."""
    now = datetime.now(timezone.utc)

    connector_instances: dict[str, FakeConnector] = {}

    class EbayConnectorClass:
        def __init__(self, **kwargs: Any) -> None:
            connector_instances["ebay"] = FakeConnector("ebay")
            self._inner = connector_instances["ebay"]

        async def initialize(self) -> Any:
            return await self._inner.initialize()

        async def search(self, query: Any, connector_filters: Any) -> Any:
            return await self._inner.search(query, connector_filters)

        async def cleanup(self) -> Any:
            return await self._inner.cleanup()

    class AliexpressConnectorClass:
        def __init__(self, **kwargs: Any) -> None:
            connector_instances["aliexpress"] = FakeConnector("aliexpress")
            self._inner = connector_instances["aliexpress"]

        async def initialize(self) -> Any:
            return await self._inner.initialize()

        async def search(self, query: Any, connector_filters: Any) -> Any:
            return await self._inner.search(query, connector_filters)

        async def cleanup(self) -> Any:
            return await self._inner.cleanup()

    watch = Watch(
        id=3,
        name="No overrides watch",
        query="default query",
        display_title=None,
        category="test",
        synonym_groups=[],
        source_queries={},
        sources=[
            SourceConfig(connector="ebay", config={}),
            SourceConfig(connector="aliexpress", config={}),
        ],
        filters=WatchFilters(
            price_max=None,
            spec_match=SpecMatch(ram_gb=None),
            min_seller_feedback=None,
            min_seller_feedback_pct=None,
        ),
        schedule=WatchSchedule(time_window=None),
        grouping=WatchGrouping(product_key=None),
        notifications=WatchNotification(
            webhook_url=None,
            telegram_bot_token=None,
            telegram_chat_id=None,
            discord_webhook_url=None,
        ),
        enabled=True,
        created_at=now,
        updated_at=now,
        last_check_at=None,
        status="active",
    )

    monkeypatch.setattr(watch_executor, "get_watch", lambda watch_id: watch)
    monkeypatch.setattr(
        watch_executor, "run_check", lambda *_args, **_kwargs: (True, FakeDiffResult(), [])
    )
    monkeypatch.setattr(watch_executor, "get_db", lambda: FakeConn())
    monkeypatch.setattr(
        "pricerecon.connectors.discover_connectors",
        lambda: {"ebay": EbayConnectorClass, "aliexpress": AliexpressConnectorClass},
    )

    health_records: list[tuple[str, str, str | None, dict[str, object] | None]] = []
    monkeypatch.setattr(
        watch_executor,
        "upsert_connector_health",
        lambda connector_id, status, last_error=None, details=None: health_records.append(
            (connector_id, status, last_error, details)
        ),
    )

    result = await watch_executor.execute_watch(3)

    assert result["success"] is True

    # Both connectors use default query
    assert connector_instances["ebay"].queries_received == ["default query"]
    assert connector_instances["aliexpress"].queries_received == ["default query"]


@pytest.mark.asyncio
async def test_source_queries_mixed_connectors(monkeypatch: Any) -> None:
    """Test mixed-source watch with some overrides and some fallback."""
    now = datetime.now(timezone.utc)

    connector_instances: dict[str, FakeConnector] = {}

    def make_connector_class(connector_id: str):
        def __init__(self, **kwargs: Any) -> None:
            connector_instances[connector_id] = FakeConnector(connector_id)
            self._inner = connector_instances[connector_id]

        async def initialize(self) -> Any:
            return await self._inner.initialize()

        async def search(self, query: Any, connector_filters: Any) -> Any:
            return await self._inner.search(query, connector_filters)

        async def cleanup(self) -> Any:
            return await self._inner.cleanup()

        return type(f"{connector_id.title()}Connector", (), {
            "__init__": __init__,
            "initialize": initialize,
            "search": search,
            "cleanup": cleanup,
        })

    watch = Watch(
        id=4,
        name="Mixed connectors watch",
        query="default query",
        display_title=None,
        category="test",
        synonym_groups=[],
        source_queries={
            "ebay": "ebay query",
            "johnlewis": "johnlewis query",
            # aliexpress and cex will fall back
        },
        sources=[
            SourceConfig(connector="ebay", config={}),
            SourceConfig(connector="aliexpress", config={}),
            SourceConfig(connector="cex", config={}),
            SourceConfig(connector="johnlewis", config={}),
        ],
        filters=WatchFilters(
            price_max=None,
            spec_match=SpecMatch(ram_gb=None),
            min_seller_feedback=None,
            min_seller_feedback_pct=None,
        ),
        schedule=WatchSchedule(time_window=None),
        grouping=WatchGrouping(product_key=None),
        notifications=WatchNotification(
            webhook_url=None,
            telegram_bot_token=None,
            telegram_chat_id=None,
            discord_webhook_url=None,
        ),
        enabled=True,
        created_at=now,
        updated_at=now,
        last_check_at=None,
        status="active",
    )

    monkeypatch.setattr(watch_executor, "get_watch", lambda watch_id: watch)
    monkeypatch.setattr(
        watch_executor, "run_check", lambda *_args, **_kwargs: (True, FakeDiffResult(), [])
    )
    monkeypatch.setattr(watch_executor, "get_db", lambda: FakeConn())

    monkeypatch.setattr(
        "pricerecon.connectors.discover_connectors",
        lambda: {cid: make_connector_class(cid) for cid in ["ebay", "aliexpress", "cex", "johnlewis"]},
    )

    health_records: list[tuple[str, str, str | None, dict[str, object] | None]] = []
    monkeypatch.setattr(
        watch_executor,
        "upsert_connector_health",
        lambda connector_id, status, last_error=None, details=None: health_records.append(
            (connector_id, status, last_error, details)
        ),
    )

    result = await watch_executor.execute_watch(4)

    assert result["success"] is True
    assert len(health_records) == 4

    # Verify each connector got correct query
    assert connector_instances["ebay"].queries_received == ["ebay query"]
    assert connector_instances["aliexpress"].queries_received == ["default query"]
    assert connector_instances["cex"].queries_received == ["default query"]
    assert connector_instances["johnlewis"].queries_received == ["johnlewis query"]


@pytest.mark.asyncio
async def test_source_queries_raw_strings_passed_unchanged(monkeypatch: Any) -> None:
    """Raw connector-native query strings are passed unchanged (no parsing/translation)."""
    now = datetime.now(timezone.utc)

    # Use raw connector-specific syntax
    raw_queries = {
        "ebay": "laptop* (RTX, GTX) -broken -refurbished",
        "aliexpress": "(RTX|GTX) laptop -broken -refurbished*",
    }

    connector_instances: dict[str, FakeConnector] = {}

    def make_connector_class(connector_id: str):
        def __init__(self, **kwargs: Any) -> None:
            connector_instances[connector_id] = FakeConnector(connector_id)
            self._inner = connector_instances[connector_id]

        async def initialize(self) -> Any:
            return await self._inner.initialize()

        async def search(self, query: Any, connector_filters: Any) -> Any:
            return await self._inner.search(query, connector_filters)

        async def cleanup(self) -> Any:
            return await self._inner.cleanup()

        return type(f"{connector_id.title()}Connector", (), {
            "__init__": __init__,
            "initialize": initialize,
            "search": search,
            "cleanup": cleanup,
        })

    watch = Watch(
        id=5,
        name="Raw queries watch",
        query="default query",
        display_title=None,
        category="test",
        synonym_groups=[],
        source_queries=raw_queries,
        sources=[
            SourceConfig(connector="ebay", config={}),
            SourceConfig(connector="aliexpress", config={}),
        ],
        filters=WatchFilters(
            price_max=None,
            spec_match=SpecMatch(ram_gb=None),
            min_seller_feedback=None,
            min_seller_feedback_pct=None,
        ),
        schedule=WatchSchedule(time_window=None),
        grouping=WatchGrouping(product_key=None),
        notifications=WatchNotification(
            webhook_url=None,
            telegram_bot_token=None,
            telegram_chat_id=None,
            discord_webhook_url=None,
        ),
        enabled=True,
        created_at=now,
        updated_at=now,
        last_check_at=None,
        status="active",
    )

    monkeypatch.setattr(watch_executor, "get_watch", lambda watch_id: watch)
    monkeypatch.setattr(
        watch_executor, "run_check", lambda *_args, **_kwargs: (True, FakeDiffResult(), [])
    )
    monkeypatch.setattr(watch_executor, "get_db", lambda: FakeConn())

    monkeypatch.setattr(
        "pricerecon.connectors.discover_connectors",
        lambda: {cid: make_connector_class(cid) for cid in ["ebay", "aliexpress"]},
    )

    health_records: list[tuple[str, str, str | None, dict[str, object] | None]] = []
    monkeypatch.setattr(
        watch_executor,
        "upsert_connector_health",
        lambda connector_id, status, last_error=None, details=None: health_records.append(
            (connector_id, status, last_error, details)
        ),
    )

    result = await watch_executor.execute_watch(5)

    assert result["success"] is True

    # Verify raw strings passed unchanged
    assert connector_instances["ebay"].queries_received == [raw_queries["ebay"]]
    assert connector_instances["aliexpress"].queries_received == [raw_queries["aliexpress"]]


@pytest.mark.asyncio
async def test_source_queries_with_price_max_filter(monkeypatch: Any) -> None:
    """Query routing works correctly with connector filters (e.g., price_max)."""
    now = datetime.now(timezone.utc)

    connector_instances: dict[str, FakeConnector] = {}

    def make_connector_class(connector_id: str):
        def __init__(self, **kwargs: Any) -> None:
            connector_instances[connector_id] = FakeConnector(connector_id)
            self._inner = connector_instances[connector_id]

        async def initialize(self) -> Any:
            return await self._inner.initialize()

        async def search(self, query: Any, connector_filters: Any) -> Any:
            return await self._inner.search(query, connector_filters)

        async def cleanup(self) -> Any:
            return await self._inner.cleanup()

        return type(f"{connector_id.title()}Connector", (), {
            "__init__": __init__,
            "initialize": initialize,
            "search": search,
            "cleanup": cleanup,
        })

    watch = Watch(
        id=6,
        name="Filter test watch",
        query="default query",
        display_title=None,
        category="test",
        synonym_groups=[],
        source_queries={
            "ebay": "ebay query",
            "aliexpress": "aliexpress query",
        },
        sources=[
            SourceConfig(connector="ebay", config={}),
            SourceConfig(connector="aliexpress", config={}),
        ],
        filters=WatchFilters(
            price_max=Decimal("1000.00"),
            spec_match=SpecMatch(ram_gb=None),
            min_seller_feedback=None,
            min_seller_feedback_pct=None,
        ),
        schedule=WatchSchedule(time_window=None),
        grouping=WatchGrouping(product_key=None),
        notifications=WatchNotification(
            webhook_url=None,
            telegram_bot_token=None,
            telegram_chat_id=None,
            discord_webhook_url=None,
        ),
        enabled=True,
        created_at=now,
        updated_at=now,
        last_check_at=None,
        status="active",
    )

    monkeypatch.setattr(watch_executor, "get_watch", lambda watch_id: watch)
    monkeypatch.setattr(
        watch_executor, "run_check", lambda *_args, **_kwargs: (True, FakeDiffResult(), [])
    )
    monkeypatch.setattr(watch_executor, "get_db", lambda: FakeConn())

    monkeypatch.setattr(
        "pricerecon.connectors.discover_connectors",
        lambda: {cid: make_connector_class(cid) for cid in ["ebay", "aliexpress"]},
    )

    health_records: list[tuple[str, str, str | None, dict[str, object] | None]] = []
    monkeypatch.setattr(
        watch_executor,
        "upsert_connector_health",
        lambda connector_id, status, last_error=None, details=None: health_records.append(
            (connector_id, status, last_error, details)
        ),
    )

    result = await watch_executor.execute_watch(6)

    assert result["success"] is True

    # Verify queries and filters
    assert connector_instances["ebay"].queries_received == ["ebay query"]
    assert connector_instances["aliexpress"].queries_received == ["aliexpress query"]

    # Verify price_max filters were passed
    assert connector_instances["ebay"].filters_received == [{"price_max": Decimal("1000.00")}]
    assert connector_instances["aliexpress"].filters_received == [{"price_max": Decimal("1000.00")}]