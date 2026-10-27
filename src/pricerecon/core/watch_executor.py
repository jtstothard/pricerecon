"""Watch execution engine - runs watches and emits events.

Orchestrates connector calls, diff engine, and event emission.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pricerecon.connectors.specs import extract_specs
from pricerecon.core.diff_engine import run_check
from pricerecon.core.notifications import dispatch_for_event
from pricerecon.db.schema import DB_PATH
from pricerecon.models import EventType, NormalizedListing, Watch

logger = logging.getLogger(__name__)

SHADOW_FILTER_PATTERN_NAME = "P1"
SHADOW_FILTER_PATTERN = (
    r"\bfor\s+(?:the\s+)?(?:mac\s+studio|macbook(?:\s+pro)?|mac\s+mini|"
    r"strix(?:\s+halo)?|ryzen\s+ai\s+max(?:\+)?\s*395)\b[^\n]{0,100}\b"
    r"(?:ssd|solid\s*state\s*drive|pcb|circuit\s*board|nand|"
    r"upgrade\s*(?:kit|board|module)?|expansion\s*board|enclosure|charger|"
    r"cable|adapter|case|cover|psu|power\s*supply|heatsink|heat\s*sink|"
    r"ram\s*stick|memory\s*module)\b"
)


def _shadow_title(title: str) -> str:
    """Normalize punctuation to separators while retaining word boundaries."""
    return re.sub(r"[^\w\n]+", " ", title.casefold()).strip()


def evaluate_shadow_filters(
    listings: list[NormalizedListing], filters: Any, watch_id: int
) -> list[dict[str, Any]]:
    """Log-only evaluation of false-positive rules; never alters listings."""
    values = filters.model_dump() if hasattr(filters, "model_dump") else (filters or {})
    floor = values.get("min_price_gbp")
    pattern = values.get("component_subject_pattern") or SHADOW_FILTER_PATTERN
    results: list[dict[str, Any]] = []
    for listing in listings:
        matched: list[str] = []
        # Floors are GBP by contract. Prices should already be normalized by the
        # connector; unknown currencies and invalid values are review-worthy, not
        # silently coerced to zero (and are never suppressed in shadow mode).
        review_missing_price = listing.price is None
        review_invalid_price = False
        if listing.price is not None:
            try:
                review_invalid_price = not listing.price.is_finite()
            except (AttributeError, TypeError):
                review_invalid_price = True
        currency = (listing.currency or "").upper()
        price_gbp = listing.price if currency == "GBP" and not review_invalid_price else None
        if floor is not None and (
            review_missing_price
            or review_invalid_price
            or (price_gbp is None and listing.price is not None)
            or (price_gbp is not None and price_gbp < floor)
        ):
            matched.append("price_floor")
        title = _shadow_title(listing.title_raw)
        if pattern and re.search(pattern, title, flags=re.IGNORECASE):
            matched.append("component_pattern")
        if not matched:
            continue
        entry = {
            "tag": "shadow_filter",
            "watch_id": watch_id,
            "listing_id": listing.source_listing_id,
            "alert_id": None,
            "title": listing.title_raw,
            "price": str(listing.price) if listing.price is not None else None,
            "which_filter_matched": matched[0] if len(matched) == 1 else "both",
            "floor_value": floor,
            "pattern_name": SHADOW_FILTER_PATTERN_NAME,
        }
        if review_missing_price:
            entry["review"] = "missing_price"
        logger.info("shadow_filter", extra=entry)
        results.append(entry)
    return results


def apply_component_pattern_filter(
    listings: list[NormalizedListing], filters: Any
) -> list[NormalizedListing]:
    """Suppress listings matching the enforced P1 component-subject pattern."""
    values = filters.model_dump() if hasattr(filters, "model_dump") else (filters or {})
    if not values.get("enforce_component_pattern", True):
        return listings
    pattern = values.get("component_subject_pattern") or SHADOW_FILTER_PATTERN
    return [
        listing
        for listing in listings
        if not re.search(pattern, _shadow_title(listing.title_raw), flags=re.IGNORECASE)
    ]


def apply_price_floor_filter(
    listings: list[NormalizedListing], filters: Any
) -> list[NormalizedListing]:
    """Suppress listings below the per-watch GBP price floor.

    Only applies to GBP-priced listings. Non-GBP listings, missing prices, and
    invalid prices are passed through unchanged — the FB price parser now returns
    None for foreign-currency listings, so those will pass here rather than being
    incorrectly suppressed by a garbage price.
    """
    values = filters.model_dump() if hasattr(filters, "model_dump") else (filters or {})
    if not values.get("enforce_price_floor", True):
        return listings
    floor = values.get("min_price_gbp")
    if floor is None:
        return listings
    result = []
    for listing in listings:
        if listing.price is None:
            result.append(listing)
            continue
        currency = (listing.currency or "").upper()
        if currency != "GBP":
            result.append(listing)
            continue
        try:
            price_gbp = float(listing.price)
            if price_gbp >= floor:
                result.append(listing)
        except (TypeError, ValueError):
            result.append(listing)
    return result


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_watch(watch_id: int) -> Watch | None:
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


def _spec_matches_listing(
    listing: NormalizedListing, spec_match: Any, watch_synonym_groups: list[list[str]] | None = None
) -> bool:
    from pricerecon.core.title_matching import matches_watch_spec

    match_dict = (
        spec_match.model_dump() if hasattr(spec_match, "model_dump") else (spec_match or {})
    )
    # Watch-level synonym groups are an independent safety-net: they must run
    # even when a watch has no structured ``spec_match`` fields.  In
    # particular, do not let an empty/default SpecMatch bypass configured
    # title groups.
    if not match_dict and not watch_synonym_groups:
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
    listings: list[NormalizedListing],
    filters: Any,
    watch_synonym_groups: list[list[str]] | None = None,
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
        filtered = [lst for lst in filtered if lst.condition is None or lst.condition in conditions]
    spec_match = filter_dict.get("spec_match", {})
    if spec_match:
        filtered = [
            lst for lst in filtered if _spec_matches_listing(lst, spec_match, watch_synonym_groups)
        ]
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


async def execute_watch(watch_id: int) -> dict[str, Any]:
    watch = get_watch(watch_id)
    if not watch:
        return {"success": False, "error": f"Watch {watch_id} not found"}

    from uuid import uuid4

    from pricerecon.core.acquisition import acquire_sources

    acquisition_context = f"watch:{watch_id}:{uuid4()}"
    acquisition = await acquire_sources(
        watch.sources, query=watch.query, source_queries=watch.source_queries,
        filters={"price_max": watch.filters.price_max} if watch.filters.price_max else {},
        context_id=acquisition_context,
    )
    all_listings = acquisition.listings
    failed_sources = acquisition.failed_sources

    filtered_listings = apply_post_normalization_filters(
        all_listings, watch.filters, watch.synonym_groups if watch.synonym_groups else None
    )
    # ADR 0001: raw connector queries never replace title matching. Watches
    # without synonym groups retain the legacy all-query-terms safety net.
    if not watch.synonym_groups and not watch.filters.spec_match.synonym_groups:
        from pricerecon.core.title_matching import legacy_query_match

        filtered_listings = [
            listing
            for listing in filtered_listings
            if legacy_query_match(listing.title_raw, watch.query)
        ]
    # Keep shadow evaluation against the complete post-fetch set for auditing,
    # then enforce P1 component pattern + price floors before the alert pipeline.
    shadow_entries = evaluate_shadow_filters(all_listings, watch.filters, watch_id)
    filtered_listings = apply_component_pattern_filter(filtered_listings, watch.filters)
    filtered_listings = apply_price_floor_filter(filtered_listings, watch.filters)
    from pricerecon.core.rate_limiter import AdmissionDenied

    try:
        first_run, diff_result, event_ids = run_check(
            watch_id, filtered_listings, failed_sources=failed_sources
        )
    except AdmissionDenied as exc:
        from pricerecon.db.collection import reject_capture

        reject_capture(acquisition_context, exc.reason, exc.state)
        for outcome in acquisition.outcomes:
            if outcome.state in {"success", "success_empty", "partial", "cache_reuse"}:
                outcome.state, outcome.reason = exc.state, exc.reason
        return {"success": False, "watch_id": watch_id, "error": exc.reason,
                "acquisition_outcomes": [o.model_dump(mode="json") for o in acquisition.outcomes],
                "notifications_sent": 0, "events": []}

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE watches SET last_check_at = ? WHERE id = ?",
        (datetime.now(UTC).isoformat(), watch_id),
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
        "acquisition_outcomes": [outcome.model_dump(mode="json") for outcome in acquisition.outcomes],
        "watch_id": watch_id,
        "first_run": first_run,
        "listings_found": len(filtered_listings),
        "new_listings": len(diff_result.new_listings),
        "price_drops": len(diff_result.price_drops),
        "stock_changes": len(diff_result.stock_changes),
        "listings_gone": len(diff_result.listings_gone),
        "events": [],
        "notifications_sent": len(notifications_dispatched),
        "shadow_filters_logged": len(shadow_entries),
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
