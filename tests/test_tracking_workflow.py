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
