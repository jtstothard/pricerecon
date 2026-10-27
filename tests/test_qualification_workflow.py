"""Fresh-process public application qualification acceptance."""

import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def run_qualification(name, shared_root=None):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "tests.monitoring.qualification_workflows", name]
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


def test_legacy_exact_flags_titles_and_generic_stock_remain_unresolved():
    run_qualification("legacy_abstention")


def test_named_cohort_separates_identity_selection_offer_and_comparison_with_honest_preferences():
    run_qualification("named_cohort")


def test_mismatches_conflicts_copy_ai_stock_and_market_cohorts_cannot_bypass_gates():
    run_qualification("traps")


def test_one_listing_retains_multiple_selected_offers_without_first_sku_price_transfer():
    run_qualification("multiple_variations")


def test_qualification_survives_fresh_process_and_price_change_revises_same_offer():
    with TemporaryDirectory(prefix="pricerecon-offline-") as root:
        Path(root, ".offline-monitoring").write_text("ticket01-test-storage\n")
        run_qualification("persist_before", root)
        run_qualification("persist_after", root)


def test_source_urls_context_mismatches_missing_times_and_http_writes_fail_closed():
    run_qualification("boundary_contexts")


def test_arbitrary_dictionary_cannot_enter_the_typed_evidence_report_boundary():
    run_qualification("untyped_report")


def test_additive_migration_keeps_old_leads_and_saved_rules_without_inventing_proof():
    run_qualification("migration")


def test_extreme_numeric_claim_is_a_parse_failure_without_crashing_or_creating_proof():
    run_qualification("numeric_safety")
