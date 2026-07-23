#!/usr/bin/env python3
"""PriceRecon CLI - watch management and execution."""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import click
import sqlite3

from pricerecon.db.schema import DB_PATH, init_db
from pricerecon.core.watch_executor import execute_watch, get_watch_results, get_watch_events
from pricerecon.models import (
    SourceConfig,
    WatchFilters,
    WatchSchedule,
    WatchGrouping,
    WatchNotification,
    ConditionFilter,
    SpecMatch,
    EventType,
)


def get_db() -> sqlite3.Connection:
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_db() -> None:
    """Ensure database exists and is initialized."""
    if not DB_PATH.exists():
        click.echo(f"Initializing database at {DB_PATH}")
        init_db(DB_PATH)


@click.group()
def cli() -> None:
    """PriceRecon CLI - monitor prices across multiple sources."""
    ensure_db()


# ============================================================================
# Watch Commands
# ============================================================================


@cli.group()
def watch() -> None:
    """Watch management commands."""
    pass


@watch.command("add")
@click.option("--name", required=True, help="Watch name")
@click.option("--query", required=True, help="Search query")
@click.option("--category", help="Product category (e.g., 'gpu', 'cpu')")
@click.option("--source", "sources", multiple=True, help="Sources to use (e.g., 'cex', 'ebay')")
@click.option("--price-max", type=float, help="Maximum price")
@click.option("--interval", default="4h", help="Check interval (e.g., '4h', '30m')")
def watch_add(
    name: str,
    query: str,
    category: Optional[str],
    sources: tuple,
    price_max: Optional[float],
    interval: str,
) -> None:
    """Add a new watch."""
    conn = get_db()
    cursor = conn.cursor()

    # Build sources list
    if not sources:
        sources = ("cex",)  # Default to CeX for this task

    source_configs = [SourceConfig(connector=s) for s in sources]

    # Build filters
    filters = WatchFilters(
        price_max=None,
        currency="GBP",
        condition_filter=ConditionFilter(),
        exclude_patterns=[],
        spec_match=SpecMatch(),
        min_seller_feedback=None,
        min_seller_feedback_pct=None,
    )
    if price_max:
        from decimal import Decimal
        filters.price_max = Decimal(str(price_max))

    # Build schedule
    schedule = WatchSchedule(interval=interval, time_window=None)

    # Build config JSON (using mode='json' to handle Decimal serialization)
    config = {
        "sources": [s.model_dump(mode='json') for s in source_configs],
        "filters": filters.model_dump(mode='json'),
        "schedule": schedule.model_dump(mode='json'),
        "grouping": WatchGrouping(enabled=False, product_key=None).model_dump(mode='json'),
        "notifications": WatchNotification(
            events=[EventType.NEW_LISTING, EventType.PRICE_DROP, EventType.STOCK_CHANGE],
            channels=["webhook"],
            webhook_url=None,
            telegram_bot_token=None,
            telegram_chat_id=None,
            discord_webhook_url=None,
        ).model_dump(mode='json'),
        "enabled": True,
        "status": "active",
    }

    try:
        cursor.execute(
            """INSERT INTO watches (name, query, category, config_json, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                name,
                query,
                category,
                json.dumps(config),
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat(),
            )
        )
        watch_id = cursor.lastrowid
        conn.commit()
        conn.close()

        click.echo(f"✓ Watch created with ID {watch_id}")
        click.echo(f"  Name: {name}")
        click.echo(f"  Query: {query}")
        click.echo(f"  Sources: {', '.join(sources)}")
        if price_max:
            click.echo(f"  Max price: £{price_max}")
        click.echo(f"  Interval: {interval}")

    except sqlite3.IntegrityError:
        conn.close()
        click.echo(f"✗ Watch with name '{name}' already exists", err=True)
        sys.exit(1)


@watch.command("list")
@click.option("--limit", default=20, help="Maximum watches to show")
def watch_list(limit: int) -> None:
    """List all watches."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT id, name, query, config_json, last_check_at
           FROM watches
           ORDER BY created_at DESC
           LIMIT ?""",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        click.echo("No watches found")
        return

    click.echo(f"Found {len(rows)} watch(es):")
    click.echo()

    for row in rows:
        config = json.loads(row["config_json"])
        enabled = config.get("enabled", True)
        status = config.get("status", "active")

        status_icon = "✓" if enabled else "✗"
        check_time = row["last_check_at"]
        if check_time:
            # Parse and format
            dt = datetime.fromisoformat(check_time)
            check_str = dt.strftime("%Y-%m-%d %H:%M")
        else:
            check_str = "never"

        click.echo(f"[{row['id']}] {status_icon} {row['name']}")
        click.echo(f"    Query: {row['query']}")
        click.echo(f"    Status: {status}")
        click.echo(f"    Last check: {check_str}")
        click.echo()


@watch.command("check")
@click.argument("watch_id", type=int)
def watch_check(watch_id: int) -> None:
    """Run a watch check immediately."""
    click.echo(f"Running check for watch {watch_id}...")

    # Run the check
    result = asyncio.run(execute_watch(watch_id))

    if not result["success"]:
        click.echo(f"✗ {result.get('error', 'Unknown error')}", err=True)
        sys.exit(1)

    click.echo()
    click.echo("✓ Check completed")
    click.echo(f"  Listings found: {result['listings_found']}")

    if result["first_run"]:
        click.echo("  First run: baseline established (no events)")
    else:
        click.echo(f"  New listings: {result['new_listings']}")
        click.echo(f"  Price drops: {result['price_drops']}")
        click.echo(f"  Stock changes: {result['stock_changes']}")
        click.echo(f"  Listings gone: {result['listings_gone']}")

    click.echo()

    # Show events
    if result["events"]:
        click.echo("Events:")
        for event in result["events"]:
            event_type = event["type"].upper()
            listing = event["listing"]

            if event_type == "NEW_LISTING":
                click.echo(f"  [{event_type}] {listing['title_raw']}")
                click.echo(f"    Price: £{listing['price']} | Source: {listing['source']}")
                click.echo(f"    URL: {listing['url']}")

            elif event_type == "PRICE_DROP":
                prev = event["previous_price"]
                curr = event["current_price"]
                drop = event["drop_amount"]
                click.echo(f"  [{event_type}] {listing['title_raw']}")
                click.echo(f"    £{prev:.2f} → £{curr:.2f} (saved £{drop:.2f})")
                click.echo(f"    Source: {listing['source']} | URL: {listing['url']}")

            elif event_type == "STOCK_CHANGE":
                prev = event["previous_in_stock"]
                curr = event["current_in_stock"]
                status = "IN STOCK" if curr else "OUT OF STOCK"
                click.echo(f"  [{event_type}] {listing['title_raw']}")
                click.echo(f"    {prev} → {status}")
                click.echo(f"    Source: {listing['source']} | URL: {listing['url']}")

            click.echo()


@watch.command("results")
@click.argument("watch_id", type=int)
def watch_results(watch_id: int) -> None:
    """Show current listings for a watch."""
    result = get_watch_results(watch_id)

    click.echo(f"Current listings for watch {watch_id}:")
    click.echo()

    if not result["listings"]:
        click.echo("No listings found")
        return

    for listing in result["listings"]:
        click.echo(f"[{listing['source']}] {listing['title_raw']}")
        click.echo(f"    Price: £{listing['price']:.2f} | ID: {listing['source_listing_id']}")
        click.echo(f"    URL: {listing['url']}")
        click.echo()

    click.echo(f"Total: {result['total_count']} listing(s)")


@watch.command("events")
@click.argument("watch_id", type=int)
@click.option("--limit", default=20, help="Maximum events to show")
def watch_events(watch_id: int, limit: int) -> None:
    """Show events for a watch."""
    result = get_watch_events(watch_id, limit)

    click.echo(f"Events for watch {watch_id}:")
    click.echo()

    if not result["events"]:
        click.echo("No events found")
        return

    for event in result["events"]:
        click.echo(f"[{event['id']}] {event['event_type'].upper()} - {event['created_at']}")
        click.echo(f"    Listing key: {event['listing_key']}")
        click.echo()

    click.echo(f"Total: {result['total_count']} event(s)")


if __name__ == "__main__":
    cli()