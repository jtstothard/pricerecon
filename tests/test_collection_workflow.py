"""Collection policy acceptance through isolated API/execution workflows."""

import os
import subprocess
import sys
from pathlib import Path


def run_collection(name, storage=None):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "tests.monitoring.collection_workflows", name]
        + ([str(storage)] if storage else []),
        cwd=root,
        env={
            "PYTHONPATH": os.pathsep.join([str(root / "src"), str(root)]),
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        capture_output=True,
        text=True,
        timeout=40,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_collection_requires_explicit_operating_policy_and_exposes_its_gate():
    run_collection("missing_policy")


def test_discovery_yields_to_tracking_and_persists_explicit_coverage_and_last_good():
    run_collection("shared_priority")


def test_real_http_attempts_count_auth_pages_and_retry_before_controlled_transport_send():
    run_collection("real_attempts")


def test_storage_exhaustion_rolls_back_candidate_evidence_and_withholds_alerts():
    run_collection("storage_exhaustion")


def test_existing_exact_target_verification_can_use_the_reserved_capacity_and_capture_send():
    run_collection("verification_priority")


def test_overlap_and_concurrent_sources_share_one_cap_and_source_lease():
    run_collection("concurrent")


def test_killed_process_resumes_once_without_refill_catchup_or_policy_label_bypass():
    from tempfile import TemporaryDirectory

    with TemporaryDirectory(prefix="pricerecon-offline-", dir="/tmp") as root:
        Path(root, ".offline-monitoring").write_text("ticket01-test-storage\n")
        run_collection("restart_before", root)
        run_collection("restart_after", root)


def test_legacy_execution_applies_supplied_storage_cap_before_snapshot_or_event_commit():
    run_collection("legacy_storage")


def test_detail_and_fallback_caps_apply_at_each_actual_transport_edge():
    run_collection("fallback_detail")


def test_failed_evidence_persistence_withholds_old_target_assessment_on_api_readback():
    run_collection("target_storage_readback")


def test_unbounded_browser_and_unsupplied_ai_are_gated_and_timeouts_are_finite():
    run_collection("optional_resources")
