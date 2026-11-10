"""Test per-connector query routing in watch_executor."""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, ClassVar

import pytest

from pricerecon.core import watch_executor
from pricerecon.models import (
    NormalizedListing,
    SourceConfig,
    SourceType,
    SpecMatch,
    Watch,
    WatchFilters,
    WatchGrouping,
    WatchNotification,
    WatchSchedule,
)


class FakeDiffResult:
    """Mock diff result for testing."""

    has_events = False
    new_listings: ClassVar[list[Any]] = []
    price_drops: ClassVar[list[Any]] = []
    stock_changes: ClassVar[list[Any]] = []
    listings_gone: ClassVar[list[Any]] = []


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
                timestamp_seen=datetime.now(UTC),
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
    now = datetime.now(UTC)

    # Track connector instances and constructor arguments for the live eBay path.
    connector_instances: dict[str, FakeConnector] = {}
    ebay_constructor_kwargs: dict[str, Any] = {}

    class EbayConnectorClass:
        def __init__(self, **kwargs: Any) -> None:
            ebay_constructor_kwargs.update(kwargs)
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
            # Reproduce a deployed watch with a stale null app_id. The
            # environment credential must still reach the OAuth constructor.
            SourceConfig(connector="ebay", config={"app_id": None}),
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
        "pricerecon.core.connector_health.list_connector_health",
        lambda path=None: {},
    )
    monkeypatch.setattr(
        "pricerecon.core.collection_policy.current_policy",
        lambda connection=None: None,
    )
    monkeypatch.setattr(
        "pricerecon.core.acquisition.upsert_connector_health",
        lambda connector_id, status, last_error=None, details=None: health_records.append(
            (connector_id, status, last_error, details)
        ),
    )
    monkeypatch.setenv("EBAY_APP_ID", "configured-live-app-id")

    result = await watch_executor.execute_watch(1)

    assert result["success"] is True
    assert ebay_constructor_kwargs["app_id"] == "configured-live-app-id"
    assert len(health_records) == 2

    # Verify each connector got its specific query
    assert connector_instances["ebay"].queries_received == ["ebay-specific query"]
    assert connector_instances["aliexpress"].queries_received == ["aliexpress-specific query"]


