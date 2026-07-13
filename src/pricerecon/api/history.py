"""Price history API endpoints."""

from datetime import datetime
from decimal import Decimal

import sqlite3
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from pricerecon.db.schema import DB_PATH
from pricerecon.models import PriceHistory

router = APIRouter()


# ============================================================================
# Pagination Response Models
# ============================================================================


class HistoryResponse(BaseModel):
    """Response for price history."""

    items: list[PriceHistory]
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


def history_row_to_model(row: sqlite3.Row) -> PriceHistory:
    """Convert database row to PriceHistory model."""
    in_stock = row["in_stock"]
    return PriceHistory(
        id=row["id"],
        watch_id=row["watch_id"],
        listing_id=row["listing_key"],
        price=Decimal(row["price"]),
        currency=row["currency"],
        timestamp=datetime.fromisoformat(row["timestamp"]),
        in_stock=bool(in_stock) if in_stock is not None else None,
    )


# ============================================================================
# History Endpoints
# ============================================================================


@router.get("/watches/{watch_id}/history", response_model=HistoryResponse)
async def get_price_history(
    watch_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
) -> HistoryResponse:
    """Get price history for a watch."""
    conn = get_db()
    cursor = conn.cursor()

    # Check if watch exists
    cursor.execute("SELECT id FROM watches WHERE id = ?", (watch_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Watch {watch_id} not found"
        )

    # Get total count
    cursor.execute("SELECT COUNT(*) as total FROM price_history WHERE watch_id = ?", (watch_id,))
    total = cursor.fetchone()["total"]

    # Get paginated results
    skip = (page - 1) * page_size
    cursor.execute(
        """SELECT * FROM price_history 
           WHERE watch_id = ? 
           ORDER BY timestamp DESC 
           LIMIT ? OFFSET ?""",
        (watch_id, page_size, skip),
    )
    rows = cursor.fetchall()

    history = [history_row_to_model(row) for row in rows]
    conn.close()

    return HistoryResponse(
        items=history,
        total=total,
        page=page,
        page_size=page_size,
    )
