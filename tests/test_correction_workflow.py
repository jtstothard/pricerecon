"""Correction acceptance at the approved guarded application seams."""


def run_correction(name, module="tests.monitoring.correction_workflows"):
    import os
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", module, name],
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


def test_fresh_corrected_configuration_requalifies_alongside_unrelated_variant_after_restart():
    run_correction("merger_multi", "tests.monitoring.correction_scope_workflows")


def test_merger_single_configuration_positive_control_remains_supported_after_restart():
    run_correction("merger_single", "tests.monitoring.correction_scope_workflows")


def test_recorrection_rejects_unrelated_current_configuration_as_descendant_without_mutation():
    run_correction("foreign_descendant", "tests.monitoring.correction_scope_workflows")


def test_correction_preserves_other_candidates_exact_revisions_of_same_definition():
    run_correction("other_candidate", "tests.monitoring.correction_scope_workflows")


def test_recorrection_of_converged_definition_preserves_unrelated_selection_after_restart():
    run_correction("converged_descendants", "tests.monitoring.correction_scope_workflows")


def test_unrelated_fresh_matching_offer_cannot_certify_corrected_stale_cost_lineage_after_restart():
    run_correction("unrelated_valid_corrected_stale", "tests.monitoring.correction_scope_workflows")


def test_same_definition_multiple_offers_keep_fresh_descendant_while_withdrawing_stale_dependency():
    run_correction("shared_definition_offers", "tests.monitoring.correction_scope_workflows")


def test_multiple_corrections_qualify_and_release_only_their_own_target_intent_after_restart():
    run_correction("multiple_corrections", "tests.monitoring.correction_scope_workflows")


def test_unrelated_reproduced_coupon_keeps_its_own_correction_boundary_after_restart():
    run_correction("unrelated_coupon", "tests.monitoring.correction_scope_workflows")


def test_dispute_state_projects_only_to_the_disputed_configuration_descendants():
    run_correction("dispute_scope", "tests.monitoring.correction_scope_workflows")


def test_partial_acquisition_cannot_requalify_corrected_scope_or_withdraw_unrelated_variant():
    run_correction("partial_scope", "tests.monitoring.correction_scope_workflows")


def test_unrelated_supported_offer_cannot_supply_missing_corrected_merchant_selection_proof():
    run_correction("unsupported_scope", "tests.monitoring.correction_scope_workflows")


def test_overlapping_multi_configuration_acquisition_and_restart_replay_preserve_unrelated_variant():
    run_correction("overlap_scope", "tests.monitoring.correction_scope_workflows")


def test_target_created_on_descendant_requalifies_after_recorrection_without_rewriting_subject():
    run_correction("descendant_target", "tests.monitoring.correction_scope_workflows")


def test_valid_correction_cannot_release_another_journals_target_with_same_descendant_definition():
    run_correction("multiple_convergent_corrections", "tests.monitoring.correction_scope_workflows")


def test_historical_definition_member_is_not_a_current_correction_subject():
    run_correction("former_definition_member", "tests.monitoring.correction_scope_workflows")


def test_pre_correction_other_identity_history_and_target_are_not_reassigned_by_selection_reuse():
    run_correction("pre_correction_other_identity", "tests.monitoring.correction_scope_workflows")
