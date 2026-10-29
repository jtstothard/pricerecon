"""Source evidence acceptance uses only guarded fresh application children."""

import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory, gettempdir

import pytest


def run_source(name, storage=None):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "tests.monitoring.source_evidence_workflows", name]
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
        timeout=40,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_browser_leads_retain_selected_labels_unbound_price_and_capture_limits():
    run_source("aliexpress")


def test_browse_retains_auction_used_parent_price_and_missing_fields_without_defaults():
    run_source("ebay")


def test_independent_retailer_variants_keep_movement_price_and_missing_currency_separate():
    run_source("retailer")


@pytest.mark.parametrize("case", ["control", "malformed"])
def test_retailer_preserves_valid_siblings_and_actual_capture_bounds(case, tmp_path):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "docs/testing/artifacts/watch-source-evidence/merger/retailer_isolation_probe.py",
            case,
            str(tmp_path),
        ],
        cwd=root,
        env={
            "PYTHONPATH": os.pathsep.join([str(root / "src"), str(root)]),
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        capture_output=True,
        text=True,
        timeout=40,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_legacy_retailer_watch_still_uses_normal_search_without_discovery_use_policy():
    run_source("retailer_watch")


def test_missing_use_authority_and_real_browser_accounting_stop_before_transport():
    run_source("gates")


def test_browse_failure_keeps_route_prerequisites_and_last_good_capture():
    run_source("failure")


def test_every_mandatory_source_family_is_visible_without_any_acquisition():
    run_source("roster")


def test_adapter_evidence_and_limits_survive_fresh_process_without_refresh():
    with TemporaryDirectory(prefix="pricerecon-offline-") as storage:
        Path(storage, ".offline-monitoring").write_text("ticket01-test-storage\n")
        run_source("restart_seed", storage)
        run_source("restart_read", storage)


def test_source_destination_stock_and_shipping_claims_survive_without_qualifying_a_total():
    run_source("source_context")


@pytest.mark.parametrize("case", ["retry_admitted", "retry_capped", "malformed"])
def test_real_adapter_retry_cap_and_malformed_item_outcomes(case):
    run_source(case)


def test_truncated_product_evidence_is_visible_and_cannot_qualify():
    run_source("truncated")


def test_militado_signer_gate_cannot_be_replaced_by_a_fixture_permission_label():
    run_source("militado_gate")


def test_truncated_discovery_is_a_failed_capture_with_explicit_limits_not_an_empty_search():
    run_source("discovery_truncated")


def test_merged_assessments_cannot_promote_reviewed_adapter_leads_to_price_claims():
    run_source("assessment_interaction")


def test_captured_manufacturer_document_reaches_supported_identity_through_acquisition():
    run_source("manufacturer_document")


def test_unregistered_manufacturer_host_never_serves_manufacturer_provenance():
    run_source("manufacturer_host_gate")
