"""Watch execution engine - runs watches and emits events.

Orchestrates connector calls, diff engine, and event emission.
"""

from __future__ import annotations

import importlib
import json
import sqlite3
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

import httpx

from pricerecon.core.connector_health import upsert_connector_health
from pricerecon.core.diff_engine import DiffResult, run_check
from pricerecon.core.notifications import dispatch_for_event
from pricerecon.db.schema import DB_PATH, get_db_path
from pricerecon.models import EventType, NormalizedListing, Watch
from pricerecon.connectors.status import ConnectorDegradedError


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_watch(watch_id: int) -> Optional[Watch]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM watches WHERE id = ?", (watch_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    config = json.loads(row["config_json"])
    return Watch(
        id=row["id"],
        name=row["name"],
        query=row["query"],
        category=row["category"],
        sources=config.get("sources", []),
        filters=config.get("filters", {}),
        schedule=config.get("schedule", {}),
        grouping=config.get("grouping", {}),
        notifications=config.get("notifications", {}),
        enabled=config.get("enabled", True),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        last_check_at=datetime.fromisoformat(row["last_check_at"]) if row["last_check_at"] else None,
        status=config.get("status", "active"),
    )


def apply_post_normalization_filters(listings: list[NormalizedListing], filters: Any) -> list[NormalizedListing]:
    filtered = listings
    filter_dict = filters.model_dump() if hasattr(filters, "model_dump") else filters
    price_max = filter_dict.get("price_max")
    if price_max:
        filtered = [lst for lst in filtered if lst.price <= Decimal(str(price_max))]
    condition_filter = filter_dict.get("condition_filter", {})
    conditions = condition_filter.get("conditions")
    if conditions:
        filtered = [lst for lst in filtered if lst.condition and lst.condition in conditions]
    if condition_filter.get("dedup_enabled", False):
        dedup_keys = {}
        for lst in filtered:
            import re
            title_norm = re.sub(r"\s*-\s*(Fair|Good|Excellent|Premium|Pristine)\s*$", "", lst.title_raw, flags=re.IGNORECASE)
            if title_norm not in dedup_keys:
                dedup_keys[title_norm] = lst
        filtered = list(dedup_keys.values())
    exclude_patterns = filter_dict.get("exclude_patterns", [])
    if exclude_patterns:
        import re
        for lst in filtered[:]:
            title_lower = lst.title_raw.lower()
            if any(re.search(pattern.lower(), title_lower) for pattern in exclude_patterns):
                filtered.remove(lst)
    return filtered


def _non_empty_error_message(exc: Exception) -> str:
    message = str(exc).strip()
    return message or exc.__class__.__name__


