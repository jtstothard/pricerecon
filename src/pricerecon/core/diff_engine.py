from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal

from pricerecon.db.schema import DB_PATH
from pricerecon.models import EventType, NormalizedListing


class DiffResult:
    """Result of diffing two listing sets."""

    def __init__(
        self,
        new_listings: list[dict],
        price_drops: list[dict],
        price_increases: list[dict],
        stock_changes: list[dict],
        listings_gone: list[dict],
    ):
        self.new_listings = new_listings
        self.price_drops = price_drops
        self.price_increases = price_increases
        self.stock_changes = stock_changes
        self.listings_gone = listings_gone

    @property
    def has_events(self) -> bool:
        """Check if any events were generated."""
        return bool(
            self.new_listings
            or self.price_drops
            or self.price_increases
            or self.stock_changes
            or self.listings_gone
        )


def get_db() -> sqlite3.Connection:
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_previous_listings(watch_id: int) -> dict[tuple[str, str], dict]:
    """Get previous listings for a watch.

    Returns dict keyed by (source, source_listing_id) with listing data.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT source, source_listing_id, title_raw, price, currency, url,
                  timestamp_seen, listing_json
           FROM listings
           WHERE watch_id = ?""",
        (watch_id,),
    )
    rows = cursor.fetchall()
    conn.close()

    previous = {}
    for row in rows:
        key = (row["source"], row["source_listing_id"])
        previous[key] = {
            "title_raw": row["title_raw"],
            "price": Decimal(row["price"]),
            "currency": row["currency"],
            "url": row["url"],
            "timestamp_seen": row["timestamp_seen"],
            "listing_json": row["listing_json"],
        }

    return previous


def is_first_run(watch_id: int) -> bool:
    """Check if this is the first run for a watch.

    First run is determined by whether there are any previous listings.
    """
    previous = get_previous_listings(watch_id)
    return len(previous) == 0


def compute_diff(
    watch_id: int,
    current_listings: list[NormalizedListing],
    *,
    failed_sources: set[str] | None = None,
) -> DiffResult:
    """Compute diff between current listings and previous state.

    Args:
        watch_id: Watch ID
        current_listings: Current listings from connectors

    Returns:
        DiffResult with detected changes
    """
    previous = get_previous_listings(watch_id)
    current = {}

    # Build current listing map
    for listing in current_listings:
        key = (listing.source, listing.source_listing_id)
        current[key] = listing

    new_listings = []
    price_drops = []
    price_increases = []
    stock_changes = []
    listings_gone = []

    # Check for new listings
    for key, listing in current.items():
        if key not in previous:
            new_listings.append(
                {
                    "listing": listing.model_dump(),
                    "event_type": EventType.NEW_LISTING.value,
                }
            )

    # Check for price changes and stock changes
    for key, listing in current.items():
        if key in previous:
            prev = previous[key]
            current_price = Decimal(str(listing.price))
            prev_price = prev["price"]

            if current_price < prev_price:
                price_drops.append(
                    {
                        "listing": listing.model_dump(),
                        "previous_price": float(prev_price),
                        "current_price": float(current_price),
                        "drop_amount": float(prev_price - current_price),
                        "event_type": EventType.PRICE_DROP.value,
                    }
                )
            elif current_price > prev_price:
                price_increases.append(
                    {
                        "listing": listing.model_dump(),
                        "previous_price": float(prev_price),
                        "current_price": float(current_price),
                        "increase_amount": float(current_price - prev_price),
                        "event_type": EventType.PRICE_INCREASE.value,
                    }
                )

            # Check stock change (in_stock transition)
            prev_stock = prev.get("listing_json", "{}")
            # Extract in_stock from previous JSON if available
            import json

            try:
                prev_data = json.loads(prev_stock)
                prev_in_stock = prev_data.get("in_stock")
            except (json.JSONDecodeError, AttributeError):
                prev_in_stock = None

            curr_in_stock = listing.in_stock

            if prev_in_stock is not None and curr_in_stock is not None:
                if prev_in_stock != curr_in_stock:
                    stock_changes.append(
                        {
                            "listing": listing.model_dump(),
                            "previous_in_stock": prev_in_stock,
                            "current_in_stock": curr_in_stock,
                            "event_type": EventType.STOCK_CHANGE.value,
                        }
                    )

    # Check for listings that disappeared
    for key in previous:
        if key not in current and key[0] not in (failed_sources or set()):
            prev = previous[key]
            listings_gone.append(
                {
                    "source": key[0],
                    "source_listing_id": key[1],
                    "title_raw": prev["title_raw"],
                    "url": prev["url"],
                    "event_type": EventType.LISTING_GONE.value,
                }
            )

    return DiffResult(
        new_listings=new_listings,
        price_drops=price_drops,
        price_increases=price_increases,
        stock_changes=stock_changes,
        listings_gone=listings_gone,
    )


