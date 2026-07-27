"""HotUKDeals connector tests using real fixtures."""

import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from pricerecon.connectors.reddit import HotUKDealsConnector
from pricerecon.connectors.rss import parse_feed


@pytest.mark.asyncio
async def test_hotukdeals_real_feed_parsing():
    """Test parsing the real HotUKDeals RSS feed returns listings."""
    feed_xml = open("tests/fixtures/hotukdeals/new.xml").read()
    entries = parse_feed(feed_xml)

    assert len(entries) > 10, f"Expected >10 entries in real feed, got {len(entries)}"

    # Spot-check first entry
    assert entries[0].title
    assert entries[0].link
    assert entries[0].link.startswith("https://www.hotukdeals.com/deals/")


@pytest.mark.asyncio
async def test_hotukdeals_real_search_returns_listings():
    """Real search query against real fixture: expect >0 listings for relevant terms."""
    feed_xml = open("tests/fixtures/hotukdeals/new.xml").read()
    entries = parse_feed(feed_xml)

    connector = HotUKDealsConnector()
    connector._client = None  # Disable network

    # Mock fetch_entries to return our real feed
    connector.fetch_entries = lambda url: entries

    # Search for something generic that might appear
    # The real feed contains items like "Bloo 3in1", "Garnier Vitamin C", "Ibergrif Bathroom Set"
    listings_bloo = await connector.search("Bloo")
    assert len(listings_bloo) > 0, "Expected >0 listings for 'Bloo' in real feed"

    listings_bathroom = await connector.search("bathroom")
    assert len(listings_bathroom) > 0, "Expected >0 listings for 'bathroom' in real feed"

    # Ensure price extraction worked
    assert listings_bloo[0].price is not None
    assert listings_bloo[0].title_raw


@pytest.mark.asyncio
async def test_hotukdeals_missing_terms_returns_zero():
    """Search for something not in the real feed returns 0 listings (expected)."""
    feed_xml = open("tests/fixtures/hotukdeals/new.xml").read()
    entries = parse_feed(feed_xml)

    connector = HotUKDealsConnector()
    connector._client = None
    connector.fetch_entries = lambda url: entries

    # "RTX" is not in the real feed snapshot, so should return 0
    listings_rtx = await connector.search("RTX")
    assert len(listings_rtx) == 0, f"Expected 0 listings for 'RTX' (not in feed), got {len(listings_rtx)}"


@pytest.mark.asyncio
async def test_hotukdeals_cache_deduplicates_and_matches_locally(tmp_path: Path):
    """A feed snapshot is persisted once and subsequent searches filter it locally."""
    feed_xml = open("tests/fixtures/hotukdeals/new.xml").read()
    entries = parse_feed(feed_xml)
    connector = HotUKDealsConnector(cache_path=tmp_path / "hotukdeals.json")
    connector.fetch_entries = lambda url: entries

    first = await connector.search("bathroom")
    second = await connector.search("bathroom")

    assert first
    assert [item.source_listing_id for item in first] == [item.source_listing_id for item in second]
    assert connector.cache_size == len(entries)
    assert (tmp_path / "hotukdeals.json").exists()


@pytest.mark.asyncio
async def test_hotukdeals_uses_fresh_cache_when_feed_unavailable(tmp_path: Path):
    feed_xml = open("tests/fixtures/hotukdeals/new.xml").read()
    entries = parse_feed(feed_xml)
    cache_path = tmp_path / "hotukdeals.json"
    seed = HotUKDealsConnector(cache_path=cache_path)
    seed.fetch_entries = lambda url: entries
    await seed.search("bathroom")

    async def unavailable(url):
        raise RuntimeError("upstream unavailable")

    connector = HotUKDealsConnector(cache_path=cache_path)
    connector.fetch_entries = unavailable
    listings = await connector.search("bathroom")
    assert listings


def test_hotukdeals_cache_expires_old_entries(tmp_path: Path):
    connector = HotUKDealsConnector(cache_path=tmp_path / "hotukdeals.json")
    old = datetime.now(timezone.utc) - timedelta(days=connector.cache_retention_days + 1)
    entries = parse_feed(open("tests/fixtures/hotukdeals/new.xml").read())
    entries = [entry.model_copy(update={"published_at": old}) for entry in entries]
    connector._cache.upsert(entries, seen_at=old)
    connector._cache.save()
    assert connector.cache_size == 0
