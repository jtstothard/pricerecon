"""Events API endpoints."""

from datetime import datetime

import sqlite3
import json
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from pricerecon.db.schema import DB_PATH
from pricerecon.models import Event, EventType, Severity

router = APIRouter()


# ============================================================================
# Pagination Response Models
# ============================================================================


class EventsResponse(BaseModel):
    """Response for events."""

    items: list[Event]
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


def event_row_to_model(row: sqlite3.Row) -> Event:
    """Convert database row to Event model."""
    event_json = json.loads(row["event_json"])
    return Event(
        id=row["id"],
        watch_id=row["watch_id"],
        event_type=EventType(row["event_type"]),
        severity=Severity(row["severity"]),
        listing_id=str(row["listing_key"]) if row["listing_key"] else None,
        data=event_json,
        timestamp=datetime.fromisoformat(row["created_at"]),
    )


# ============================================================================
# Events Endpoints
# ============================================================================


@router.get("/watches/{watch_id}/events", response_model=EventsResponse)
async def get_watch_events(
    watch_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
) -> EventsResponse:
    """Get events for a watch."""
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
    cursor.execute("SELECT COUNT(*) as total FROM events WHERE watch_id = ?", (watch_id,))
    total = cursor.fetchone()["total"]

    # Get paginated results
    skip = (page - 1) * page_size
    cursor.execute(
        """SELECT * FROM events 
           WHERE watch_id = ? 
           ORDER BY created_at DESC 
           LIMIT ? OFFSET ?""",
        (watch_id, page_size, skip),
    )
    rows = cursor.fetchall()

    events = [event_row_to_model(row) for row in rows]
    conn.close()

    return EventsResponse(
        items=events,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/events", response_model=EventsResponse)
async def get_all_events(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
) -> EventsResponse:
    """Get all events across all watches."""
    conn = get_db()
    cursor = conn.cursor()

    # Get total count
    cursor.execute("SELECT COUNT(*) as total FROM events")
    total = cursor.fetchone()["total"]

    # Get paginated results
    skip = (page - 1) * page_size
    cursor.execute(
        """SELECT * FROM events 
           ORDER BY created_at DESC 
           LIMIT ? OFFSET ?""",
        (page_size, skip),
    )
    rows = cursor.fetchall()

    events = [event_row_to_model(row) for row in rows]
    conn.close()

    return EventsResponse(
        items=events,
        total=total,
        page=page,
        page_size=page_size,
    )
