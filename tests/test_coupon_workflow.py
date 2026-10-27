"""Fresh-process coupon workflows through API and controlled execution."""


def run_coupon(name, storage=None):
    import os
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "tests.monitoring.coupon_workflows", name]
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


def test_advertised_coupon_is_persisted_without_reducing_public_no_coupon_total():
    run_coupon("advertised")


def test_exact_public_terms_establish_applicability_but_cannot_create_a_payable_reduction():
    run_coupon("applicable")


def test_reproduced_exact_basket_reconciles_complete_payable_without_replacing_public_base():
    run_coupon("reproduced")


def test_coupon_terms_evaluate_time_quantity_channel_membership_new_customer_and_stacks():
    run_coupon("eligibility_boundaries")


def test_receipt_rejects_changed_terms_context_lineage_incomplete_costs_and_advertisement_reuse():
    run_coupon("proof_boundaries")


def test_coupon_history_survives_restart_and_changed_evidence_invalidates_old_application():
    from pathlib import Path
    from tempfile import TemporaryDirectory

    with TemporaryDirectory(prefix="pricerecon-offline-") as root:
        Path(root, ".offline-monitoring").write_text("ticket01-test-storage\n")
        run_coupon("persistence_before", root)
        run_coupon("persistence_after", root)


def test_complete_basket_allocation_and_policy_lineage_are_required_for_reproduction():
    run_coupon("allocation_policy")


def test_explicit_whole_stack_app_channel_and_full_basket_commitment_reconcile_separately():
    run_coupon("stack_and_basket")


def test_replacing_selected_variation_invalidates_previous_application_and_totals():
    run_coupon("selection_replacement")


def test_conflicting_derivations_safe_pointers_malformed_inputs_and_staged_collection_fail_closed():
    run_coupon("conflicts_and_staging")
