"""Persistent connector health states."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from pricerecon.db.schema import DB_PATH
from pricerecon.models import SourceType


def get_db(path: Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def upsert_connector_health(
    connector_id: str,
    status: str,
    *,
    last_error: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO connector_health (connector_id, status, last_error, details_json, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(connector_id) DO UPDATE SET
            status = excluded.status,
            last_error = excluded.last_error,
            details_json = excluded.details_json,
            updated_at = excluded.updated_at
        """,
        (
            connector_id,
            status,
            last_error,
            json.dumps(details or {}),
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def list_connector_health() -> dict[str, dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT connector_id, status, last_error, details_json, updated_at FROM connector_health"
    )
    rows = cursor.fetchall()
    conn.close()
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        try:
            details = json.loads(row["details_json"] or "{}")
        except Exception:
            details = {}
        result[row["connector_id"]] = {
            "status": row["status"],
            "last_error": row["last_error"],
            "details": details,
            "updated_at": row["updated_at"],
        }
    return result


def source_status(
    connector_id: str, source_type: SourceType, enabled: bool, name: str
) -> dict[str, Any]:
    state = list_connector_health().get(connector_id, {})
    return {
        "connector": connector_id,
        "name": name,
        "source_type": source_type,
        "enabled": enabled,
        "status": state.get("status", "healthy" if enabled else "disabled"),
        "last_error": state.get("last_error"),
        "config": state.get("details", {}),
    }
