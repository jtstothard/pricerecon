"""Deal chatter panel data API endpoints."""

from datetime import datetime
from decimal import Decimal

import sqlite3
import json
from fastapi import APIRouter, Query
from pydantic import BaseModel

from pricerecon.db.schema import DB_PATH

router = APIRouter()


# ============================================================================
# Signal Models
# ============================================================================


class Signal(BaseModel):
    """Deal chatter signal."""

    id: int
    watch_id: int
    watch_name: str
    signal_type: str  # "price_drop", "new_listing", "low_stock", "back_in_stock"
    title: str
    description: str
    listing_id: str | None = None
    old_price: Decimal | None = None
    new_price: Decimal | None = None
    discount_pct: Decimal | None = None
    created_at: datetime


class SignalsResponse(BaseModel):
    """Response for signals."""

    items: list[Signal]
    total: int
    page: int
    page_size: int


# ============================================================================
# Database Helpers
# ============================================================================


def get_db() -> sqlite3.Connection:
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================================
# Signals Endpoints
# ============================================================================


@router.get("/signals", response_model=SignalsResponse)
async def get_signals(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    signal_type: str | None = Query(None, description="Filter by signal type"),
    watch_id: int | None = Query(None, description="Filter by watch ID"),
) -> SignalsResponse:
    """Get deal chatter signals with optional filters."""
    conn = get_db()
    cursor = conn.cursor()

    # Build query with filters
    where_clauses = []
    params: list[str | int] = []

    if signal_type:
        where_clauses.append("event_type = ?")
        params.append(signal_type)

    if watch_id:
        where_clauses.append("watch_id = ?")
        params.append(watch_id)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # Get total count
    count_sql = f"SELECT COUNT(*) as total FROM events WHERE {where_sql}"
    cursor.execute(count_sql, params)
    total = cursor.fetchone()["total"]

    # Get paginated results
    skip = (page - 1) * page_size
    sql = f"""
        SELECT 
            e.id,
            e.watch_id,
            w.name as watch_name,
            e.event_type,
            e.event_json,
            e.created_at
        FROM events e
        JOIN watches w ON e.watch_id = w.id
        WHERE {where_sql}
        ORDER BY e.created_at DESC
        LIMIT ? OFFSET ?
    """
    params.extend([page_size, skip])
    cursor.execute(sql, params)
    rows = cursor.fetchall()

    signals = []
    for row in rows:
        event_json = json.loads(row["event_json"])

        # Map event types to signal types
        signal_map = {
            "price_drop": "price_drop",
            "price_change": "price_drop",
            "new_listing": "new_listing",
            "listing_appeared": "new_listing",
            "low_stock": "low_stock",
            "out_of_stock": "low_stock",
            "back_in_stock": "back_in_stock",
            "listing_reappeared": "back_in_stock",
        }

        signal_type = signal_map.get(row["event_type"], row["event_type"])

        # Extract relevant data based on signal type
        old_price = None
        new_price = None
        discount_pct = None
        listing_id = str(row["listing_key"]) if row["listing_key"] else None

        if signal_type == "price_drop":
            old_price = (
                Decimal(str(event_json.get("old_price"))) if event_json.get("old_price") else None
            )
            new_price = (
                Decimal(str(event_json.get("new_price"))) if event_json.get("new_price") else None
            )
            if old_price and new_price:
                discount_pct = Decimal(str((old_price - new_price) / old_price * 100))

        title = f"{signal_type.replace('_', ' ').title()} - {row['watch_name']}"
        description = event_json.get("description", event_json.get("message", ""))

        signals.append(
            Signal(
                id=row["id"],
                watch_id=row["watch_id"],
                watch_name=row["watch_name"],
                signal_type=signal_type,
                title=title,
                description=description,
                listing_id=listing_id,
                old_price=old_price,
                new_price=new_price,
                discount_pct=discount_pct,
                created_at=datetime.fromisoformat(row["created_at"]),
            )
        )

    conn.close()

    return SignalsResponse(
        items=signals,
        total=total,
        page=page,
        page_size=page_size,
    )