def store_listings(
    watch_id: int,
    listings: list[NormalizedListing],
    *,
    failed_sources: set[str] | None = None,
    connection: sqlite3.Connection | None = None,
) -> None:
    """Store current listings in the database.

    Replaces previous listings except last-good rows from failed sources.
    Retained rows keep their original observation time and payload.
    """
    conn = connection if connection is not None else get_db()
    cursor = conn.cursor()

    if failed_sources:
        placeholders = ", ".join("?" for _ in failed_sources)
        cursor.execute(
            f"DELETE FROM listings WHERE watch_id = ? AND source NOT IN ({placeholders})",
            (watch_id, *sorted(failed_sources)),
        )
    else:
        cursor.execute("DELETE FROM listings WHERE watch_id = ?", (watch_id,))

    # Insert new listings
    for listing in listings:
        cursor.execute(
            """INSERT INTO listings (watch_id, source, source_listing_id, title_raw,
                                     price, currency, url, timestamp_seen, listing_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                watch_id,
                listing.source,
                listing.source_listing_id,
                listing.title_raw,
                str(listing.price),
                listing.currency,
                listing.url,
                (
                    listing.timestamp_seen.isoformat()
                    if listing.timestamp_seen
                    else datetime.now(timezone.utc).isoformat()
                ),
                listing.model_dump_json(),
            ),
        )

    if connection is None:
        conn.commit()
        conn.close()


def store_events(
    watch_id: int, diff_result: DiffResult, *, connection: sqlite3.Connection | None = None
) -> list[int]:
    """Store events from diff result in the database.

    Returns list of created event IDs.
    """

    conn = connection if connection is not None else get_db()
    cursor = conn.cursor()

    event_ids = []

    for event in diff_result.new_listings:
        listing_data = event["listing"]
        if hasattr(listing_data, "model_dump"):
            listing_data = listing_data.model_dump(mode="json")
        event["listing"] = listing_data
        cursor.execute(
            """INSERT INTO events (watch_id, event_type, listing_key, severity, event_json)
               VALUES (?, ?, ?, ?, ?)""",
            (
                watch_id,
                event["event_type"],
                f"{event['listing']['source']}|{event['listing']['source_listing_id']}",
                "info",
                json.dumps(event, default=str),
            ),
        )
        if cursor.lastrowid is not None:
            event_ids.append(cursor.lastrowid)

    for event in diff_result.price_drops:
        listing_data = event["listing"]
        if hasattr(listing_data, "model_dump"):
            listing_data = listing_data.model_dump(mode="json")
        event["listing"] = listing_data
        cursor.execute(
            """INSERT INTO events (watch_id, event_type, listing_key, severity, event_json)
               VALUES (?, ?, ?, ?, ?)""",
            (
                watch_id,
                event["event_type"],
                f"{event['listing']['source']}|{event['listing']['source_listing_id']}",
                "info",
                json.dumps(event, default=str),
            ),
        )
        if cursor.lastrowid is not None:
            event_ids.append(cursor.lastrowid)

    for event in diff_result.stock_changes:
        listing_data = event["listing"]
        if hasattr(listing_data, "model_dump"):
            listing_data = listing_data.model_dump(mode="json")
        event["listing"] = listing_data
        cursor.execute(
            """INSERT INTO events (watch_id, event_type, listing_key, severity, event_json)
               VALUES (?, ?, ?, ?, ?)""",
            (
                watch_id,
                event["event_type"],
                f"{event['listing']['source']}|{event['listing']['source_listing_id']}",
                "info",
                json.dumps(event, default=str),
            ),
        )
        if cursor.lastrowid is not None:
            event_ids.append(cursor.lastrowid)

    for event in diff_result.listings_gone:
        cursor.execute(
            """INSERT INTO events (watch_id, event_type, listing_key, severity, event_json)
               VALUES (?, ?, ?, ?, ?)""",
            (
                watch_id,
                event["event_type"],
                f"{event['source']}|{event['source_listing_id']}",
                "info",
                json.dumps(event, default=str),
            ),
        )
        if cursor.lastrowid is not None:
            event_ids.append(cursor.lastrowid)

    if connection is None:
        conn.commit()
        conn.close()

    return event_ids


def run_check(
    watch_id: int,
    listings: list[NormalizedListing],
    *,
    failed_sources: set[str] | None = None,
) -> tuple[bool, DiffResult, list[int]]:
    """Run a complete check cycle for a watch.

    1. Check if first run (silent baseline)
    2. Compute diff
    3. Store listings
    4. Store events (if not first run)

    Args:
        watch_id: Watch ID
        listings: Current listings from connectors
        failed_sources: Sources whose old evidence must survive failed collection.
            An empty successful collection still replaces its previous snapshot.

    Returns:
        Tuple of (is_first_run, DiffResult, event_ids)
    """
    first_run = is_first_run(watch_id)
    diff_result = compute_diff(watch_id, listings, failed_sources=failed_sources)

    from contextlib import closing

    from pricerecon.core.collection_policy import current_policy

    policy = current_policy()
    if policy:
        from pricerecon.core.rate_limiter import DurableAdmission
        from pricerecon.db.collection import storage_size

        with closing(get_db()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            before = storage_size(connection)
            store_listings(watch_id, listings, failed_sources=failed_sources, connection=connection)
            event_ids = (
                store_events(watch_id, diff_result, connection=connection)
                if (not first_run and diff_result.has_events)
                else []
            )
            DurableAdmission(policy, "sqlite", "tracking", watch_id).debit(
                {"storage_bytes": max(0, storage_size(connection) - before)}, connection=connection
            )
        return first_run, diff_result, event_ids

    # Store current listings (always)
    store_listings(watch_id, listings, failed_sources=failed_sources)

    # Store events only if not first run
    event_ids = []
    if not first_run and diff_result.has_events:
        event_ids = store_events(watch_id, diff_result)

    return first_run, diff_result, event_ids
