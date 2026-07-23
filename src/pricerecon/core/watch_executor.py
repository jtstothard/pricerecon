"""Watch execution engine - runs watches and emits events.

Orchestrates connector calls, diff engine, and event emission.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

import httpx

from pricerecon.config import load_config
from pricerecon.connectors.browser_client import BrowserClient, BrowserSessionConfig
from pricerecon.core.connector_health import upsert_connector_health
from pricerecon.core.diff_engine import run_check
from pricerecon.core.notifications import dispatch_for_event
from pricerecon.core.hardware_routes import route_for_query, route_title_matches
from pricerecon.connectors.specs import extract_specs
from pricerecon.connectors.status import ConnectorDegradedError
from pricerecon.db.schema import DB_PATH
from pricerecon.models import EventType, NormalizedListing, Watch


def get_db() -> sqlite3.Connection:
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
        display_title=config.get("display_title"),
        category=row["category"],
        synonym_groups=config.get("synonym_groups", []),
        source_queries=config.get("source_queries", {}),
        sources=config.get("sources", []),
        filters=config.get("filters", {}),
        schedule=config.get("schedule", {}),
        grouping=config.get("grouping", {}),
        notifications=config.get("notifications", {}),
        enabled=config.get("enabled", True),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        last_check_at=(
            datetime.fromisoformat(row["last_check_at"]) if row["last_check_at"] else None
        ),
        status=config.get("status", "active"),
    )


def _normalized_listing_specs(listing: NormalizedListing) -> dict[str, Any]:
    specs: dict[str, Any] = {}
    if listing.variant_normalized:
        specs.update(listing.variant_normalized)
    specs.update(extract_specs(listing.title_raw, listing.category))
    return specs


def _storage_gb_from_specs(specs: dict[str, Any]) -> int | None:
    storage_size = specs.get("storage_size")
    if storage_size is None:
        return None
    try:
        storage_value = int(storage_size)
    except (TypeError, ValueError):
        return None
    unit = str(specs.get("storage_unit") or "GB").upper()
    if unit == "TB":
        return storage_value * 1000
    return storage_value


def _spec_matches_listing(listing: NormalizedListing, spec_match: Any, watch_synonym_groups: list[list[str]] | None = None) -> bool:
    from pricerecon.core.title_matching import matches_watch_spec

    match_dict = (
        spec_match.model_dump() if hasattr(spec_match, "model_dump") else (spec_match or {})
    )
    if not match_dict:
        return True

    # Use new token-based title matching
    if not matches_watch_spec(listing.title_raw, spec_match, watch_synonym_groups):
        return False

    # Spec field matching (ram, storage, cpu, gpu)
    specs = _normalized_listing_specs(listing)
    title_lower = listing.title_raw.lower()

    ram_gb = match_dict.get("ram_gb")
    if ram_gb is not None:
        listing_ram_gb = specs.get("ram_gb")
        if listing_ram_gb is None or int(listing_ram_gb) < int(ram_gb):
            return False

    storage_gb = match_dict.get("storage_gb")
    if storage_gb is not None:
        listing_storage_gb = _storage_gb_from_specs(specs)
        if listing_storage_gb is None or listing_storage_gb < int(storage_gb):
            return False

    cpu_model = match_dict.get("cpu_model")
    if cpu_model:
        cpu_text = str(specs.get("cpu_model") or "").lower()
        if str(cpu_model).lower() not in cpu_text and str(cpu_model).lower() not in title_lower:
            return False

    gpu_model = match_dict.get("gpu_model")
    if gpu_model:
        gpu_text = str(specs.get("gpu_model") or "").lower()
        if str(gpu_model).lower() not in gpu_text and str(gpu_model).lower() not in title_lower:
            return False

    return True


def apply_post_normalization_filters(
    listings: list[NormalizedListing], filters: Any, watch_synonym_groups: list[list[str]] | None = None
) -> list[NormalizedListing]:
    filtered = listings
    filter_dict = filters.model_dump() if hasattr(filters, "model_dump") else filters
    price_max = filter_dict.get("price_max")
    if price_max:
        filtered = [
            lst
            for lst in filtered
            if lst.price is not None and lst.price <= Decimal(str(price_max))
        ]
    condition_filter = filter_dict.get("condition_filter", {})
    conditions = condition_filter.get("conditions")
    if conditions:
        filtered = [lst for lst in filtered if lst.condition and lst.condition in conditions]
    spec_match = filter_dict.get("spec_match", {})
    if spec_match:
        filtered = [lst for lst in filtered if _spec_matches_listing(lst, spec_match, watch_synonym_groups)]
    if condition_filter.get("dedup_enabled", False):
        dedup_keys = {}
        for lst in filtered:
            import re

            title_norm = re.sub(
                r"\s*-\s*(Fair|Good|Excellent|Premium|Pristine)\s*$",
                "",
                lst.title_raw,
                flags=re.IGNORECASE,
            )
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

    runtime_config = load_config()
    connector_defaults = (
        runtime_config.get("connectors", {}) if isinstance(runtime_config, dict) else {}
    )

    all_listings = []

    for source in watch.sources:
        if not source.enabled:
            continue
        connector_id = source.connector
        if not connector_id:
            continue
        connector = None
        try:
            # Use entry-point registry to resolve connector_id -> class
            from pricerecon.connectors import discover_connectors

            all_connectors = discover_connectors()
            connector_class = all_connectors.get(connector_id)
            if connector_class is None:
                raise AttributeError(
                    f"Connector '{connector_id}' not found in registry. "
                    f"Available: {sorted(all_connectors.keys())}"
                )
            # Build connector kwargs: merge config-file defaults, env-level credentials,
            # and per-watch config. Per-watch config takes precedence.
            config_defaults = dict(connector_defaults.get(connector_id, {}) or {})
            connector_kwargs: dict[str, Any] = {**config_defaults, **dict(source.config or {})}
            if connector_id == "ebay":
                import os

                connector_kwargs.setdefault("app_id", os.environ.get("EBAY_APP_ID", ""))
                connector_kwargs.setdefault("cert_id", os.environ.get("EBAY_CERT_ID"))
            elif connector_id == "aliexpress":
                import os

                cfg = {**config_defaults, **dict(source.config or {})}
                cfg.setdefault("app_key", os.environ.get("ALIEXPRESS_APP_KEY"))
                cfg.setdefault("app_secret", os.environ.get("ALIEXPRESS_APP_SECRET"))
                cfg.setdefault("ds_app_key", os.environ.get("ALIEXPRESS_DS_APP_KEY"))
                cfg.setdefault("ds_app_secret", os.environ.get("ALIEXPRESS_DS_APP_SECRET"))
                cfg.setdefault("ds_access_token", os.environ.get("ALIEXPRESS_DS_ACCESS_TOKEN"))
                cfg.setdefault("ds_refresh_token", os.environ.get("ALIEXPRESS_DS_REFRESH_TOKEN"))
                browser_client = None
                camofox_url = (
                    cfg.get("camofox_url")
                    or os.environ.get("ALIEXPRESS_CAMOFOX_URL")
                    or os.environ.get("CAMOFOX_URL")
                    or "http://192.168.10.252:9377"
                )
                cfg.setdefault("camofox_url", camofox_url)
                if camofox_url:
                    browser_client = BrowserClient(
                        config=BrowserSessionConfig(
                            camofox_url=str(camofox_url),
                            camofox_user_id=str(
                                cfg.get("camofox_user_id") or f"pricerecon_{watch_id}"
                            ),
                            camofox_session_key=str(
                                cfg.get("camofox_session_key") or f"watch_{watch_id}"
                            ),
                            camofox_api_key=os.environ.get("CAMOFOX_API_KEY"),
                            camofox_access_key=os.environ.get("CAMOFOX_ACCESS_KEY"),
                        )
                    )
                connector_kwargs = {"config": cfg}
                if browser_client is not None:
                    connector_kwargs["browser_client"] = browser_client
            try:
                connector = connector_class(**connector_kwargs)
            except TypeError:
                connector = connector_class()
            await connector.initialize()
            connector_filters = {}
            if watch.filters.price_max:
                connector_filters["price_max"] = watch.filters.price_max
            # Use per-connector query if available, otherwise fall back to watch.query
            effective_query = watch.source_queries.get(connector_id, watch.query)
            listings = await connector.search(effective_query, connector_filters)
            all_listings.extend(listings)
            upsert_connector_health(connector_id, "ok", details={"listing_count": len(listings)})
        except ConnectorDegradedError as exc:
            last_error = exc.message.strip() if exc.message else exc.status.value
            upsert_connector_health(
                connector_id, exc.status.value, last_error=last_error, details=exc.detail
            )
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

    filtered_listings = apply_post_normalization_filters(
        all_listings,
        watch.filters,
        watch.synonym_groups if watch.synonym_groups else None
    )
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

    result: dict[str, Any] = {
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

    events: list[dict[str, Any]] = result["events"]

    if not first_run and diff_result.has_events:
        for event in diff_result.new_listings:
            events.append({"type": EventType.NEW_LISTING.value, "listing": event["listing"]})
        for event in diff_result.price_drops:
            events.append(
                {
                    "type": EventType.PRICE_DROP.value,
                    "listing": event["listing"],
                    "previous_price": event["previous_price"],
                    "current_price": event["current_price"],
                    "drop_amount": event["drop_amount"],
                }
            )
        for event in diff_result.stock_changes:
            events.append(
                {
                    "type": EventType.STOCK_CHANGE.value,
                    "listing": event["listing"],
                    "previous_in_stock": event["previous_in_stock"],
                    "current_in_stock": event["current_in_stock"],
                }
            )
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
