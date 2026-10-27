"""Retain the connected proof from fresh guarded children; no app imports."""

import argparse
import gzip
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory


def summarize(value):
    """Readable projection only; byte-complete API observations remain in gzip."""
    if isinstance(value, list):
        return [summarize(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {}
    for key, item in value.items():
        if key == "price_assessments":
            result[key] = [
                summarize(
                    {
                        name: detail
                        for name, detail in row.items()
                        if name
                        in {
                            "id",
                            "revision",
                            "historical",
                            "current_best",
                            "observed_low",
                            "usual_price",
                            "personal_price",
                            "savings",
                            "invalidation_reasons",
                        }
                    }
                )
                for row in item[-1:]
            ]
            result["retained_assessment_count"] = len(item)
            continue
        if key == "offer" and isinstance(item, dict):
            result[key] = {
                name: detail
                for name, detail in item.items()
                if name
                in {
                    "id",
                    "revision",
                    "item_price",
                    "currency",
                    "condition",
                    "purchase_mode",
                    "quantity",
                    "availability",
                    "merchant_key",
                    "variation_id",
                    "binding_revision",
                    "configuration_revision",
                }
            }
            continue
        if key == "costs":
            result[key] = [
                {
                    name: detail
                    for name, detail in row.items()
                    if name
                    in {
                        "id",
                        "revision",
                        "kind",
                        "state",
                        "total",
                        "known_subtotal",
                        "policy_version",
                        "configuration_revision",
                        "binding_revision",
                        "offer_revision",
                    }
                }
                for row in item
            ]
            continue
        if key in {
            "evidence",
            "context_evidence",
            "opportunity_evidence",
            "compatibility_evidence",
            "original_evidence",
            "claims",
        }:
            continue
        if key in {
            "application",
            "historical_resulting_cost",
            "resulting_cost",
            "original_configuration",
        } and isinstance(item, dict):
            result[key] = {
                name: summarize(detail)
                for name, detail in item.items()
                if name.startswith("expected_")
                or name
                in {
                    "id",
                    "revision",
                    "state",
                    "total",
                    "before_total",
                    "quoted_total",
                    "currency",
                    "result",
                    "applied_codes",
                }
            }
            result[key]["full_evidence"] = "raw-api.json.gz"
        elif key == "paths":
            result[key] = [
                {
                    name: detail
                    for name, detail in path.items()
                    if name
                    in {
                        "observation_id",
                        "offer_id",
                        "source",
                        "scenario_kind",
                        "observed_at",
                        "amount",
                        "currency",
                        "coupon_id",
                    }
                }
                for path in item
            ]
        else:
            result[key] = summarize(item)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    output = args.artifacts.resolve()
    output.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[2]
    results = []
    with TemporaryDirectory(prefix="pricerecon-offline-", dir="/tmp") as directory:
        storage = Path(directory)
        (storage / ".offline-monitoring").write_text("ticket01-test-storage\n")
        for phase in ("connected", "resume"):
            command = [sys.executable, "-m", "tests.monitoring.watch_workflow", phase, str(storage)]
            start = time.monotonic()
            result = subprocess.run(
                command,
                cwd=root,
                env={
                    "PYTHONPATH": os.pathsep.join([str(root / "src"), str(root)]),
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
                text=True,
                capture_output=True,
                timeout=60,
                check=False,
            )
            (output / f"{phase}.log").write_text(result.stdout + result.stderr)
            results.append(
                {
                    "phase": phase,
                    "command": command,
                    "exit": result.returncode,
                    "seconds": time.monotonic() - start,
                }
            )
            assert result.returncode == 0, result.stdout + result.stderr
        raw = (storage / "receipt.json").read_bytes()
        (output / "raw-api.json.gz").write_bytes(gzip.compress(raw, mtime=0))
        (output / "observed.json").write_text(
            json.dumps(summarize(json.loads(raw)), indent=2) + "\n"
        )
    with TemporaryDirectory(prefix="pricerecon-offline-", dir="/tmp") as directory:
        storage = Path(directory)
        (storage / ".offline-monitoring").write_text("ticket01-test-storage\n")
        command = [
            sys.executable,
            "-m",
            "tests.monitoring.watch_workflow",
            "recovery",
            str(storage),
        ]
        result = subprocess.run(
            command,
            cwd=root,
            env={
                "PYTHONPATH": os.pathsep.join([str(root / "src"), str(root)]),
                "PYTHONDONTWRITEBYTECODE": "1",
            },
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
        )
        (output / "recovery.log").write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stdout + result.stderr
        (output / "recovery.json").write_bytes((storage / "recovery.json").read_bytes())
        results.append({"phase": "recovery", "command": command, "exit": result.returncode})
    paths = subprocess.check_output(
        [
            "git",
            "ls-files",
            "src",
            "frontend/src",
            "frontend/package-lock.json",
            "tests/monitoring",
        ],
        cwd=root,
        text=True,
    ).splitlines()
    paths += [str(p.relative_to(root)) for p in root.glob("tests/monitoring/watch_workflow*.py")]
    paths += [str(p.relative_to(root)) for p in (root / "frontend/dist").rglob("*") if p.is_file()]
    hashes = {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in sorted(set(paths))
    }
    (output / "provenance.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_base_head": subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=root, text=True
                ).strip(),
                "integration_head": subprocess.check_output(
                    ["git", "rev-parse", "integration/watch-category-discovery"],
                    cwd=root,
                    text=True,
                ).strip(),
                "commands": results,
                "source_and_build_sha256": hashes,
                "fixture": "original invented values, controlled 2026-10-27 dates, no live history",
                "temporary_storage_removed": True,
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps({"passed": True, "artifacts": str(output)}))


if __name__ == "__main__":
    main()
