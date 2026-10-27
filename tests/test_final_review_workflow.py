"""Guarded application regressions from the independent final reviews."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


def run_review(name, case, tmp_path):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tests.monitoring.final_review_workflows",
            name,
            case,
            str(tmp_path / f"{name}-{case}.json"),
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


@pytest.mark.parametrize(
    "case", ["valid-first", "expired-first", "same-report", "valid-only", "identical"]
)
def test_same_selection_coupon_conflicts_survive_report_merging(case, tmp_path):
    run_review("coupon_conflict", case, tmp_path)


@pytest.mark.parametrize("case", ["retained", "fresh", "stale", "unknown"])
def test_fresh_price_crosses_with_valid_reused_definition(case, tmp_path):
    run_review("retained_definition", case, tmp_path)


@pytest.mark.parametrize(
    "case",
    [
        "shopify-numeric",
        "shopify-text",
        "shopify-report",
        "shopify-control",
        "ebay-numeric",
        "ebay-report",
        "ebay-control",
    ],
)
def test_adapter_claim_validation_preserves_valid_siblings(case, tmp_path):
    run_review("adapter_isolation", case, tmp_path)


@pytest.mark.parametrize(
    "case",
    [
        "client-secret",
        "aws",
        "aws-token",
        "google",
        "oauth",
        "aws-key",
        "access-token",
        "sku",
    ],
)
def test_credential_query_is_absent_from_persisted_feed(case, tmp_path):
    run_review("credential_pointer", case, tmp_path)
