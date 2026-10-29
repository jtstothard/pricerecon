"""Connected ticket12 proof, always in fresh audit-guarded application children."""

import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def run_workflow(name, storage):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "tests.monitoring.watch_workflow", name, str(storage)],
        cwd=root,
        env={
            "PYTHONPATH": os.pathsep.join([str(root / "src"), str(root)]),
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_five_watch_discovery_to_correction_and_alert_restart():
    with TemporaryDirectory(prefix="pricerecon-offline-", dir="/tmp") as directory:
        storage = Path(directory)
        (storage / ".offline-monitoring").write_text("ticket01-test-storage\n")
        run_workflow("connected", storage)
        run_workflow("resume", storage)
        receipt = json.loads((storage / "receipt.json").read_text())
        assert receipt["gates"]["fresh_process_withholding"] == "passed"


def test_temporary_legacy_backup_restore_and_repeatable_migration():
    with TemporaryDirectory(prefix="pricerecon-offline-", dir="/tmp") as directory:
        storage = Path(directory)
        (storage / ".offline-monitoring").write_text("ticket01-test-storage\n")
        run_workflow("recovery", storage)


def test_private_walkthrough_serves_real_attributed_images_without_qualifying_prices():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "tests.monitoring.watch_image_workflow"],
        cwd=root,
        env={
            "PYTHONPATH": os.pathsep.join([str(root / "src"), str(root)]),
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
