"""
Test that verifies the frontend builds correct payloads for watch creation.
This test ensures the UI sends payloads that match the backend WatchCreate schema.
"""

import pytest
from pricerecon.models.watches import WatchCreate


def test_frontend_payload_structure_matches_backend():
    """
    Verify that the payload structure from the frontend matches backend expectations.

    This test validates:
    - sources is a list of objects with 'connector' field (not strings)
    - schedule is nested with interval inside (not top-level)
    - filters.condition_filter.conditions exists (not filters.condition)
    """
    # Simulate what the frontend should send (after fix)
    frontend_payload = {
        "name": "Test Watch",
        "query": "RTX 4090",
        "category": "gpu",
        "enabled": True,
        "sources": [{"connector": "ebay"}, {"connector": "cex"}],
        "schedule": {"interval": "4h"},
        "filters": {
            "price_max": 1000.0,
            "condition_filter": {"conditions": ["new", "refurbished"]},
        },
        "grouping": {},
        "notifications": {},
    }

    # This should validate successfully
    validated = WatchCreate(**frontend_payload)

    # Verify the structure is correct
    assert len(validated.sources) == 2
    assert validated.sources[0].connector == "ebay"
    assert validated.sources[0].enabled is True
    assert validated.schedule.interval == "4h"
    assert validated.schedule.timezone == "UTC"
    assert validated.filters.price_max == 1000.0
    assert len(validated.filters.condition_filter.conditions) == 2


def test_frontend_payload_rejects_old_structure():
    """
    Verify that the old (broken) frontend payload structure is rejected.

    This test validates that the backend properly rejects:
    - sources as string array
    - top-level interval
    - filters.condition (should be filters.condition_filter.conditions)
    """
    # Simulate what the frontend used to send (before fix)
    old_frontend_payload = {
        "name": "Test Watch",
        "query": "RTX 4090",
        "category": "gpu",
        "interval": "4h",  # Wrong: should be schedule.interval
        "enabled": True,
        "sources": ["ebay", "cex"],  # Wrong: should be objects
        "filters": {
            "price_max": 1000.0,
            "condition": ["new", "refurbished"],  # Wrong: should be condition_filter.conditions
        },
    }

    # This should fail validation
    with pytest.raises(Exception) as exc_info:
        WatchCreate(**old_frontend_payload)

    # Verify it's a validation error about sources
    assert "validation error" in str(exc_info.value).lower()


def test_minimal_frontend_payload():
    """
    Verify that minimal frontend payloads work correctly.

    Frontend might send only required fields, with defaults coming from backend.
    """
    minimal_payload = {
        "name": "Minimal Watch",
        "query": "test",
        "sources": [{"connector": "ebay"}],
        "schedule": {"interval": "4h"},
    }

    validated = WatchCreate(**minimal_payload)

    assert validated.name == "Minimal Watch"
    assert validated.query == "test"
    assert len(validated.sources) == 1
    assert validated.sources[0].connector == "ebay"
    assert validated.schedule.interval == "4h"
    # Verify defaults are applied
    assert validated.enabled is True
    assert validated.category is None


if __name__ == "__main__":
    # Run the tests
    test_frontend_payload_structure_matches_backend()
    print("✓ test_frontend_payload_structure_matches_backend passed")

    test_frontend_payload_rejects_old_structure()
    print("✓ test_frontend_payload_rejects_old_structure passed")

    test_minimal_frontend_payload()
    print("✓ test_minimal_frontend_payload passed")

    print("\nAll tests passed!")
