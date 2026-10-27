"""History acceptance uses fresh guarded application processes only."""


def test_history_retains_initial_unchanged_rising_and_falling_exact_revisions():
    run_cost_history("observations")


def run_cost_history(name, storage=None):
    import os
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "tests.monitoring.history_workflows", name]
        + ([str(storage)] if storage else []),
        cwd=root,
        env={
            "PYTHONPATH": os.pathsep.join([str(root / "src"), str(root)]),
            "PYTHONDONTWRITEBYTECODE": "1",
            **({"TMPDIR": str(Path(storage).parent)} if storage else {}),
        },
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_history_distinguishes_duplicates_cache_partial_empty_failures_and_missing_periods():
    run_cost_history("gaps")


def test_copied_lineage_cannot_gain_independence_by_adding_an_extraction():
    run_cost_history("copied_lineage")


def test_additive_history_migration_preserves_seeded_data_and_exact_withdrawal_after_restart():
    from pathlib import Path
    from tempfile import TemporaryDirectory

    with TemporaryDirectory(prefix="pricerecon-offline-") as root:
        Path(root, ".offline-monitoring").write_text("ticket01-test-storage\n")
        for stage in ("migration_before", "migration_after", "invalidation_after"):
            run_cost_history(stage, root)


def test_purchase_basis_changes_and_unknown_or_malformed_evidence_never_create_price_changes():
    run_cost_history("basis_changes")


def test_copied_merchant_capture_on_another_source_remains_one_acquisition_lineage():
    run_cost_history("cross_route")


def test_new_offer_capture_can_reuse_retained_configuration_and_selection_definitions():
    run_cost_history("retained_definitions")
