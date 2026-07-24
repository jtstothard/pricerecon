"""Persistent connector health states."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
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
    path: Path | None = None,
) -> None:
    from datetime import timezone

    conn = get_db(path)
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
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def list_connector_health(path: Path | None = None) -> dict[str, dict[str, Any]]:
    conn = get_db(path)
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


def is_health_stale(
    connector_id: str, stale_threshold_seconds: int = 3600, path: Path | None = None
) -> bool:
    """Check if connector health state is stale and should be retried.

    A health state is considered stale if:
    - It's marked as auth_failed or error
    - It hasn't been updated in the last stale_threshold_seconds (default 1 hour)

    This allows transient failures to auto-recover after a cooldown period.
    """
    state = list_connector_health(path).get(connector_id, {})
    status = state.get("status")

    # If status is healthy, not stale
    if status in (None, "ok", "healthy"):
        return False

    # Check when the health state was last updated
    updated_at = state.get("updated_at")
    if not updated_at:
        # No timestamp, consider it stale
        return True

    try:
        updated_dt = datetime.fromisoformat(updated_at)
        now = datetime.now(timezone.utc)
        age = now - updated_dt

        # Stale if older than threshold
        return age.total_seconds() > stale_threshold_seconds
    except Exception:
        # Failed to parse timestamp, consider it stale
        return True
