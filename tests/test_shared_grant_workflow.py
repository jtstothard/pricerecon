"""Shared grant regressions at the API, execution and controlled transport seams."""

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest


def run(module, case, *args):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", f"tests.monitoring.{module}", case, *map(str, args)],
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
    return result.stdout


@pytest.mark.parametrize("case", ["context_api", "context_scheduler", "legacy_no_grant", "redirect"])
def test_retained_shared_grant_probes(case, tmp_path):
    run("collection_merger_probe", case, tmp_path / f"{case}.json")


def test_retained_fresh_process_exhausted_grant_probe(tmp_path):
    with TemporaryDirectory(prefix="pricerecon-offline-", dir="/tmp") as root:
        Path(root, ".offline-monitoring").write_text("ticket01-test-storage\n")
        for case in ("process_seed", "process_resume"):
            run("collection_merger_probe", case, tmp_path / f"{case}.json", "--storage", root)


@pytest.mark.parametrize("case", [
    "remaining_none", "expired", "expired_first", "zero_elapsed", "zero_requests",
    "zero_provider", "scope_change",
    "concurrent_none", "transport", "missing", "invalid", "ambiguous", "legacy_intent",
    "migration_single", "migration_ambiguous",
])
def test_durable_shared_policy_boundary(case):
    run("shared_grant_workflows", case)


def test_zero_first_denial_survives_fresh_process():
    with TemporaryDirectory(prefix="pricerecon-offline-", dir="/tmp") as root:
        Path(root, ".offline-monitoring").write_text("ticket01-test-storage\n")
        run("shared_grant_workflows", "zero_seed", root)
        run("shared_grant_workflows", "zero_resume", root)


def test_independent_processes_share_the_same_source_lease_and_global_provider_cap():
    with TemporaryDirectory(prefix="pricerecon-offline-", dir="/tmp") as root:
        Path(root, ".offline-monitoring").write_text("ticket01-test-storage\n")
        run("shared_grant_workflows", "concurrent_seed", root)
        with ThreadPoolExecutor(max_workers=2) as pool:
            runs = [pool.submit(run, "shared_grant_workflows", "concurrent_resume", root)
                    for _ in range(2)]
            outputs = [result.result() for result in runs]
        assert sum("sends=1" in output for output in outputs) == 1
        run("shared_grant_workflows", "concurrent_inspect", root)
