#!/usr/bin/env python3
"""
Test FlareSolverr-dependent connectors with live queries.
Run this after FlareSolverr is deployed to verify connectors work.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pricerecon.connectors.backmarket import BackMarketConnector
from pricerecon.connectors.depop import DepopConnector
from pricerecon.connectors.mercari_uk import MercariUKConnector
from pricerecon.connectors.onbuy import OnBuyConnector
from pricerecon.connectors.etsy import EtsyConnector
from pricerecon.connectors.very_uk import VeryUKConnector
from pricerecon.connectors.cdkeys import CDKeysConnector

# FlareSolverr-dependent connectors to test from the batch
CONNECTORS = [
    ("Back Market", BackMarketConnector),
    ("Depop", DepopConnector),
    ("Mercari", MercariUKConnector),
    ("OnBuy", OnBuyConnector),
    ("Etsy", EtsyConnector),
    ("Very.co.uk", VeryUKConnector),
    ("CDKeys", CDKeysConnector),
]

# Test queries
TEST_QUERIES = [
    "iPhone 12",
    "RTX 3060",
    "Nintendo Switch",
]


async def test_connector(name: str, connector_class, query: str) -> dict:
    """Test a single connector and return results."""
    result = {
        "connector": name,
        "query": query,
        "success": False,
        "listings": 0,
        "error": None,
        "error_type": None,
    }

    conn = connector_class()
    try:
        listings = await conn.search(query)
        result["success"] = True
        result["listings"] = len(listings)
        
        # Show sample listing
        if listings:
            sample = listings[0]
            print(f"    ✓ Got {len(listings)} listings")
            print(f"      Sample: {sample.title[:50]}... - {sample.price}")
    except Exception as e:
        result["error"] = str(e)
        result["error_type"] = type(e).__name__
        print(f"    ✗ {type(e).__name__}: {str(e)[:80]}")
    finally:
        await conn.cleanup()

    return result


async def main():
    """Test all FlareSolverr connectors."""
    print("=" * 70)
    print("FlareSolverr Connector Live Verification")
    print("=" * 70)
    print()

    results = []
    for name, connector_class in CONNECTORS:
        print(f"Testing {name}...")
        # Test with first query only to save time
        result = await test_connector(name, connector_class, TEST_QUERIES[0])
        results.append(result)
        print()

    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print()

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print(f"Successful: {len(successful)}/{len(results)}")
    print(f"Failed: {len(failed)}/{len(results)}")
    print()

    if successful:
        print("Working connectors:")
        for r in successful:
            print(f"  ✓ {r['connector']} - {r['listings']} listings")
        print()

    if failed:
        print("Failed connectors:")
        for r in failed:
            print(f"  ✗ {r['connector']} - {r['error_type']}: {r['error'][:60]}")
        print()

    # Exit code based on success rate
    # Consider it a pass if at least 75% of connectors work
    success_rate = len(successful) / len(results)
    if success_rate >= 0.75:
        print(f"✓ {success_rate*100:.0f}% success rate - connectors are healthy")
        sys.exit(0)
    else:
        print(f"✗ {success_rate*100:.0f}% success rate - connectors need attention")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())