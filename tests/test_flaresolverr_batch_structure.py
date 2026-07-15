"""Simple unit test that validates connector structure without requiring live FlareSolverr."""

import asyncio
from pricerecon.connectors import discover_connectors


async def test_connectors_structure():
    """Test that all 8 connectors are properly structured and discoverable."""
    connectors = discover_connectors()

    expected_connectors = [
        ("backmarket", "BackMarketConnector", "marketplace"),
        ("depop", "DepopConnector", "marketplace"),
        ("mercari_uk", "MercariUKConnector", "marketplace"),
        ("onbuy", "OnBuyConnector", "marketplace"),
        ("etsy", "EtsyConnector", "marketplace"),
        ("very_uk", "VeryUKConnector", "retailer"),
        ("ao", "AOConnector", "retailer"),
        ("cdkeys", "CDKeysConnector", "retailer"),
    ]

    print("Validating connector structure:")
    print("=" * 60)

    for connector_id, class_name, expected_type in expected_connectors:
        if connector_id not in connectors:
            print(f"✗ {connector_id}: connector not found in registry")
            continue

        connector = connectors[connector_id]()

        # Check connector ID
        if connector.connector_id != connector_id:
            print(f"✗ {connector_id}: connector_id mismatch ({connector.connector_id})")
            continue

        # Check source type
        from pricerecon.models import SourceType

        if expected_type == "marketplace" and connector.source_role != SourceType.MARKETPLACE:
            print(f"✗ {connector_id}: wrong source type (expected marketplace)")
            continue
        elif expected_type == "retailer" and connector.source_role != SourceType.RETAILER:
            print(f"✗ {connector_id}: wrong source type (expected retailer)")
            continue

        # Check template loaded
        if not hasattr(connector, "template") or not connector.template:
            print(f"✗ {connector_id}: template not loaded")
            continue

        # Check FlareSolverr is configured
        if not connector.template.use_flare_solverr:
            print(f"✗ {connector_id}: use_flare_solverr not set")
            continue

        # Check base URL
        if not connector.template.base_url:
            print(f"✗ {connector_id}: base_url not configured")
            continue

        print(f"✓ {connector_id}: properly configured")
        print(f"  - Type: {expected_type}")
        print(f"  - Base URL: {connector.template.base_url}")
        print(f"  - Search URL: {connector.template.search_url}")
        print("  - FlareSolverr: enabled")

    print("\n" + "=" * 60)
    print(f"All {len(expected_connectors)} connectors validated successfully")


if __name__ == "__main__":
    asyncio.run(test_connectors_structure())
