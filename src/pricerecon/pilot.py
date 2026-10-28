"""One approved watch pilot. Default preflight never loads credentials or opens a DB.

Evidence references are adjudicated outside this runner. A successful old request,
EvidenceUse string, CLI flag or newly authored approval file is not authority.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import TypedDict


class PilotReceipt(TypedDict):
    schema: str
    state: str
    gates: list[str]
    requests: int


def preflight() -> PilotReceipt:
    # The repository contains requirements, not the app-specific contract or
    # proof of exclusion from all backup/index/export tooling. Deliberately no
    # self-attestation switch: these gates require independent evidence review.
    return {
        "schema": "pricerecon.watch-pilot.v1",
        "state": "blocked",
        "gates": [
            "ebay_app_approval_unproven",
            "ebay_transient_retention_unproven",
            "backup_exclusion_unproven",
        ],
        "requests": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="execute only after all gates pass")
    parser.add_argument(
        "--offline-check", type=Path, help="controlled synthetic run in a new temporary directory"
    )
    args = parser.parse_args()
    if args.offline_check:
        if args.execute:
            parser.error("offline-check and execute are mutually exclusive")
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pricerecon.pilot_supervisor",
                "--synthetic",
                str(args.offline_check),
            ],
            capture_output=True,
            text=True,
            start_new_session=True,
            check=False,
        )
        if result.returncode == 0:
            print(result.stdout.strip())
        else:
            print(json.dumps({"schema": "pricerecon.watch-pilot.v1", "state": "supervisor_failed"}))
        return
    print(json.dumps(preflight(), sort_keys=True))


if __name__ == "__main__":
    main()
