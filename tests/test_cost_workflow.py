"""Fresh-process application delivered-cost acceptance."""

import os
import subprocess
import sys
from pathlib import Path
from tempfile import gettempdir


def run_cost(name, storage=None):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "tests.monitoring.cost_workflows", name]
        + ([str(storage)] if storage else []),
        cwd=root,
        env={
            "PYTHONPATH": os.pathsep.join([str(root / "src"), str(root)]),
            "PYTHONDONTWRITEBYTECODE": "1",
            # Keep the child's temporary root aligned with the parent's so the
            # harness guard (shared storage under the child's gettempdir())
            # holds in every shell, instead of only where TMPDIR is normalized.
            "TMPDIR": str(Path(gettempdir()).resolve()),
        },
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_exact_public_cost_counts_included_vat_once_and_keeps_acceptance_gates_separate():
    run_cost("included_vat")


def test_cost_history_survives_restart_quantity_basket_changes_and_repeated_capture():
    from tempfile import TemporaryDirectory

    with TemporaryDirectory(prefix="pricerecon-offline-") as root:
        Path(root, ".offline-monitoring").write_text("ticket01-test-storage\n")
        run_cost("persistence_before", root)
        run_cost("persistence_after", root)


def test_unbounded_missing_charges_currency_international_gbp_and_conflicts_withhold_totals():
    run_cost("missing_conflicting")


def test_import_liabilities_and_payment_fx_are_separate_from_merchant_and_customs_fx():
    run_cost("liabilities_fx")


def test_public_no_coupon_and_conditional_benefits_do_not_mix_or_use_item_budget_prefilters():
    run_cost("conditional_public")


def test_quantity_threshold_selection_and_buyer_context_changes_cannot_reuse_old_cost_proof():
    run_cost("context_changes")


def test_cost_evidence_boundaries_zero_conflicts_payers_and_sql_reads_fail_closed():
    run_cost("boundary_evidence")


def test_malformed_costs_are_acquisition_failures_and_default_execution_stays_staged():
    run_cost("invalid_acquisition")


def test_missing_conflicting_expired_fx_and_unknown_spread_withhold_but_bounded_estimate_is_conditional():
    run_cost("fx_conflicts")


def test_valid_extreme_decimal_representation_preserves_small_payable_component_without_crash():
    run_cost("exact_precision")


def test_allocated_basket_share_and_whole_basket_cost_cannot_masquerade_as_standalone_price():
    run_cost("basket_scope")


def test_many_valid_cost_extractions_retain_conflicts_without_crashing_or_voting():
    run_cost("repeated_cost_claims")


def test_equivalent_fx_quanta_preserve_payable_totals_evidence_history_and_budget_fit():
    run_cost("quantum_representations")


def test_equivalent_quantum_claims_retain_all_evidence_and_material_conflicts():
    run_cost("quantum_claims")
