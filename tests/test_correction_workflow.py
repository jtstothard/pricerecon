"""Correction acceptance at the approved guarded application seams."""


def run_correction(name):
    import os
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "tests.monitoring.correction_workflows", name],
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


def test_correction_retains_original_facts_and_target_withdraws_all_dependents_and_survives_restart():
    run_correction("persistence")


def test_allowlisted_values_stale_edits_and_append_only_dispute_resolution():
    run_correction("validation")


def test_overlapping_acquisition_cannot_publish_old_prices_even_after_restart():
    run_correction("overlap")


def test_requalification_uses_new_compatible_evidence_and_new_history_without_transferring_old_prices():
    run_correction("requalification")


def test_inflight_delivery_rolls_back_entire_correction_and_accepted_sends_remain_historical():
    run_correction("inflight")


def test_correction_before_dispatch_withholds_pending_send_after_restart():
    run_correction("pending")


def test_second_correction_after_requalification_withdraws_new_configuration_as_well_as_original():
    run_correction("recorrection")


def test_new_extraction_of_pre_correction_capture_cannot_requalify_old_prices():
    run_correction("derived_replay")


def test_fresh_base_cannot_inherit_pre_correction_coupon_receipt_and_new_receipt_can_qualify():
    run_correction("coupon_replay")


def test_requalification_keeps_category_numeric_identity_equivalence_without_rewriting_intent():
    run_correction("numeric_identity")
