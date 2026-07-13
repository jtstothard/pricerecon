"""Data export API endpoints."""

import csv
import io
import json
import sqlite3
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Query, Response

from pricerecon.db.schema import DB_PATH

router = APIRouter()


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def export_to_json(data: list[dict], filename: str) -> Response:
    return Response(
        content=json.dumps(data, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def export_to_csv(data: list[dict], filename: str) -> Response:
    if not data:
        return Response(
            content="",
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export")
async def export_data(
    format: Literal["json", "csv"] = Query("json", description="Export format"),
    resource: Literal["watches", "listings", "history", "events", "all"] = Query(
        "all", description="Resource to export"
    ),
    watch_id: int | None = Query(None, description="Filter by watch ID"),
) -> Response:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    data: list[dict] = []
    filename = f"pricerecon_{resource}_{timestamp}.{format}"

    conn = get_db()
    cursor = conn.cursor()

    try:
        if resource in ["watches", "all"]:
            where_sql = "WHERE id = ?" if watch_id else ""
            params = [watch_id] if watch_id else []
            cursor.execute(
                f"""
                SELECT id, name, query, category, config_json,
                       created_at, updated_at, last_check_at
                FROM watches
                {where_sql}
                ORDER BY created_at DESC
                """,
                params,
            )
            for row in cursor.fetchall():
                config = json.loads(row["config_json"])
                data.append(
                    {
                        "resource": "watch",
                        "id": row["id"],
                        "name": row["name"],
                        "query": row["query"],
                        "category": row["category"],
                        "enabled": config.get("enabled", True),
                        "sources": config.get("sources", []),
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                        "last_check_at": row["last_check_at"],
                    }
                )

        if resource in ["listings", "all"] and not watch_id:
            cursor.execute("""
                SELECT watch_id, source, source_listing_id, title_raw,
                       price, currency, url, timestamp_seen
                FROM listings
                ORDER BY timestamp_seen DESC
                """)
            for row in cursor.fetchall():
                data.append(
                    {
                        "resource": "listing",
                        "watch_id": row["watch_id"],
                        "source": row["source"],
                        "source_listing_id": row["source_listing_id"],
                        "title_raw": row["title_raw"],
                        "price": row["price"],
                        "currency": row["currency"],
                        "url": row["url"],
                        "timestamp_seen": row["timestamp_seen"],
                    }
                )

        if resource in ["history", "all"]:
            where_sql = "WHERE watch_id = ?" if watch_id else ""
            params = [watch_id] if watch_id else []
            cursor.execute(
                f"""
                SELECT id, watch_id, listing_key, price, currency,
                       timestamp, in_stock
                FROM price_history
                {where_sql}
                ORDER BY timestamp DESC
                """,
                params,
            )
            for row in cursor.fetchall():
                data.append(
                    {
                        "resource": "price_history",
                        "id": row["id"],
                        "watch_id": row["watch_id"],
                        "listing_key": row["listing_key"],
                        "price": row["price"],
                        "currency": row["currency"],
                        "timestamp": row["timestamp"],
                        "in_stock": row["in_stock"],
                    }
                )

        if resource in ["events", "all"]:
            where_sql = "WHERE watch_id = ?" if watch_id else ""
            params = [watch_id] if watch_id else []
            cursor.execute(
                f"""
                SELECT id, watch_id, event_type, severity,
                       listing_key, created_at
                FROM events
                {where_sql}
                ORDER BY created_at DESC
                """,
                params,
            )
            for row in cursor.fetchall():
                data.append(
                    {
                        "resource": "event",
                        "id": row["id"],
                        "watch_id": row["watch_id"],
                        "event_type": row["event_type"],
                        "severity": row["severity"],
                        "listing_key": row["listing_key"],
                        "created_at": row["created_at"],
                    }
                )

        if format == "json":
            return export_to_json(data, filename)
        return export_to_csv(data, filename)
    finally:
        conn.close()
