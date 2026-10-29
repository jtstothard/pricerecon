"""Discovery verification always starts inside the fresh-process safety harness."""

import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def run_discovery(name, shared_root=None):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "tests.monitoring.discovery_workflows", name]
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
    assert result.returncode == 0, result.stdout + result.stderr


def test_category_acquisition_discovers_without_a_saved_watch():
    run_discovery("independent")


def test_origin_records_the_executed_source_query_even_for_a_legacy_reported_source_id():
    run_discovery("query_lineage")


def test_preferences_persist_and_unknown_dimensions_never_satisfy_limits():
    run_discovery("preferences")


def test_staged_denial_failure_coverage_and_leads_remain_visible_without_alerts():
    run_discovery("coverage")


def test_candidate_lineage_and_preferences_survive_a_fresh_process_without_reacquisition():
    with TemporaryDirectory(prefix="pricerecon-offline-") as shared_root:
        Path(shared_root, ".offline-monitoring").write_text("ticket01-test-storage\n")
        run_discovery("before_restart", shared_root)
        run_discovery("after_restart", shared_root)


def test_permitted_exact_depiction_survives_execution_api_and_restart():
    run_discovery("permitted_image")


def test_invalid_or_unmatched_images_fall_back_without_losing_leads():
    run_discovery("image_rejections")


def test_remote_reference_preserves_unresolved_target_without_price_qualification():
    run_discovery("remote_reference")
