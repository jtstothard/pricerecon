"""Buyer-visible comparisons through guarded API/execution workflows."""


def run_assessment(name, storage=None):
    import os
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "tests.monitoring.assessment_workflows", name]
        + ([str(storage)] if storage else []),
        cwd=root,
        env={
            "PYTHONPATH": os.pathsep.join([str(root / "src"), str(root)]),
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_scoped_best_and_dated_low_are_independent_of_unavailable_usual_price():
    run_assessment("scoped")


def test_staleness_correction_and_same_label_policy_changes_retire_claims():
    run_assessment("invalidation")


def test_public_receipt_enters_same_comparison_and_target_crossing_with_legacy_opt_out():
    run_assessment("coupon_crossing")


def test_coupon_expiry_conditional_proof_and_interrupted_send_guards():
    run_assessment("coupon_guards")


def test_independent_configuration_paths_survive_sibling_correction_and_restart():
    run_assessment("siblings")


def test_conflicting_same_opportunity_routes_cannot_certify_a_low_or_current_winner():
    run_assessment("contradictions")


def test_personal_payment_cashback_app_and_advertised_codes_cannot_enter_public_comparison():
    run_assessment("restricted_coupons")


def test_coupons_terms_and_receipts_recaptured_before_channel_claim_cancel_pending_send():
    run_assessment("coupon_replaced")


def test_used_auction_quantity_destination_unknown_and_conditional_paths_stay_separate():
    run_assessment("cohorts")


def test_persisted_assessments_and_coupon_target_dedup_survive_fresh_process_restart():
    from pathlib import Path
    from tempfile import TemporaryDirectory

    with TemporaryDirectory(prefix="pricerecon-offline-", dir="/tmp") as root:
        Path(root, ".offline-monitoring").write_text("ticket01-test-storage\n")
        run_assessment("restart_before", root)
        run_assessment("restart_after", root)


def test_duplicate_captures_and_missing_failed_coverage_preserve_only_a_dated_low():
    run_assessment("duplicates_and_gaps")
