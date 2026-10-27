"""Run monitoring checks separately from unsafe legacy API fixtures."""

import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from tests.monitoring.harness import MonitoringRequirementGap


def run_scenario(name, shared_root=None):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "tests.monitoring.workflows", name]
        + ([str(shared_root)] if shared_root else []),
        cwd=root,
        env={
            "PYTHONPATH": os.pathsep.join([str(root / "src"), str(root)]),
            "PYTHONDONTWRITEBYTECODE": "1",
            **({"TMPDIR": str(Path(shared_root).parent)} if shared_root else {}),
        },
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode == 3 and "UNMET_REQUIREMENT: " in result.stdout:
        raise MonitoringRequirementGap(result.stdout)
    assert result.returncode == 0, result.stdout + result.stderr


def test_startup_and_api_checks_stay_inside_isolation():
    run_scenario("isolation")


def test_legacy_searches_settings_matching_and_notifications_survive_restart():
    run_scenario("legacy")


@pytest.mark.xfail(
    strict=True,
    raises=MonitoringRequirementGap,
    reason="Baseline deletes failed-source snapshots and re-alerts on recovery",
)
def test_partial_source_failure_retains_last_good_evidence_without_recovery_alerts():
    run_scenario("partial_failure")


def test_default_application_startup_still_checks_enabled_saved_searches():
    run_scenario("automatic_startup")


@pytest.mark.xfail(
    strict=True,
    raises=MonitoringRequirementGap,
    reason="Baseline executor omits the ADR fallback query-title filter",
)
def test_simple_saved_search_filters_by_fallback_query_after_collection():
    run_scenario("simple_query")


def test_saved_time_window_uses_the_controlled_clock():
    run_scenario("schedule_window")


def test_new_process_retains_monitoring_state_without_repeating_notifications():
    with TemporaryDirectory(prefix="pricerecon-offline-") as shared_root:
        Path(shared_root, ".offline-monitoring").write_text("ticket01-test-storage\n")
        run_scenario("before_process_restart", shared_root)
        run_scenario("after_process_restart", shared_root)
