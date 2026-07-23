"""REST API tests for PriceRecon."""

from typing import AsyncGenerator, Generator

import pytest
from httpx import AsyncClient, ASGITransport

from pricerecon.app import app
from pricerecon.db.schema import DB_PATH, init_db


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    """Initialize database before each test."""
    if DB_PATH.exists():
        DB_PATH.unlink()
    init_db()
    yield


# ============================================================================
# Health Endpoint Tests
# ============================================================================


async def test_health_check(client: AsyncClient) -> None:
    """Test health check endpoint."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


# ============================================================================
# Watch CRUD Tests
# ============================================================================


async def test_list_watches(client: AsyncClient) -> None:
    """Test listing watches."""
    response = await client.get("/api/watches")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data


async def test_create_watch(client: AsyncClient) -> None:
    """Test creating a watch."""
    watch_data = {
        "name": "Test Watch",
        "query": "test query",
        "category": "electronics",
        "sources": [{"connector": "ebay"}],
        "schedule": {"interval": "1h"},
        "filters": {},
        "grouping": {},
        "notifications": {},
        "enabled": True,
    }
    response = await client.post("/api/watches", json=watch_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Watch"
    assert data["query"] == "test query"
    assert "id" in data


async def test_create_watch_initializes_scheduler_when_missing(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test API-created watches initialize the live scheduler singleton if needed."""
    from pricerecon.core import scheduler as scheduler_module

    calls: list[tuple] = []

    class DummyScheduler:
        def add_watch(self, watch_id: int, interval: str, timezone: str, time_window: None) -> None:
            calls.append((watch_id, interval, timezone, time_window))

        def remove_watch(self, watch_id: int) -> None:
            calls.append(("remove", watch_id))

    monkeypatch.setattr(
        scheduler_module,
        "get_scheduler",
        lambda: (_ for _ in ()).throw(RuntimeError("no scheduler")),
    )
    monkeypatch.setattr(scheduler_module, "init_scheduler", lambda: DummyScheduler())

    watch_data = {
        "name": "Immediate Watch",
        "query": "rtx 4070",
        "category": "gpu",
        "sources": [{"connector": "ebay"}],
        "schedule": {"interval": "1h", "timezone": "UTC"},
        "filters": {},
        "grouping": {},
        "notifications": {},
        "enabled": True,
    }
    response = await client.post("/api/watches", json=watch_data)
    assert response.status_code == 201
    assert calls and calls[0][0] == response.json()["id"]
    assert calls[0][1:] == ("1h", "UTC", None)


