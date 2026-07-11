"""Watches CRUD API endpoints."""

from datetime import datetime
from decimal import Decimal
from typing import Any

import sqlite3
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from pricerecon.db.schema import DB_PATH
from pricerecon.models import (
    Watch,
    WatchCreate,
    WatchUpdate,
    WatchCheckResponse,
    ErrorResponse,
)

router = APIRouter()


# ============================================================================
# Scheduler Integration Helpers
# ============================================================================


def get_schedule_config(watch: Watch) -> dict[str, Any]:
    """Extract the schedule config from a watch model."""
    schedule = watch.schedule
    if hasattr(schedule, "model_dump"):
        return schedule.model_dump()
    return dict(schedule)


def sync_watch_scheduler(watch: Watch) -> None:
    """Add, update, or remove a watch in the live scheduler.

    Best-effort: if the scheduler is not running yet, this is a no-op.
    """
    try:
        from pricerecon.core.scheduler import get_scheduler
    except Exception:
        return

    try:
        scheduler = get_scheduler()
    except RuntimeError:
        return

    if not watch.enabled:
        scheduler.remove_watch(watch.id)
        return

    schedule = get_schedule_config(watch)
    scheduler.add_watch(
        watch.id,
        schedule.get("interval", "4h"),
        schedule.get("timezone", "UTC"),
        schedule.get("time_window"),
    )


# ============================================================================
# Pagination Response Models
# ============================================================================


class WatchListResponse(BaseModel):
    """Response for listing watches."""
    items: list[Watch]
    total: int
    page: int
    page_size: int


# ============================================================================
# Database Helpers
# ============================================================================


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def watch_row_to_model(row: sqlite3.Row) -> Watch:
    """Convert database row to Watch model."""
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


# ============================================================================
# Watch CRUD Endpoints
# ============================================================================


@router.get("/watches", response_model=WatchListResponse)
async def list_watches(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> WatchListResponse:
    """List all watches with pagination."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get total count
    cursor.execute("SELECT COUNT(*) as total FROM watches")
    total = cursor.fetchone()["total"]
    
    # Get paginated results
    skip = (page - 1) * page_size
    cursor.execute(
        "SELECT * FROM watches ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (page_size, skip)
    )
    rows = cursor.fetchall()
    
    watches = [watch_row_to_model(row) for row in rows]
    conn.close()
    
    return WatchListResponse(
        items=watches,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/watches", response_model=Watch, status_code=status.HTTP_201_CREATED)
async def create_watch(watch_create: WatchCreate) -> Watch:
    """Create a new watch."""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Build config JSON
        config = {
            "sources": [s.model_dump() for s in watch_create.sources],
            "filters": watch_create.filters.model_dump(),
            "schedule": watch_create.schedule.model_dump(),
            "grouping": watch_create.grouping.model_dump(),
            "notifications": watch_create.notifications.model_dump(mode="json"),
            "enabled": watch_create.enabled,
            "status": "active",
        }

        cursor.execute(
            """INSERT INTO watches (name, query, category, config_json, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                watch_create.name,
                watch_create.query,
                watch_create.category,
                json.dumps(config),
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat(),
            )
        )
        watch_id = cursor.lastrowid
        conn.commit()

        # Get the created watch
        cursor.execute("SELECT * FROM watches WHERE id = ?", (watch_id,))
        row = cursor.fetchone()
        watch = watch_row_to_model(row)
        conn.close()

        sync_watch_scheduler(watch)

        return watch
    except sqlite3.IntegrityError:
        cursor.execute("SELECT * FROM watches WHERE name = ?", (watch_create.name,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return watch_row_to_model(row)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Watch with name '{watch_create.name}' already exists"
        )
    except Exception as e:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create watch: {str(e)}"
        )


@router.get("/watches/{watch_id}", response_model=Watch)
async def get_watch(watch_id: int) -> Watch:
    """Get watch details by ID."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM watches WHERE id = ?", (watch_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Watch {watch_id} not found"
        )
    
    return watch_row_to_model(row)


@router.put("/watches/{watch_id}", response_model=Watch)
async def update_watch(watch_id: int, watch_update: WatchUpdate) -> Watch:
    """Update a watch."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if watch exists
    cursor.execute("SELECT * FROM watches WHERE id = ?", (watch_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Watch {watch_id} not found"
        )
    
    try:
        # Build config JSON
        config = {
            "sources": [s.model_dump() for s in watch_update.sources],
            "filters": watch_update.filters.model_dump(),
            "schedule": watch_update.schedule.model_dump(),
            "grouping": watch_update.grouping.model_dump(),
            "notifications": watch_update.notifications.model_dump(mode="json"),
            "enabled": watch_update.enabled,
            "status": json.loads(row["config_json"]).get("status", "active"),  # Preserve existing status
        }
        
        cursor.execute(
            """UPDATE watches 
               SET name = ?, query = ?, category = ?, config_json = ?, updated_at = ?
               WHERE id = ?""",
            (
                watch_update.name,
                watch_update.query,
                watch_update.category,
                json.dumps(config),
                datetime.utcnow().isoformat(),
                watch_id,
            )
        )
        conn.commit()
        
        # Get the updated watch
        cursor.execute("SELECT * FROM watches WHERE id = ?", (watch_id,))
        row = cursor.fetchone()
        watch = watch_row_to_model(row)
        conn.close()

        sync_watch_scheduler(watch)
        
        return watch
    except Exception as e:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update watch: {str(e)}"
        )


@router.delete("/watches/{watch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watch(watch_id: int) -> None:
    """Delete a watch."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if watch exists
    cursor.execute("SELECT id FROM watches WHERE id = ?", (watch_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Watch {watch_id} not found"
        )
    
    cursor.execute("DELETE FROM watches WHERE id = ?", (watch_id,))
    conn.commit()
    conn.close()

    try:
        from pricerecon.core.scheduler import get_scheduler
        scheduler = get_scheduler()
        scheduler.remove_watch(watch_id)
    except Exception:
        pass


# ============================================================================
# Watch Trigger Endpoint
# ============================================================================


@router.post("/watches/{watch_id}/check", response_model=WatchCheckResponse)
async def trigger_watch_check(watch_id: int) -> WatchCheckResponse:
    """Trigger an immediate check for a watch."""
    from pricerecon.core.watch_executor import execute_watch

    # Run the check
    result = await execute_watch(watch_id)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Unknown error")
        )

    # Update last_check timestamp
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE watches SET last_check_at = ? WHERE id = ?",
        (datetime.utcnow().isoformat(), watch_id)
    )
    conn.commit()
    conn.close()

    return WatchCheckResponse(
        watch_id=watch_id,
        status="completed",
        message=f"Check completed: {result['listings_found']} listings found",
        started_at=datetime.utcnow(),
        result=result,
    )
