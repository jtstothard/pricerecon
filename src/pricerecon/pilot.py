"""One approved watch pilot: independently reviewed activation, no force switch."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from pricerecon.pilot_activation import (
    GRANT,
    ReviewError,
    credential_metadata,
    resolve_review,
)


def preflight(
    manifest: Path | None = None, public_key: Path | None = None, trusted_sha256: str | None = None
) -> dict[str, object]:
    """No provider calls or DB reads; secret presence only until review is supplied."""
    if not all((manifest, public_key, trusted_sha256)):
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
    gates: list[str] = []
    assert manifest is not None and public_key is not None and trusted_sha256 is not None
    try:
        resolve_review(manifest, public_key, trusted_sha256, os.environ.get("EBAY_APP_ID", ""))
    except ReviewError as exc:
        gates.append(str(exc))
    if not all(credential_metadata().values()):
        gates.append("existing_environment_credentials_required")
    if GRANT.exists():
        gates.append("shared_grant_already_consumed")
    if sys.platform != "darwin":
        gates.append("macos_private_tmp_required")
    from pricerecon.pilot_ui import DIST

    if not (DIST / "index.html").is_file():
        gates.append("pilot_frontend_build_required")
    return {
        "schema": "pricerecon.watch-pilot.v1",
        "state": "blocked" if gates else "ready_for_exclusion_check",
        "gates": gates,
        "requests": 0,
        "credentials": credential_metadata(),
        "storage": "macOS /private/tmp/*.noindex; exclusion verified before acquisition",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--review", type=Path)
    parser.add_argument("--reviewer-key", type=Path)
    parser.add_argument("--reviewer-key-sha256")
    parser.add_argument("--offline-check", type=Path)
    args = parser.parse_args()
    if args.offline_check and args.execute:
        parser.error("offline-check and execute are mutually exclusive")
    if args.offline_check:
        command = ["--synthetic", str(args.offline_check)]
    else:
        receipt = preflight(args.review, args.reviewer_key, args.reviewer_key_sha256)
        if not args.execute or receipt["state"] != "ready_for_exclusion_check":
            print(json.dumps(receipt, sort_keys=True))
            return
        root = Path("/private/tmp") / f"pricerecon-pilot-{uuid4().hex}.noindex"
        command = [
            "--execute",
            "--review",
            str(args.review.resolve()),
            "--reviewer-key",
            str(args.reviewer_key.resolve()),
            "--reviewer-key-sha256",
            args.reviewer_key_sha256,
            str(root),
        ]
    result = subprocess.run(
        [sys.executable, "-m", "pricerecon.pilot_supervisor", *command],
        capture_output=True,
        text=True,
        start_new_session=True,
        check=False,
    )
    if result.returncode == 0:
        print(result.stdout.strip())
    else:
        print(json.dumps({"schema": "pricerecon.watch-pilot.v1", "state": "supervisor_failed"}))


if __name__ == "__main__":
    main()