async def test_get_watch(client: AsyncClient) -> None:
    """Test getting a watch by ID."""
    # First create a watch
    watch_data = {
        "name": "Test Watch",
        "query": "test query",
        "category": "electronics",
        "sources": [{"connector": "ebay"}],
        "schedule": {"interval": "1h"},
        "filters": {},
        "grouping": {},
        "notifications": {},
        "enabled": True,
    }
    create_resp = await client.post("/api/watches", json=watch_data)
    watch_id = create_resp.json()["id"]

    # Now get it
    response = await client.get(f"/api/watches/{watch_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == watch_id
    assert data["name"] == "Test Watch"


async def test_update_watch(client: AsyncClient) -> None:
    """Test updating a watch."""
    # Create a watch
    watch_data = {
        "name": "Test Watch",
        "query": "test query",
        "category": "electronics",
        "sources": [{"connector": "ebay"}],
        "schedule": {"interval": "1h"},
        "filters": {},
        "grouping": {},
        "notifications": {},
        "enabled": True,
    }
    create_resp = await client.post("/api/watches", json=watch_data)
    watch_id = create_resp.json()["id"]

    # Update it
    update_data = {
        "name": "Updated Watch",
        "query": "updated query",
        "category": "electronics",
        "sources": [{"connector": "ebay"}],
        "schedule": {"interval": "2h"},
        "filters": {},
        "grouping": {},
        "notifications": {},
        "enabled": True,
    }
    response = await client.put(f"/api/watches/{watch_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Watch"
    assert data["query"] == "updated query"


async def test_delete_watch(client: AsyncClient) -> None:
    """Test deleting a watch."""
    # Create a watch
    watch_data = {
        "name": "Test Watch",
        "query": "test query",
        "category": "electronics",
        "sources": [{"connector": "ebay"}],
        "schedule": {"interval": "1h"},
        "filters": {},
        "grouping": {},
        "notifications": {},
        "enabled": True,
    }
    create_resp = await client.post("/api/watches", json=watch_data)
    watch_id = create_resp.json()["id"]

    # Delete it
    response = await client.delete(f"/api/watches/{watch_id}")
    assert response.status_code == 204

    # Verify it's gone
    get_resp = await client.get(f"/api/watches/{watch_id}")
    assert get_resp.status_code == 404


# ============================================================================
# Watch New Fields Round-trip Tests
# ============================================================================


async def test_create_watch_with_new_fields_roundtrip(client: AsyncClient) -> None:
    """Test that display_title, synonym_groups, and source_queries round-trip through create and get."""
    watch_data = {
        "name": "Advanced Watch",
        "query": "ryzen ai max 395 128gb",
        "display_title": "Strix Halo 128GB",
        "synonym_groups": [
            ["strix halo", "ryzen ai max", "ai max+ 395", "395+"],
            ["128gb"],
        ],
        "source_queries": {
            "ebay": '(ryzen OR strix OR "ai max") AND 128gb',
            "cex": "ryzen ai max 128gb",
            "amazon_uk": "ryzen ai max 395 128gb",
        },
        "category": "electronics",
        "sources": [{"connector": "ebay"}],
        "schedule": {"interval": "1h"},
        "filters": {},
        "grouping": {},
        "notifications": {},
        "enabled": True,
    }
    create_resp = await client.post("/api/watches", json=watch_data)
    assert create_resp.status_code == 201
    data = create_resp.json()
    watch_id = data["id"]

    # Verify new fields are in the response
    assert data["display_title"] == "Strix Halo 128GB"
    assert data["synonym_groups"] == [
        ["strix halo", "ryzen ai max", "ai max+ 395", "395+"],
        ["128gb"],
    ]
    assert data["source_queries"] == {
        "ebay": '(ryzen OR strix OR "ai max") AND 128gb',
        "cex": "ryzen ai max 128gb",
        "amazon_uk": "ryzen ai max 395 128gb",
    }

    # Get the watch and verify round-trip
    get_resp = await client.get(f"/api/watches/{watch_id}")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["display_title"] == "Strix Halo 128GB"
    assert get_data["synonym_groups"] == [
        ["strix halo", "ryzen ai max", "ai max+ 395", "395+"],
        ["128gb"],
    ]
    assert get_data["source_queries"] == {
        "ebay": '(ryzen OR strix OR "ai max") AND 128gb',
        "cex": "ryzen ai max 128gb",
        "amazon_uk": "ryzen ai max 395 128gb",
    }


async def test_update_watch_preserves_new_fields(client: AsyncClient) -> None:
    """Test that updating a watch with new fields preserves them correctly."""
    # Create watch with new fields
    watch_data = {
        "name": "Update Test Watch",
        "query": "test query",
        "display_title": "Original Display Title",
        "synonym_groups": [["term1"], ["term2"]],
        "source_queries": {"ebay": "ebay query"},
        "category": "electronics",
        "sources": [{"connector": "ebay"}],
        "schedule": {"interval": "1h"},
        "filters": {},
        "grouping": {},
        "notifications": {},
        "enabled": True,
    }
    create_resp = await client.post("/api/watches", json=watch_data)
    watch_id = create_resp.json()["id"]

    # Update with new values for the new fields
    update_data = {
        "name": "Update Test Watch",
        "query": "updated query",
        "display_title": "Updated Display Title",
        "synonym_groups": [["new1", "new2"], ["new3"]],
        "source_queries": {"ebay": "new ebay query", "cex": "new cex query"},
        "category": "electronics",
        "sources": [{"connector": "ebay"}],
        "schedule": {"interval": "2h"},
        "filters": {},
        "grouping": {},
        "notifications": {},
        "enabled": True,
    }
    update_resp = await client.put(f"/api/watches/{watch_id}", json=update_data)
    assert update_resp.status_code == 200
    update_data_result = update_resp.json()

    # Verify new fields were updated
    assert update_data_result["display_title"] == "Updated Display Title"
    assert update_data_result["synonym_groups"] == [["new1", "new2"], ["new3"]]
    assert update_data_result["source_queries"] == {
        "ebay": "new ebay query",
        "cex": "new cex query",
    }

    # Get again to verify persistence
    get_resp = await client.get(f"/api/watches/{watch_id}")
    get_data = get_resp.json()
    assert get_data["display_title"] == "Updated Display Title"
    assert get_data["synonym_groups"] == [["new1", "new2"], ["new3"]]
    assert get_data["source_queries"] == {
        "ebay": "new ebay query",
        "cex": "new cex query",
    }


async def test_old_payload_without_new_fields_remains_valid(client: AsyncClient) -> None:
    """Test that creating a watch with old-style payload (no new fields) still works."""
    old_style_watch = {
        "name": "Old Style Watch",
        "query": "old query",
        "category": "electronics",
        "sources": [{"connector": "ebay"}],
        "schedule": {"interval": "1h"},
        "filters": {},
        "grouping": {},
        "notifications": {},
        "enabled": True,
    }
    create_resp = await client.post("/api/watches", json=old_style_watch)
    assert create_resp.status_code == 201
    data = create_resp.json()

    # Verify defaults for new fields
    assert data["display_title"] is None
    assert data["synonym_groups"] == []
    assert data["source_queries"] == {}

    # Get should return same defaults
    watch_id = data["id"]
    get_resp = await client.get(f"/api/watches/{watch_id}")
    get_data = get_resp.json()
    assert get_data["display_title"] is None
    assert get_data["synonym_groups"] == []
    assert get_data["source_queries"] == {}


async def test_partial_update_preserves_existing_new_fields(client: AsyncClient) -> None:
    """Test that updating a subset of fields preserves existing new field values."""
    # Create watch with all new fields
    watch_data = {
        "name": "Partial Update Watch",
        "query": "test query",
        "display_title": "Original Title",
        "synonym_groups": [["syn1"], ["syn2"]],
        "source_queries": {"ebay": "original query"},
        "category": "electronics",
        "sources": [{"connector": "ebay"}],
        "schedule": {"interval": "1h"},
        "filters": {},
        "grouping": {},
        "notifications": {},
        "enabled": True,
    }
    create_resp = await client.post("/api/watches", json=watch_data)
    watch_id = create_resp.json()["id"]

    # Update only basic fields, not new fields
    partial_update = {
        "name": "Partial Update Watch",
        "query": "updated query",
        "display_title": "Original Title",  # Keep original
        "synonym_groups": [["syn1"], ["syn2"]],  # Keep original
        "source_queries": {"ebay": "original query"},  # Keep original
        "category": "electronics",
        "sources": [{"connector": "ebay"}],
        "schedule": {"interval": "2h"},  # Changed
        "filters": {},
        "grouping": {},
        "notifications": {},
        "enabled": True,
    }
    update_resp = await client.put(f"/api/watches/{watch_id}", json=partial_update)
    assert update_resp.status_code == 200
    data = update_resp.json()

    # Verify new fields are preserved
    assert data["display_title"] == "Original Title"
    assert data["synonym_groups"] == [["syn1"], ["syn2"]]
    assert data["source_queries"] == {"ebay": "original query"}
    # Verify other field was updated
    assert data["schedule"]["interval"] == "2h"


async def test_get_nonexistent_watch(client: AsyncClient) -> None:
    """Test getting a watch that doesn't exist."""
    response = await client.get("/api/watches/99999")
    assert response.status_code == 404


# ============================================================================
# Listings Endpoint Tests
# ============================================================================


async def test_get_watch_listings(client: AsyncClient) -> None:
    """Test getting listings for a watch."""
    # Create a watch first
    watch_data = {
        "name": "Test Watch",
        "query": "test query",
        "category": "electronics",
        "sources": [{"connector": "ebay"}],
        "schedule": {"interval": "1h"},
        "filters": {},
        "grouping": {},
        "notifications": {},
        "enabled": True,
    }
    create_resp = await client.post("/api/watches", json=watch_data)
    watch_id = create_resp.json()["id"]

    # Get listings (should be empty)
    response = await client.get(f"/api/watches/{watch_id}/listings")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


async def test_get_listings_for_nonexistent_watch(client: AsyncClient) -> None:
    """Test getting listings for a watch that doesn't exist."""
    response = await client.get("/api/watches/99999/listings")
    assert response.status_code == 404


# ============================================================================
# History Endpoint Tests
# ============================================================================


async def test_get_price_history(client: AsyncClient) -> None:
    """Test getting price history for a watch."""
    # Create a watch first
    watch_data = {
        "name": "Test Watch",
        "query": "test query",
        "category": "electronics",
        "sources": [{"connector": "ebay"}],
        "schedule": {"interval": "1h"},
        "filters": {},
        "grouping": {},
        "notifications": {},
        "enabled": True,
    }
    create_resp = await client.post("/api/watches", json=watch_data)
    watch_id = create_resp.json()["id"]

    # Get history (should be empty)
    response = await client.get(f"/api/watches/{watch_id}/history")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


async def test_get_history_for_nonexistent_watch(client: AsyncClient) -> None:
    """Test getting history for a watch that doesn't exist."""
    response = await client.get("/api/watches/99999/history")
    assert response.status_code == 404


# ============================================================================
# Events Endpoint Tests
# ============================================================================


async def test_get_watch_events(client: AsyncClient) -> None:
    """Test getting events for a watch."""
    # Create a watch first
    watch_data = {
        "name": "Test Watch",
        "query": "test query",
        "category": "electronics",
        "sources": [{"connector": "ebay"}],
        "schedule": {"interval": "1h"},
        "filters": {},
        "grouping": {},
        "notifications": {},
        "enabled": True,
    }
    create_resp = await client.post("/api/watches", json=watch_data)
    watch_id = create_resp.json()["id"]

    # Get events (should be empty)
    response = await client.get(f"/api/watches/{watch_id}/events")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


async def test_get_all_events(client: AsyncClient) -> None:
    """Test getting all events across all watches."""
    response = await client.get("/api/events")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data


async def test_get_events_for_nonexistent_watch(client: AsyncClient) -> None:
    """Test getting events for a watch that doesn't exist."""
    response = await client.get("/api/watches/99999/events")
    assert response.status_code == 404


# ============================================================================
# Sources Endpoint Tests
# ============================================================================


async def test_list_sources(client: AsyncClient) -> None:
    """Test listing sources."""
    response = await client.get("/api/sources")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


# ============================================================================
# Signals Endpoint Tests
# ============================================================================


async def test_get_signals(client: AsyncClient) -> None:
    """Test getting deal chatter signals."""
    response = await client.get("/api/signals")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data


async def test_get_signals_filtered(client: AsyncClient) -> None:
    """Test getting signals with filters."""
    # Create a watch first
    watch_data = {
        "name": "Test Watch",
        "query": "test query",
        "category": "electronics",
        "sources": [{"connector": "ebay"}],
        "schedule": {"interval": "1h"},
        "filters": {},
        "grouping": {},
        "notifications": {},
        "enabled": True,
    }
    create_resp = await client.post("/api/watches", json=watch_data)
    watch_id = create_resp.json()["id"]

    # Get signals filtered by watch_id
    response = await client.get(f"/api/signals?watch_id={watch_id}")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


# ============================================================================
# Export Endpoint Tests
# ============================================================================


async def test_export_watches_json(client: AsyncClient) -> None:
    """Test exporting watches as JSON."""
    response = await client.get("/api/export?resource=watches&format=json")
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]


async def test_export_watches_csv(client: AsyncClient) -> None:
    """Test exporting watches as CSV."""
    response = await client.get("/api/export?resource=watches&format=csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]


async def test_export_all(client: AsyncClient) -> None:
    """Test exporting all data."""
    response = await client.get("/api/export?resource=all&format=json")
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]


async def test_export_filtered_by_watch(client: AsyncClient) -> None:
    """Test exporting data filtered by watch ID."""
    # Create a watch first
    watch_data = {
        "name": "Test Watch",
        "query": "test query",
        "category": "electronics",
        "sources": [{"connector": "ebay"}],
        "schedule": {"interval": "1h"},
        "filters": {},
        "grouping": {},
        "notifications": {},
        "enabled": True,
    }
    create_resp = await client.post("/api/watches", json=watch_data)
    watch_id = create_resp.json()["id"]

    response = await client.get(f"/api/export?resource=watches&format=json&watch_id={watch_id}")
    assert response.status_code == 200


# ============================================================================
# Pagination Tests
# ============================================================================


async def test_pagination(client: AsyncClient) -> None:
    """Test pagination works correctly."""
    # Create multiple watches
    for i in range(5):
        watch_data = {
            "name": f"Test Watch {i}",
            "query": f"test query {i}",
            "category": "electronics",
            "sources": [{"connector": "ebay"}],
            "schedule": {"interval": "1h"},
            "filters": {},
            "grouping": {},
            "notifications": {},
            "enabled": True,
        }
        await client.post("/api/watches", json=watch_data)

    # Test first page
    response = await client.get("/api/watches?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2

    # Test second page
    response = await client.get("/api/watches?page=2&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["page"] == 2


# ============================================================================
# Main Test Runner
# ============================================================================


if __name__ == "__main__":
    import asyncio

    async def run_tests() -> None:
        """Run all tests."""
        from httpx import AsyncClient, ASGITransport
        from pricerecon.app import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Run a quick smoke test
            print("Running smoke tests...")

            # Health check
            resp = await client.get("/api/health")
            print(
                f"  GET /api/health: {resp.status_code} - {'PASS' if resp.status_code == 200 else 'FAIL'}"
            )

            # List watches
            resp = await client.get("/api/watches")
            print(
                f"  GET /api/watches: {resp.status_code} - {'PASS' if resp.status_code == 200 else 'FAIL'}"
            )

            # Create watch
            watch_data = {
                "name": "Smoke Test Watch",
                "query": "smoke test",
                "category": "test",
                "sources": [{"connector": "ebay"}],
                "schedule": {"interval": "1h"},
                "filters": {},
                "grouping": {},
                "notifications": {},
                "enabled": True,
            }
            resp = await client.post("/api/watches", json=watch_data)
            print(
                f"  POST /api/watches: {resp.status_code} - {'PASS' if resp.status_code == 201 else 'FAIL'}"
            )
            watch_id = resp.json()["id"]

            # Get watch
            resp = await client.get(f"/api/watches/{watch_id}")
            print(
                f"  GET /api/watches/{watch_id}: {resp.status_code} - {'PASS' if resp.status_code == 200 else 'FAIL'}"
            )

            print("Smoke tests complete!")

    asyncio.run(run_tests())
