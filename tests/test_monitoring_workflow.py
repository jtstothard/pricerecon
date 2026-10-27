"""Run monitoring checks separately from unsafe legacy API fixtures."""

import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def run_scenario(name, shared_root=None, input_data=None):
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
        input=input_data,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_startup_and_api_checks_stay_inside_isolation():
    run_scenario("isolation")


def test_legacy_searches_settings_matching_and_notifications_survive_restart():
    run_scenario("legacy")


def test_form_title_edits_retain_saved_intent_through_api_and_restart():
    from tests.monitoring.workflows import LEGACY

    root = Path(__file__).resolve().parents[1]
    payload_module = (root / "frontend/src/lib/watchPayload.ts").as_uri()
    # Generate the real UI payload before the guarded application child starts.
    # Node's installed type stripping needs no frontend install or network.
    result = subprocess.run(
        [
            "node",
            "--input-type=module",
            "-e",
            f"""
import {{ readFileSync }} from 'node:fs';
import {{ formDataFromWatch, buildWatchEditPayload }} from {json.dumps(payload_module)};
const legacy = JSON.parse(readFileSync(0, 'utf8'));
const payloads = [true, false].map(enabled => {{
  const saved = {{ ...legacy, id: enabled ? 7 : 8, name: enabled ? legacy.name : 'Paused saved search', category: null, last_check_at: null, enabled }};
  return buildWatchEditPayload({{ ...formDataFromWatch(saved), display_title: 'Edited label' }}, saved);
}});
process.stdout.write(JSON.stringify(payloads));
""",
        ],
        input=json.dumps(LEGACY),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    run_scenario("form_edit", input_data=result.stdout)


def test_partial_source_failure_retains_last_good_evidence_without_recovery_alerts():
    run_scenario("partial_failure")


def test_unexpected_source_error_retains_last_good_evidence():
    run_scenario("unexpected_failure")


def test_fresh_auth_failure_skips_collection_without_erasing_last_good_evidence():
    run_scenario("auth_failure")


def test_successful_empty_source_removes_its_previous_listings():
    run_scenario("successful_empty")


def test_all_sources_failed_does_not_clear_the_existing_baseline():
    run_scenario("all_sources_failed")


def test_advanced_groups_match_tokens_and_phrases_with_exclusions():
    run_scenario("advanced_query")


def test_existing_spec_groups_replace_fallback_query_matching():
    run_scenario("spec_groups")


def test_watch_groups_apply_with_default_filters():
    run_scenario("default_groups")


def test_default_application_startup_still_checks_enabled_saved_searches():
    run_scenario("automatic_startup")


def test_simple_saved_search_filters_by_fallback_query_after_collection():
    run_scenario("simple_query")


def test_saved_time_window_uses_the_controlled_clock():
    run_scenario("schedule_window")


def test_new_process_retains_monitoring_state_without_repeating_notifications():
    with TemporaryDirectory(prefix="pricerecon-offline-") as shared_root:
        Path(shared_root, ".offline-monitoring").write_text("ticket01-test-storage\n")
        run_scenario("before_process_restart", shared_root)
        run_scenario("after_process_restart", shared_root)
