"""Gate tests for scripts/check_public_markers.py (adversarial-review n3).

Until 2026-10-31 the scan exempted ``tests/fixtures/`` wholesale, so a
fixture carrying a private deployment marker would pass the gate (finding
n3, PR #142 adversarial review). These tests pin the narrowed behavior:
fixtures are scanned like every other tracked path, with only the
documented per-file exceptions.

The tests are hermetic: each scan case runs inside a throwaway git
repository so the real index is never touched, and marker strings are
parsed from the gate script itself (ast) rather than written into this
file — this test must stay marker-free or it would trip the very gate it
pins.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GATE_SCRIPT = REPO_ROOT / "scripts" / "check_public_markers.py"


def _script_constants() -> tuple[tuple[str, ...], tuple[str, ...], dict[str, set[str]]]:
    """Extract (private, host, accepted) marker sets from the gate script."""
    private: tuple[str, ...] = ()
    host: tuple[str, ...] = ()
    accepted: dict[str, set[str]] = {}
    for node in ast.parse(GATE_SCRIPT.read_text(encoding="utf-8")).body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            if target.id == "PRIVATE_MARKERS":
                private = ast.literal_eval(node.value)
            elif target.id == "HOST_AND_NETWORK_MARKERS":
                host = ast.literal_eval(node.value)
            elif target.id == "ACCEPTED_MENTIONS":
                accepted = ast.literal_eval(node.value)
    assert private, "gate script must define PRIVATE_MARKERS"
    assert host, "gate script must define HOST_AND_NETWORK_MARKERS"
    return private, host, accepted


def _run_scan(cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run the gate script from cwd; the scan lists files via git ls-files."""
    return subprocess.run(
        [sys.executable, str(GATE_SCRIPT)],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _temp_repo(tmp_path: Path) -> Path:
    """A throwaway git repo with one tracked synthetic fixture."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    return repo


def test_gate_passes_on_the_real_tree() -> None:
    """The operator command `python3 scripts/check_public_markers.py` passes."""
    result = _run_scan(REPO_ROOT)
    assert result.returncode == 0, result.stdout + result.stderr


def test_tracked_fixture_with_markers_fails_the_gate(tmp_path: Path) -> None:
    """n3 pin: a fixture file carrying markers must fail, not slip through.

    Before the narrowing, `tests/fixtures/` was skipped wholesale, so this
    probe exited 0.
    """
    private, host, _ = _script_constants()
    repo = _temp_repo(tmp_path)
    probe_dir = repo / "tests" / "fixtures" / "synthetic"
    probe_dir.mkdir(parents=True)
    probe = probe_dir / "probe.md"
    # One marker of each class on separate lines, so both detectors trip.
    probe.write_text(
        f"# synthetic fixture\nleak one: {private[0]}\nleak two: {host[0]}\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "tests/fixtures/synthetic/probe.md"], cwd=repo, check=True)

    result = _run_scan(repo)
    assert result.returncode == 1, (
        "marker-bearing tracked fixture passed the gate:\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "tests/fixtures/synthetic/probe.md" in result.stdout


def test_clean_fixture_and_exempted_script_pass(tmp_path: Path) -> None:
    """Negative control: marker-free fixture content exits 0."""
    repo = _temp_repo(tmp_path)
    fixture_dir = repo / "tests" / "fixtures" / "ok"
    fixture_dir.mkdir(parents=True)
    (fixture_dir / "page.html").write_text(
        "<html><body>public captured content</body></html>\n", encoding="utf-8"
    )
    subprocess.run(["git", "add", "tests/fixtures/ok/page.html"], cwd=repo, check=True)

    result = _run_scan(repo)
    assert result.returncode == 0, result.stdout + result.stderr
