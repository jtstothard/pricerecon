"""Additive storage for category leads and acquisition receipts, independent of Watches."""

import sqlite3
from contextlib import closing
from datetime import UTC, datetime

from pricerecon.categories.watches import interpret, lead_preference_fit
from pricerecon.db.schema import DB_PATH
from pricerecon.models.discovery import (
    DiscoveryCandidate,
    DiscoveryCapture,
    DiscoveryFeed,
    PreferenceProfile,
    PreferenceUpdate,
)


def init_discovery_tables(connection: sqlite3.Connection) -> None:
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS discovery_captures (
            capture_id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            captured_at TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS discovery_leads (
            candidate_id TEXT NOT NULL,
            capture_id TEXT NOT NULL REFERENCES discovery_captures(capture_id),
            payload_json TEXT NOT NULL,
            PRIMARY KEY (candidate_id, capture_id)
        );
        CREATE INDEX IF NOT EXISTS idx_discovery_category
            ON discovery_captures(category, captured_at);
        CREATE TABLE IF NOT EXISTS discovery_preferences (
            category TEXT PRIMARY KEY,
            revision INTEGER NOT NULL,
            payload_json TEXT NOT NULL
        );
        INSERT OR IGNORE INTO schema_migrations (version, description)
            VALUES ('1.3', 'Add staged category discovery captures, leads and preferences');
    """)


def save_capture(capture: DiscoveryCapture, candidates: list[DiscoveryCandidate]) -> None:
    with closing(sqlite3.connect(DB_PATH)) as connection, connection:
        connection.execute(
            "INSERT INTO discovery_captures VALUES (?, ?, ?, ?)",
            (
                capture.capture_id,
                capture.request.category,
                capture.captured_at.isoformat(),
                capture.model_dump_json(),
            ),
        )
        connection.executemany(
            "INSERT INTO discovery_leads VALUES (?, ?, ?)",
            [
                (candidate.id, capture.capture_id, candidate.model_dump_json())
                for candidate in candidates
            ],
        )


def get_feed() -> DiscoveryFeed:
    with closing(sqlite3.connect(DB_PATH)) as connection:
        captures = [
            DiscoveryCapture.model_validate_json(row[0])
            for row in connection.execute(
                "SELECT payload_json FROM discovery_captures WHERE category = 'watches' ORDER BY rowid DESC"
            )
        ]
        rows = connection.execute("SELECT payload_json FROM discovery_leads ORDER BY rowid DESC")
        latest: dict[str, DiscoveryCandidate] = {}
        for row in rows:
            candidate = DiscoveryCandidate.model_validate_json(row[0])
            latest.setdefault(candidate.id, candidate)
    preferences = get_preferences()
    candidates = [
        candidate.model_copy(
            update={
                "preference_fit": lead_preference_fit(preferences.values),
            }
        )
        for candidate in latest.values()
    ]
    return DiscoveryFeed(candidates=candidates, captures=captures, preferences=preferences)


class PreferenceConflict(Exception):
    """An edit used an older preference revision."""


def get_preferences() -> PreferenceProfile:
    with closing(sqlite3.connect(DB_PATH)) as connection:
        row = connection.execute(
            "SELECT payload_json FROM discovery_preferences WHERE category = 'watches'"
        ).fetchone()
    profile = PreferenceProfile.model_validate_json(row[0]) if row else PreferenceProfile()
    return profile.model_copy(update={"interpretation": interpret(profile.values)})


def save_preferences(update: PreferenceUpdate) -> PreferenceProfile:
    profile = PreferenceProfile(
        revision=update.expected_revision + 1,
        updated_at=datetime.now(UTC),
        values=update.values,
        interpretation=interpret(update.values),
    )
    with closing(sqlite3.connect(DB_PATH)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT revision FROM discovery_preferences WHERE category = 'watches'"
        ).fetchone()
        if (row[0] if row else 0) != update.expected_revision:
            raise PreferenceConflict()
        connection.execute(
            "INSERT INTO discovery_preferences VALUES ('watches', ?, ?) "
            "ON CONFLICT(category) DO UPDATE SET revision=excluded.revision, payload_json=excluded.payload_json",
            (profile.revision, profile.model_dump_json()),
        )
    return profile
