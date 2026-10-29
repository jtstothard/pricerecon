"""Tracking acceptance at the isolated API and normal execution seams."""

import os
import subprocess
import sys
from pathlib import Path


def run_tracking(name, storage=None):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "tests.monitoring.tracking_workflows", name]
        + ([str(storage)] if storage else []),
        cwd=root,
        env={
            "PYTHONPATH": os.pathsep.join([str(root / "src"), str(root)]),
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_discovery_to_exact_tracking_preserves_legacy_intent_and_validates_edits():
    run_tracking("intent")


def test_verified_crossing_further_drop_and_rise_recross_use_delivered_totals():
    run_tracking("crossings")


def test_unknown_stale_withdrawn_mismatched_and_recovery_evidence_withhold_alerts():
    run_tracking("withholding")


def test_offer_price_deduplication_survives_restart_and_duplicate_acquisition_routes():
    from tempfile import TemporaryDirectory

    with TemporaryDirectory(prefix="pricerecon-offline-", dir="/tmp") as root:
        Path(root, ".offline-monitoring").write_text("ticket01-test-storage\n")
        run_tracking("restart_before", root)
        run_tracking("restart_after", root)


def test_interrupted_presend_reservation_recovers_once_through_normal_execution():
    from tempfile import TemporaryDirectory

    with TemporaryDirectory(prefix="pricerecon-offline-", dir="/tmp") as root:
        Path(root, ".offline-monitoring").write_text("ticket01-test-storage\n")
        run_tracking("presend_before", root)
        run_tracking("presend_after", root)


def test_external_send_crash_is_durably_ambiguous_and_requires_explicit_reconciliation():
    from tempfile import TemporaryDirectory

    with TemporaryDirectory(prefix="pricerecon-offline-", dir="/tmp") as root:
        Path(root, ".offline-monitoring").write_text("ticket01-test-storage\n")
        run_tracking("ambiguous_before", root)
        run_tracking("ambiguous_after", root)


def test_delivery_serializes_target_edits_rechecks_preferences_and_invalidates_correction_seam():
    run_tracking("serialized_delivery")


def test_recovery_rechecks_full_policy_even_if_its_version_label_was_reused():
    run_tracking("changed_policy")


def test_conflicting_duplicate_routes_cannot_alert_and_no_channel_choice_cannot_send():
    run_tracking("route_conflict")


def test_schema_upgrade_preserves_existing_events_and_their_monotonic_identity():
    run_tracking("migration")


def test_merged_partial_and_cache_acquisition_contract_cannot_trigger_targets():
    run_tracking("combined_acquisition")


def test_merged_exact_revision_withdrawal_blocks_pending_target_delivery():
    run_tracking("combined_withdrawal")


def test_migration_seeds_events_sequence_for_empty_sequenced_legacy_tables(tmp_path):
    """m4 (adversarial review, 2026-10-29): legacy empty-but-sequenced events.

    Watch deletion cascaded legacy ``events`` rows away while unenforced
    foreign keys left orphan ``notifications.event_id`` rows behind, so a
    legacy database can arrive at the migration with an empty ``events``
    table whose ``sqlite_sequence`` row still holds a high watermark. The
    renamed table must never hand those ids out again.
    """
    import sqlite3

    from pricerecon.db.tracking import init_tracking_tables

    connection = sqlite3.connect(tmp_path / "legacy.db")
    try:
        connection.executescript("""
            CREATE TABLE schema_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT, version TEXT NOT NULL UNIQUE,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, description TEXT
            );
            CREATE TABLE watches (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE,
                query TEXT NOT NULL, category TEXT, config_json TEXT NOT NULL,
                last_check_at TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, watch_id INTEGER NOT NULL,
                event_type TEXT NOT NULL, listing_key TEXT, severity TEXT NOT NULL,
                event_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(watch_id) REFERENCES watches(id) ON DELETE CASCADE
            );
            CREATE TABLE notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT, event_id INTEGER NOT NULL,
                channel TEXT NOT NULL, status TEXT NOT NULL, message TEXT,
                error_message TEXT, sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(event_id) REFERENCES events(id)
            );
        """)
        # Thirty events once existed; the watch cascade removed every row while
        # the unenforced notifications FK left an orphan referencing event 30.
        connection.executemany(
            "INSERT INTO events(watch_id, event_type, severity, event_json)"
            " VALUES (1, 'new_listing', 'info', '{}')",
            [()] * 30,
        )
        connection.execute(
            "INSERT INTO notifications(event_id, channel, status)"
            " VALUES (30, 'webhook', 'sent')"
        )
        connection.execute("DELETE FROM events")
        assert connection.execute(
            "SELECT seq FROM sqlite_sequence WHERE name='events'"
        ).fetchone()[0] == 30

        init_tracking_tables(connection)

        seeded = connection.execute(
            "SELECT seq FROM sqlite_sequence WHERE name='events'"
        ).fetchone()
        assert seeded is not None, "renamed events must keep a seeded sequence row"
        assert seeded[0] == 30
        cursor = connection.execute(
            "INSERT INTO events(watch_id, event_type, severity, event_json)"
            " VALUES (NULL, 'target_reached', 'info', '{}')"
        )
        assert cursor.lastrowid == 31
        # The orphan still points at its dead event; it cannot mis-join a new one.
        assert connection.execute(
            "SELECT COUNT(*) FROM notifications n JOIN events e ON n.event_id = e.id"
        ).fetchone()[0] == 0
        # The migration stays idempotent for a second init pass.
        init_tracking_tables(connection)
    finally:
        connection.close()
