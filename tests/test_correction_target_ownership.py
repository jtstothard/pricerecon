"""Target ownership is observable through correction/tracking APIs and restart."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("option", [None, "--reverse-journals", "--descendant-target"])
def test_recorrection_preserves_independent_target_and_follows_its_own_selections(tmp_path, option):
    root = Path(__file__).resolve().parents[1]
    command = [
        sys.executable,
        "-m",
        "tests.monitoring.correction_repair_merger_probe",
        str(tmp_path / "receipt.json"),
    ]
    if option is not None:
        command.append(option)
    result = subprocess.run(
        command,
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
