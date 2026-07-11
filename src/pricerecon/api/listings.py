"""Listings API endpoints."""

from datetime import datetime
from decimal import Decimal
from typing import Any

import sqlite3
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from pricerecon.db.schema import DB_PATH
from pricerecon.models import NormalizedListing, SourceType, Condition, StockState, VariantMatchConfidence

router = APIRouter()


# ============================================================================
# Pagination Response Models
# ============================================================================


class ListingsResponse(BaseModel):
    """Response for listings."""
    items: list[NormalizedListing]
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


def listing_row_to_model(row: sqlite3.Row) -> NormalizedListing:
    """Convert database row to NormalizedListing model."""
    listing_json = json.loads(row["listing_json"])
    return NormalizedListing(
        schema_version=listing_json.get("schema_version", "1.0"),
        source=row["source"],
        source_type=SourceType(listing_json.get("source_type", "retailer")),
        source_listing_id=row["source_listing_id"],
        title_raw=row["title_raw"],
        price=Decimal(row["price"]),
        currency=row["currency"],
        url=row["url"],
        timestamp_seen=datetime.fromisoformat(row["timestamp_seen"]),
        product_normalized=listing_json.get("product_normalized"),
        variant_normalized=listing_json.get("variant_normalized"),
        condition=Condition(listing_json["condition"]) if listing_json.get("condition") else None,
        condition_raw=listing_json.get("condition_raw"),
        shipping_cost=Decimal(listing_json["shipping_cost"]) if listing_json.get("shipping_cost") else None,
        total_landed_cost=Decimal(listing_json["total_landed_cost"]) if listing_json.get("total_landed_cost") else None,
        seller_or_store=listing_json.get("seller_or_store"),
        seller_feedback_score=listing_json.get("seller_feedback_score"),
        seller_feedback_pct=Decimal(listing_json["seller_feedback_pct"]) if listing_json.get("seller_feedback_pct") else None,
        location=listing_json.get("location"),
        in_stock=listing_json.get("in_stock"),
        stock_state=StockState(listing_json["stock_state"]) if listing_json.get("stock_state") else None,
        image_url=listing_json.get("image_url"),
        exact_variant_confirmed=listing_json.get("exact_variant_confirmed"),
        variant_match_confidence=VariantMatchConfidence(listing_json["variant_match_confidence"]) if listing_json.get("variant_match_confidence") else None,
        mismatch_flags=listing_json.get("mismatch_flags", []),
        risk_flags=listing_json.get("risk_flags", []),
        category=listing_json.get("category"),
    )


# ============================================================================
# Listings Endpoints
# ============================================================================


@router.get("/watches/{watch_id}/listings", response_model=ListingsResponse)
async def get_watch_listings(
    watch_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> ListingsResponse:
    """Get current listings for a watch."""
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
    
    # Get total count
    cursor.execute(
        "SELECT COUNT(*) as total FROM listings WHERE watch_id = ?",
        (watch_id,)
    )
    total = cursor.fetchone()["total"]
    
    # Get paginated results
    skip = (page - 1) * page_size
    cursor.execute(
        """SELECT * FROM listings 
           WHERE watch_id = ? 
           ORDER BY price ASC 
           LIMIT ? OFFSET ?""",
        (watch_id, page_size, skip)
    )
    rows = cursor.fetchall()
    
    listings = [listing_row_to_model(row) for row in rows]
    conn.close()
    
    return ListingsResponse(
        items=listings,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/listings/{listing_id}", response_model=NormalizedListing)
async def get_listing(
    watch_id: int,
    listing_id: str,
) -> NormalizedListing:
    """Get a specific listing by ID."""
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
    
    cursor.execute(
        """SELECT * FROM listings 
           WHERE watch_id = ? AND source_listing_id = ?""",
        (watch_id, listing_id)
    )
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Listing {listing_id} not found"
        )
    
    return listing_row_to_model(row)