async def execute_watch(watch_id: int) -> dict[str, Any]:
    watch = get_watch(watch_id)
    if not watch:
        return {"success": False, "error": f"Watch {watch_id} not found"}

    all_listings = []
    for source in watch.sources:
        if not source.enabled:
            continue
        connector_id = source.connector
        if not connector_id:
            continue
        connector = None
        try:
            module = importlib.import_module(f"pricerecon.connectors.{connector_id}")
            candidates = [
                f"{connector_id.capitalize()}Connector",
                f"{connector_id.title().replace('_', '')}Connector",
                "eBayConnector",
                "ShopifyConnector",
                "FacebookMarketplaceConnector",
                "ConfigConnector",
            ]
            connector_class = next((getattr(module, name) for name in candidates if hasattr(module, name)), None)
            if connector_class is None:
                raise AttributeError(f"No connector class found in {module.__name__}")
            try:
                connector = connector_class(**(source.config or {}))
            except TypeError:
                connector = connector_class()
            await connector.initialize()
            connector_filters = {}
            if watch.filters.price_max:
                connector_filters["price_max"] = watch.filters.price_max
            listings = await connector.search(watch.query, connector_filters)
            all_listings.extend(listings)
            upsert_connector_health(connector_id, "ok", details={"listing_count": len(listings)})
        except ConnectorDegradedError as exc:
            last_error = exc.message.strip() if exc.message else exc.status.value
            upsert_connector_health(connector_id, exc.status.value, last_error=last_error, details=exc.detail)
            continue
        except httpx.TimeoutException as exc:
            message = _non_empty_error_message(exc)
            upsert_connector_health(
                connector_id,
                "timeout",
                last_error=message,
                details={"error": message, "error_type": exc.__class__.__name__},
            )
            continue
        except Exception as exc:
            message = _non_empty_error_message(exc)
            upsert_connector_health(
                connector_id,
                "unknown_error",
                last_error=message,
                details={"error": message, "error_type": exc.__class__.__name__},
            )
            print(f"Error running connector {connector_id}: {exc}")
        finally:
            if connector is not None:
                try:
                    await connector.cleanup()
                except Exception:
                    pass

    filtered_listings = apply_post_normalization_filters(all_listings, watch.filters)
    first_run, diff_result, event_ids = run_check(watch_id, filtered_listings)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE watches SET last_check_at = ? WHERE id = ?",
        (datetime.utcnow().isoformat(), watch_id),
    )
    conn.commit()
    conn.close()

    # Dispatch notifications for events
    notifications_dispatched = []
    if not first_run and diff_result.has_events:
        # Get events from database to get their IDs and full data
        for event_data in diff_result.new_listings:
            if event_ids:
                event_id = event_ids.pop(0)
                event_type = EventType.NEW_LISTING
                listing = event_data["listing"]
                channels = await dispatch_for_event(
                    watch_id=watch_id,
                    event_id=event_id,
                    event_type=event_type,
                    watch_name=watch.name,
                    watch_notifications=watch.notifications.model_dump(),
                    listing=listing,
                )
                if channels:
                    notifications_dispatched.append({"event_id": event_id, "channels": channels})

        for event_data in diff_result.price_drops:
            if event_ids:
                event_id = event_ids.pop(0)
                event_type = EventType.PRICE_DROP
                listing = event_data["listing"]
                listing["previous_price"] = event_data["previous_price"]
                channels = await dispatch_for_event(
                    watch_id=watch_id,
                    event_id=event_id,
                    event_type=event_type,
                    watch_name=watch.name,
                    watch_notifications=watch.notifications.model_dump(),
                    listing=listing,
                )
                if channels:
                    notifications_dispatched.append({"event_id": event_id, "channels": channels})

        for event_data in diff_result.stock_changes:
            if event_ids:
                event_id = event_ids.pop(0)
                event_type = EventType.STOCK_CHANGE
                listing = event_data["listing"]
                listing["previous_in_stock"] = event_data["previous_in_stock"]
                listing["current_in_stock"] = event_data["current_in_stock"]
                channels = await dispatch_for_event(
                    watch_id=watch_id,
                    event_id=event_id,
                    event_type=event_type,
                    watch_name=watch.name,
                    watch_notifications=watch.notifications.model_dump(),
                    listing=listing,
                )
                if channels:
                    notifications_dispatched.append({"event_id": event_id, "channels": channels})

        # listings_gone events (lower priority, usually not notified)
        for _ in diff_result.listings_gone:
            if event_ids:
                event_ids.pop(0)

    result = {
        "success": True,
        "watch_id": watch_id,
        "first_run": first_run,
        "listings_found": len(filtered_listings),
        "new_listings": len(diff_result.new_listings),
        "price_drops": len(diff_result.price_drops),
        "stock_changes": len(diff_result.stock_changes),
        "listings_gone": len(diff_result.listings_gone),
        "events": [],
        "notifications_sent": len(notifications_dispatched),
    }

    if not first_run and diff_result.has_events:
        for event in diff_result.new_listings:
            result["events"].append({"type": EventType.NEW_LISTING.value, "listing": event["listing"]})
        for event in diff_result.price_drops:
            result["events"].append({
                "type": EventType.PRICE_DROP.value,
                "listing": event["listing"],
                "previous_price": event["previous_price"],
                "current_price": event["current_price"],
                "drop_amount": event["drop_amount"],
            })
        for event in diff_result.stock_changes:
            result["events"].append({
                "type": EventType.STOCK_CHANGE.value,
                "listing": event["listing"],
                "previous_in_stock": event["previous_in_stock"],
                "current_in_stock": event["current_in_stock"],
            })
    return result


def get_watch_results(watch_id: int) -> dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT source, source_listing_id, title_raw, price, currency,
                  url, timestamp_seen, listing_json
           FROM listings
           WHERE watch_id = ?
           ORDER BY price ASC""",
        (watch_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    listings = []
    for row in rows:
        listing_json = json.loads(row["listing_json"])
        listings.append(
            {
                "source": row["source"],
                "source_listing_id": row["source_listing_id"],
                "title_raw": row["title_raw"],
                "price": float(row["price"]),
                "currency": row["currency"],
                "url": row["url"],
                "timestamp_seen": row["timestamp_seen"],
                "full_data": listing_json,
            }
        )
    return {"watch_id": watch_id, "listings": listings, "total_count": len(listings)}


def get_watch_events(watch_id: int, limit: int = 50) -> dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT id, event_type, listing_key, severity, event_json, created_at
           FROM events
           WHERE watch_id = ?
           ORDER BY created_at DESC
           LIMIT ?""",
        (watch_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    events = []
    for row in rows:
        event_json = json.loads(row["event_json"])
        events.append(
            {
                "id": row["id"],
                "event_type": row["event_type"],
                "listing_key": row["listing_key"],
                "severity": row["severity"],
                "event_json": event_json,
                "created_at": row["created_at"],
            }
        )
    return {"watch_id": watch_id, "events": events, "total_count": len(events)}
