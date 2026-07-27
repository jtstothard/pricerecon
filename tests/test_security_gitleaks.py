"""Regression test for gitleaks secret scanning integration.

This test ensures the .gitleaksignore file is maintained and that no new
secrets are committed to the repository. It validates the ignore file exists
and that running gitleaks returns zero findings when the ignore file is active.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

# Use the gitleaks binary at /tmp/gitleaks as per task reference
GITLEAKS_BINARY = "/tmp/gitleaks"
GITLEAKS_IGNORE_FILE = Path(".gitleaksignore")


@pytest.fixture
def repo_root() -> Path:
    """Return the repository root directory."""
    # Start from this test file and walk up to find .git
    current = Path(__file__).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    raise FileNotFoundError("Could not find repository root")


@pytest.fixture
def gitleaks_available(repo_root: Path) -> bool:
    """Check if gitleaks binary is available."""
    gitleaks_path = repo_root / GITLEAKS_BINARY
    return gitleaks_path.exists() and gitleaks_path.is_file()


def test_gitleaks_ignore_file_exists_and_non_empty(repo_root: Path) -> None:
    """Ensure .gitleaksignore exists and contains valid entries.

    This file is critical: it suppresses known false-positive findings
    from third-party test fixtures (Cloudflare RUM, Segment, Printess tokens).
    Removing or emptying it would cause CI to fail on existing fixtures.
    """
    ignore_file = repo_root / GITLEAKS_IGNORE_FILE

    assert ignore_file.exists(), (
        f".gitleaksignore not found at {ignore_file}. "
        "This file is required to suppress known false-positive tokens "
        "in test fixtures."
    )

    content = ignore_file.read_text()
    assert content.strip(), (
        f".gitleaksignore is empty at {ignore_file}. "
        "It must contain verified ignore entries for third-party fixtures."
    )

    # Check that the file has the expected header comment
    assert "# Gitleaks ignore - known third-party analytics tokens" in content, (
        ".gitleaksignore missing expected header comment. "
        "The header documents why entries exist and when they were verified."
    )


@pytest.mark.skipif(
    # We'll determine availability in the test itself for better error messages
    False,
    reason="Gitleaks binary not available - skipping integration test",
)
def test_gitleaks_detect_returns_zero_findings(repo_root: Path) -> None:
    """Run gitleaks scan and verify zero findings with ignore file active.

    This is a regression test: if new secrets are committed, this test will
    fail. The .gitleaksignore file suppresses known false positives from
    test fixtures, so any failure indicates a NEW secret leak.
    """
    gitleaks_path = repo_root / GITLEAKS_BINARY

    if not gitleaks_path.exists():
        pytest.skip(
            f"Gitleaks binary not found at {gitleaks_path}. "
            "Install it to run this integration test."
        )

    # Run gitleaks detect on the repository
    # --source .: scan current directory
    # --report-format sarif: output SARIF for GitHub code scanning
    # --report-path: where to write the SARIF report
    # --verbose: show details in CI output
    report_path = repo_root / "gitleaks-report.sarif"
    result = subprocess.run(
        [
            str(gitleaks_path),
            "detect",
            "--source",
            str(repo_root),
            "--report-format",
            "sarif",
            "--report-path",
            str(report_path),
            "--verbose",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    # Gitleaks returns non-zero exit code if any findings are detected
    assert result.returncode == 0, (
        f"gitleaks detected secrets! Exit code: {result.returncode}\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}\n"
        "This indicates NEW secrets in the repository. "
        "Check the SARIF report at gitleaks-report.sarif for details. "
        "If this is a false positive from a test fixture, add its SHA256 "
        "fingerprint to .gitleaksignore (get it from the gitleaks output)."
    )
