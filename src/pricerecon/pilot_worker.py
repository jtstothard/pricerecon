"""Isolated pilot execution seam. CLI exercises synthetic transport only.

Live CLI activation remains in pilot.preflight: unresolved source rights and
backup exclusions are blockers, not flags that this worker can manufacture.
Run in a fresh process: storage audit guards intentionally cannot be removed.
"""

import argparse
import asyncio
import json
import logging
import os
import shutil
import sys
import time
from pathlib import Path

import httpx

from pricerecon.models.collection import OperatingPolicy
from pricerecon.models.watches import SourceConfig
from pricerecon.pilot_bounds import MIB, PilotBounds, active_pilot, pilot_policy, pilot_transport

MARKER = "pricerecon-one-off-pilot-v1\n"


def install_storage_guard(root: Path) -> None:
    """Only one 32MiB SQLite file, in-memory journals/temp, no disk logs.

    Restrict every SQLite connection before its first statement, including
    connections opened by existing health/admission code. Reject ATTACH and
    changes to the storage pragmas. This is stronger than periodic disk polling:
    SQLite rejects a growing page before the file can cross its limit.
    """
    database = root / "pricerecon.db"

    def guard(event: str, args: tuple[object, ...]) -> None:
        if event == "sqlite3.connect":
            from pricerecon.db.connection import opening_isolated_connection

            if Path(str(args[0])).resolve() != database or not opening_isolated_connection.get():
                raise RuntimeError("pilot_database_escape")
        elif event == "open":
            mode, flags = args[1], args[2]
            writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
                isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT)
            )
            if writing:
                raise RuntimeError("pilot_file_write_denied")
        elif event in {"subprocess.Popen", "os.system", "os.posix_spawn"}:
            raise RuntimeError("pilot_external_process_denied")
        elif event in {"os.mkdir", "os.rename", "os.link", "os.symlink"}:
            raise RuntimeError("pilot_filesystem_mutation_denied")
        elif event in {
            "socket.connect",
            "socket.connect_ex",
            "socket.getaddrinfo",
            "socket.sendto",
        }:
            # This entrypoint is the controlled proof, never a live back door.
            raise RuntimeError("pilot_synthetic_network_denied")

    from pricerecon.db.connection import isolated_database

    isolated_database.set(database)
    sys.addaudithook(guard)
    # Never import scheduler, app startup, notifications, or watch executor here.
    # This acquisition-only process has no notification/account action entrypoint.
    logging.disable(logging.CRITICAL)
    sys.dont_write_bytecode = True


async def acquire_once(
    transport: httpx.AsyncBaseTransport, source: SourceConfig, policy: OperatingPolicy
) -> dict[str, object]:
    """Run the normal lifecycle, connector and normalizer under one grant.

    The caller supplies a source and transport only after eligibility review.
    Current CLI preflight is blocked; its offline check supplies synthetic values.
    No source content or credential values cross this receipt boundary.
    """
    from pricerecon.core.acquisition import acquire_sources
    from pricerecon.core.collection_policy import operating_policy
    from pricerecon.pilot_bounds import QUERIES

    started = time.monotonic()
    bounds = PilotBounds()
    token = active_pilot.set(bounds)
    transport_token = pilot_transport.set(transport)
    states: list[str] = []
    try:
        with operating_policy(policy):
            async with asyncio.timeout(1200):
                for query in QUERIES:
                    result = await acquire_sources(
                        [source],
                        query=query,
                        source_queries={},
                        filters={},
                        context_id="one-off-pilot",
                        purpose="discovery",
                    )
                    states.extend(outcome.state for outcome in result.outcomes)
                    if any(
                        state not in {"success", "success_empty", "partial"} for state in states
                    ):
                        break
                    del result
        state = next(
            (value for value in ("blocked", "capped", "failed", "partial") if value in states),
            "success_empty" if states == ["success_empty", "success_empty"] else "success",
        )
        return {
            "schema": "pricerecon.watch-pilot.v1",
            "code_version": "bounded-pilot-v1",
            "policy_version": policy.version,
            "state": state,
            "outcomes": states,
            "requests": bounds.requests,
            "pages": bounds.pages,
            "details": bounds.details,
            "response_bytes": bounds.response_bytes,
            "normalized_bytes": bounds.normalized_bytes,
            "log_bytes": 0,
            "duration_seconds": round(time.monotonic() - started, 3),
            "live_eligible": False,
        }
    finally:
        bounds.token = None
        active_pilot.reset(token)
        pilot_transport.reset(transport_token)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic", action="store_true", required=True)
    parser.add_argument("--synthetic-outcome", choices=("empty", "denied"), default="empty")
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    root = args.directory.resolve()
    if root.exists() or root.is_relative_to(Path(__file__).resolve().parents[2]):
        raise SystemExit("new external temporary run directory required")
    from tempfile import gettempdir

    if not any(
        root.is_relative_to(base) for base in (Path(gettempdir()).resolve(), Path("/tmp").resolve())
    ):
        raise SystemExit("run directory must be temporary")
    # Exclusive, persistent minimal tombstone: deleting merchant storage cannot
    # refill/restart this run. This contains no source data or credential value.
    with root.with_suffix(".consumed").open("x") as marker:
        marker.write("synthetic pilot consumed\n")
    root.mkdir(mode=0o700)
    (root / ".pilot-run").write_text(MARKER)
    previous = Path.cwd()
    os.chdir(root)
    receipt: dict[str, object] = {"schema": "pricerecon.watch-pilot.v1", "state": "failed"}
    try:
        install_storage_guard(root)
        from pricerecon.db.schema import init_db

        init_db(seed_sources=False)

        def synthetic(request: httpx.Request) -> httpx.Response:
            if args.synthetic_outcome == "denied":
                return httpx.Response(403, content=b"synthetic provider denial")
            if request.url.path == "/identity/v1/oauth2/token":
                return httpx.Response(
                    200, json={"access_token": "synthetic-memory-only", "expires_in": 3600}
                )
            return httpx.Response(200, json={"itemSummaries": []})

        receipt = asyncio.run(
            acquire_once(
                httpx.MockTransport(synthetic),
                SourceConfig(
                    connector="ebay",
                    enabled=True,
                    config={
                        "app_id": "synthetic-app",
                        "cert_id": "synthetic-cert",
                        "db_path": "pricerecon.db",
                        "evidence_use": {
                            "permission_reference": "synthetic controlled fixture",
                            "retention": "synthetic",
                        },
                    },
                ),
                pilot_policy(),
            )
        )
        receipt["physical_bytes"] = root.stat().st_blocks * 512 + sum(
            path.stat().st_blocks * 512 for path in root.iterdir()
        )
        if int(str(receipt["physical_bytes"])) > 50 * MIB:
            raise RuntimeError("pilot_physical_cap")
    finally:
        os.chdir(previous)
        shutil.rmtree(root)
        receipt["cleanup"] = not root.exists()
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