@pytest.mark.asyncio
async def test_source_queries_fallback_to_default(monkeypatch: Any) -> None:
    """Connectors without overrides fall back to watch.query."""
    now = datetime.now(UTC)

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
        "pricerecon.core.connector_health.list_connector_health",
        lambda path=None: {},
    )
    monkeypatch.setattr(
        "pricerecon.core.collection_policy.current_policy",
        lambda connection=None: None,
    )
    monkeypatch.setattr(
        "pricerecon.core.acquisition.upsert_connector_health",
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
    now = datetime.now(UTC)

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
        "pricerecon.core.connector_health.list_connector_health",
        lambda path=None: {},
    )
    monkeypatch.setattr(
        "pricerecon.core.collection_policy.current_policy",
        lambda connection=None: None,
    )
    monkeypatch.setattr(
        "pricerecon.core.acquisition.upsert_connector_health",
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
    now = datetime.now(UTC)

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

        return type(
            f"{connector_id.title()}Connector",
            (),
            {
                "__init__": __init__,
                "initialize": initialize,
                "search": search,
                "cleanup": cleanup,
            },
        )

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
        lambda: {
            cid: make_connector_class(cid) for cid in ["ebay", "aliexpress", "cex", "johnlewis"]
        },
    )

    health_records: list[tuple[str, str, str | None, dict[str, object] | None]] = []
    monkeypatch.setattr(
        "pricerecon.core.connector_health.list_connector_health",
        lambda path=None: {},
    )
    monkeypatch.setattr(
        "pricerecon.core.collection_policy.current_policy",
        lambda connection=None: None,
    )
    monkeypatch.setattr(
        "pricerecon.core.acquisition.upsert_connector_health",
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
    now = datetime.now(UTC)

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

        return type(
            f"{connector_id.title()}Connector",
            (),
            {
                "__init__": __init__,
                "initialize": initialize,
                "search": search,
                "cleanup": cleanup,
            },
        )

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
        "pricerecon.core.connector_health.list_connector_health",
        lambda path=None: {},
    )
    monkeypatch.setattr(
        "pricerecon.core.collection_policy.current_policy",
        lambda connection=None: None,
    )
    monkeypatch.setattr(
        "pricerecon.core.acquisition.upsert_connector_health",
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
    now = datetime.now(UTC)

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

        return type(
            f"{connector_id.title()}Connector",
            (),
            {
                "__init__": __init__,
                "initialize": initialize,
                "search": search,
                "cleanup": cleanup,
            },
        )

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
        "pricerecon.core.connector_health.list_connector_health",
        lambda path=None: {},
    )
    monkeypatch.setattr(
        "pricerecon.core.collection_policy.current_policy",
        lambda connection=None: None,
    )
    monkeypatch.setattr(
        "pricerecon.core.acquisition.upsert_connector_health",
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


def titled_listing(source: str, listing_id: str, title: str) -> NormalizedListing:
    return NormalizedListing(
        source=source,
        source_type=SourceType.MARKETPLACE,
        source_listing_id=listing_id,
        title_raw=title,
        price=Decimal("99.99"),
        currency="GBP",
        url=f"https://example.com/{source}/{listing_id}",
        timestamp_seen=datetime.now(UTC),
        in_stock=True,
    )


def _scoped_gate_watch(watch_id: int, name: str, source_queries: dict[str, str]) -> Watch:
    now = datetime.now(UTC)
    return Watch(
        id=watch_id,
        name=name,
        query="laptop",
        display_title=None,
        category="laptop",
        synonym_groups=[],
        source_queries=source_queries,
        sources=[SourceConfig(connector="ebay", config={})],
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


def _patch_scoped_gate_seams(
    monkeypatch: Any, watch: Watch, listings: list[NormalizedListing]
) -> list[str]:
    """Patch the executor seams the retargeted watch tests rely on."""

    queries: list[str] = []

    class EbayConnectorClass:
        async def initialize(self) -> Any:
            return None

        async def search(self, query: Any, connector_filters: Any) -> Any:
            queries.append(query)
            return listings

        async def cleanup(self) -> Any:
            return None

    monkeypatch.setattr(watch_executor, "get_watch", lambda watch_id: watch)
    monkeypatch.setattr(
        watch_executor, "run_check", lambda *_args, **_kwargs: (True, FakeDiffResult(), [])
    )
    monkeypatch.setattr(watch_executor, "get_db", lambda: FakeConn())
    monkeypatch.setattr(
        "pricerecon.connectors.discover_connectors",
        lambda: {"ebay": EbayConnectorClass},
    )
    monkeypatch.setattr(
        "pricerecon.core.connector_health.list_connector_health",
        lambda path=None: {},
    )
    monkeypatch.setattr(
        "pricerecon.core.collection_policy.current_policy",
        lambda connection=None: None,
    )
    monkeypatch.setattr(
        "pricerecon.core.acquisition.upsert_connector_health",
        lambda connector_id, status, last_error=None, details=None: None,
    )
    return queries


@pytest.mark.asyncio
async def test_plain_watch_without_source_queries_keeps_titles_lacking_query_terms(
    monkeypatch: Any,
) -> None:
    """Gate scoping decision, 2026-10-29 (PR #142 review finding M1).

    The all-query-terms title gate backs raw per-connector query overrides
    (ADR-0001: raw connector queries never replace title matching). A plain
    watch — no synonym groups and no ``source_queries`` — keeps the
    pre-ADR watch-path behavior of origin/main: listings whose titles lack
    the watch query terms are not dropped.
    """
    watch = _scoped_gate_watch(7, "Plain watch", source_queries={})
    listings = [
        titled_listing("ebay", "1", "Lenovo ThinkPad T14 16GB RAM 512GB SSD"),
        titled_listing("ebay", "2", "ASUS TUF Gaming A15 Notebook"),
    ]
    _patch_scoped_gate_seams(monkeypatch, watch, listings)

    result = await watch_executor.execute_watch(7)

    assert result["success"] is True
    # Neither title contains "laptop"; a plain watch keeps both anyway.
    assert result["listings_found"] == 2


@pytest.mark.asyncio
async def test_source_queries_watch_still_drops_titles_lacking_watch_query_terms(
    monkeypatch: Any,
) -> None:
    """Retained contract: with source_queries overrides the gate still fires.

    Raw connector queries widen recall (this eBay override matches ThinkPads
    that never say "laptop"), so the watch query terms remain the precision
    safety net: titles lacking them are dropped.
    """
    watch = _scoped_gate_watch(
        8, "Raw query watch", source_queries={"ebay": "thinkpad t14 (16gb, 32gb)"}
    )
    listings = [
        titled_listing("ebay", "1", "Lenovo ThinkPad T14 16GB RAM 512GB SSD"),
        titled_listing("ebay", "2", "Laptop stand"),
    ]
    queries = _patch_scoped_gate_seams(monkeypatch, watch, listings)

    result = await watch_executor.execute_watch(8)

    assert result["success"] is True
    # The raw override reached the connector unchanged...
    assert queries == ["thinkpad t14 (16gb, 32gb)"]
    # ...and only the title containing the watch query term survived.
    assert result["listings_found"] == 1


def _listing_with_price(
    source: str, listing_id: str, title: str, price: Decimal | None
) -> NormalizedListing:
    return titled_listing(source, listing_id, title).model_copy(update={"price": price})


@pytest.mark.asyncio
async def test_gate_dropped_priced_listings_emit_warning(monkeypatch: Any, caplog: Any) -> None:
    """Observability: priced listings dropped by the ADR-0001 gate are surfaced.

    When the top-level ``watch.query`` drifts from a ``source_queries``
    override, the gate silently drops priced connector listings and the only
    symptom is ``listings_found: 0`` (watch 344 debugging case). The gate's
    filtering behaviour is unchanged here — this asserts the WARNING log and
    the check-result counter only.
    """
    watch = _scoped_gate_watch(9, "Drifted override watch", source_queries={"ebay": "thinkpad t14"})
    listings = [
        # Passes the gate: title contains the watch query term "laptop".
        titled_listing("ebay", "1", "Lenovo ThinkPad T14 Laptop 16GB RAM"),
        # Dropped by the gate, priced: must be surfaced.
        _listing_with_price(
            "ebay", "2", "Lenovo ThinkPad T14 16GB RAM 512GB SSD", Decimal("599.99")
        ),
        # Dropped by the gate, no real price: stays silent.
        _listing_with_price("ebay", "3", "ASUS TUF Gaming A15 Notebook", None),
    ]
    queries = _patch_scoped_gate_seams(monkeypatch, watch, listings)

    with caplog.at_level(logging.WARNING, logger="pricerecon.core.watch_executor"):
        result = await watch_executor.execute_watch(9)

    assert result["success"] is True
    # The raw override reached the connector unchanged...
    assert queries == ["thinkpad t14"]
    # ...and filtering behaviour is unchanged: only the query-term match survives.
    assert result["listings_found"] == 1
    # Only the priced drop is surfaced in the check result.
    assert result["gate_dropped_priced_listings"] == 1

    warnings = [
        record
        for record in caplog.records
        if record.getMessage() == "adr0001_gate_dropped_priced_listings"
    ]
    assert len(warnings) == 1
    record = warnings[0]
    assert record.levelno == logging.WARNING
    assert record.watch_id == 9
    assert record.watch_query == "laptop"
    assert record.dropped_count == 1
    assert record.dropped_source_listing_ids == ["2"]


@pytest.mark.asyncio
async def test_gate_dropped_unpriced_listings_do_not_warn(monkeypatch: Any, caplog: Any) -> None:
    """Drops without a real price stay silent: no WARNING, counter stays 0."""
    watch = _scoped_gate_watch(10, "Unpriced drops watch", source_queries={"ebay": "thinkpad t14"})
    listings = [
        _listing_with_price("ebay", "1", "Lenovo ThinkPad T14 16GB RAM 512GB SSD", None),
        _listing_with_price("ebay", "2", "ASUS TUF Gaming A15 Notebook", Decimal("0.00")),
    ]
    _patch_scoped_gate_seams(monkeypatch, watch, listings)

    with caplog.at_level(logging.WARNING, logger="pricerecon.core.watch_executor"):
        result = await watch_executor.execute_watch(10)

    assert result["success"] is True
    # Both listings are still dropped — the gate behaviour is unchanged.
    assert result["listings_found"] == 0
    assert result["gate_dropped_priced_listings"] == 0
    assert not [
        record
        for record in caplog.records
        if record.getMessage() == "adr0001_gate_dropped_priced_listings"
    ]
