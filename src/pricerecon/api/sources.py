"""Sources/connectors API endpoints."""

from __future__ import annotations

import json
import sqlite3

from fastapi import APIRouter

from pricerecon.core.connector_health import source_status
from pricerecon.db.schema import DB_PATH
from pricerecon.models import SourceInfo, SourceType

router = APIRouter()


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/sources", response_model=list[SourceInfo])
async def list_sources() -> list[SourceInfo]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sources")
    rows = cursor.fetchall()

    sources = []
    for row in rows:
        config = json.loads(row["config_json"])
        state = source_status(
            row["connector_id"],
            SourceType(row["source_type"]),
            bool(row["enabled"]),
            config.get("name", row["connector_id"]),
        )
        sources.append(
            SourceInfo(
                connector=row["connector_id"],
                name=config.get("name", row["connector_id"]),
                source_type=SourceType(row["source_type"]),
                enabled=bool(row["enabled"]),
                status=state["status"],
                last_error=state["last_error"],
                config=config,
            )
        )

    conn.close()
    return sources
