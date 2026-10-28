"""Isolated worker: verified activation or explicitly synthetic offline proof.

Run in a fresh process: storage audit guards intentionally cannot be removed.
Live startup rechecks session evidence review and local exclusion before
consuming the one shared grant or entering the normal acquisition seam.
"""

import argparse
import asyncio
import hashlib
import json
import logging
import math
import os
import shutil
import socket
import sys
import time
from pathlib import Path

import httpx

from pricerecon.models.collection import OperatingPolicy
from pricerecon.models.watches import SourceConfig
from pricerecon.pilot_bounds import MIB, PilotBounds, active_pilot, pilot_policy, pilot_transport

MARKER = "pricerecon-one-off-pilot-v1\n"


def install_storage_guard(
    root: Path, *, live_ips: set[str] | None = None, ui_port: int | None = None
) -> None:
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
            if live_ips is not None:
                if (
                    event == "socket.getaddrinfo"
                    and args[0] in ("api.ebay.com", b"api.ebay.com")
                    and args[1] == 443
                ):
                    return
                if event in {"socket.connect", "socket.connect_ex"}:
                    address = args[1]
                    if isinstance(address, tuple) and address[0] in live_ips and address[1] == 443:
                        return
            raise RuntimeError("pilot_network_denied")
        elif event == "socket.bind":
            address = args[1]
            if not (
                ui_port and isinstance(address, tuple) and address[:2] == ("127.0.0.1", ui_port)
            ):
                raise RuntimeError("pilot_bind_denied")

    from pricerecon.db.connection import isolated_database

    isolated_database.set(database)
    sys.addaudithook(guard)
    # Never start scheduler, application lifespan, or watch executor here.
    # This acquisition-only process has no notification/account action entrypoint.
    logging.disable(logging.CRITICAL)
    sys.dont_write_bytecode = True


async def acquire_once(
    transport: httpx.AsyncBaseTransport,
    source: SourceConfig,
    policy: OperatingPolicy,
    *,
    live_eligible: bool = False,
    duration: float = 1200,
    ui_port: int | None = None,
    ui_check: bool = False,
) -> dict[str, object]:
    """Run the normal lifecycle, connector and normalizer under one grant.

    The caller supplies a source and transport only after eligibility review.
    Live CLI resolves session evidence review; offline check supplies synthetic values.
    No source content or credential values cross this receipt boundary.
    """
    from pricerecon.core.collection_policy import operating_policy
    from pricerecon.core.discovery import execute_discovery
    from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest
    from pricerecon.pilot_bounds import QUERIES

    started = time.monotonic()
    bounds = PilotBounds(deadline=started + duration, live_eligible=live_eligible)
    token = active_pilot.set(bounds)
    transport_token = pilot_transport.set(transport)
    states: list[str] = []
    terminal = False
    ui_checked = False
    try:
        with operating_policy(policy):
            async with asyncio.timeout(duration):
                for query in QUERIES:
                    result = await execute_discovery(
                        DiscoveryRequest(query=query, sources=[source]),
                        admission=DiscoveryAdmission(
                            mode="pilot_session" if live_eligible else "offline_verification",
                            policy_reference=policy.version,
                            permission_reference=policy.permission_reference,
                            activation_reference=policy.scope_id,
                        ),
                    )
                    states.extend(outcome.state for outcome in result.outcomes)
                    if any(
                        state not in {"success", "success_empty", "partial"} for state in states
                    ):
                        terminal = True
                        del result
                        break
                    del result
                if not terminal and (ui_port or ui_check):
                    bounds.check()
                    from pricerecon.pilot_ui import check_ui, create_ui, serve_ui

                    app = create_ui(deadline=started + duration)
                    if ui_check:
                        await check_ui(app)
                        ui_checked = True
                    if ui_port:
                        await serve_ui(
                            app, ui_port, max(0, started + duration - time.monotonic() - 2)
                        )
        state = next(
            (value for value in ("blocked", "capped", "failed", "partial") if value in states),
            "success_empty" if states == ["success_empty", "success_empty"] else "success",
        )
        return {
            "schema": "pricerecon.watch-pilot.v1",
            "code_version": "bounded-pilot-v2",
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
            "live_eligible": live_eligible,
            "ui_checked": ui_checked,
        }
    finally:
        bounds.token = None
        active_pilot.reset(token)
        pilot_transport.reset(transport_token)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--synthetic", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--review", type=Path)
    parser.add_argument("--ui-check", action="store_true")
    parser.add_argument("--deadline-monotonic", type=float)
    parser.add_argument(
        "--synthetic-outcome", choices=("empty", "denied", "offer"), default="empty"
    )
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
    if args.synthetic:
        with root.with_suffix(".consumed").open("x") as marker:
            marker.write("synthetic pilot consumed\n")
    root.mkdir(mode=0o700)
    (root / ".pilot-run").write_text(MARKER)
    previous = Path.cwd()
    os.chdir(root)
    receipt: dict[str, object] = {"schema": "pricerecon.watch-pilot.v1", "state": "failed"}
    try:
        live_ips = None
        duration = 1200.0
        permission_reference = "synthetic controlled fixture"
        if args.execute:
            from pricerecon.pilot_activation import GRANT, prepare_excluded_root, resolve_review

            if args.review is None:
                raise RuntimeError("session_evidence_review_required")
            review = resolve_review(
                args.review,
                os.environ.get("EBAY_APP_ID", ""),
            )
            permission_reference = (
                "review-sha256:" + hashlib.sha256(args.review.read_bytes()).hexdigest()
            )
            prepare_excluded_root(root)
            if not os.environ.get("EBAY_CERT_ID"):
                raise RuntimeError("existing_environment_credentials_required")
            from pricerecon.pilot_ui import DIST

            if not (DIST / "index.html").is_file():
                raise RuntimeError("pilot_frontend_build_required")
            GRANT.parent.mkdir(parents=True, exist_ok=True)
            with GRANT.open("x") as consumed:
                consumed.write("watch-pilot-2026-10-28-once consumed; no restart\n")
                consumed.flush()
                os.fsync(consumed.fileno())
            live_ips = {
                str(item[4][0])
                for item in socket.getaddrinfo("api.ebay.com", 443, type=socket.SOCK_STREAM)
            }
            duration = review.remaining_seconds()
            if args.deadline_monotonic is not None:
                if not math.isfinite(args.deadline_monotonic):
                    raise RuntimeError("invalid_supervisor_deadline")
                duration = min(duration, args.deadline_monotonic - time.monotonic())
            if duration <= 0:
                raise RuntimeError("review_expired")
        # Import the UI and TLS dependencies before the filesystem guard. They
        # must never create caches or discover production application state.
        if args.execute or args.ui_check:
            import uvicorn  # noqa: F401

            import pricerecon.pilot_ui  # noqa: F401
        transport = httpx.AsyncHTTPTransport(retries=0, trust_env=False) if args.execute else None
        source = SourceConfig(
            connector="ebay",
            enabled=True,
            config={
                "app_id": os.environ.get("EBAY_APP_ID", "") if args.execute else "synthetic-app",
                "cert_id": os.environ.pop("EBAY_CERT_ID", "") if args.execute else "synthetic-cert",
                "db_path": "pricerecon.db",
                "evidence_use": {
                    "permission_reference": permission_reference,
                    "retention": "minimal_fields" if args.execute else "synthetic",
                },
            },
        )
        install_storage_guard(root, live_ips=live_ips, ui_port=8878 if args.execute else None)
        from pricerecon.db.schema import init_db

        init_db(seed_sources=False)

        def synthetic(request: httpx.Request) -> httpx.Response:
            if args.synthetic_outcome == "denied":
                return httpx.Response(403, content=b"synthetic provider denial")
            if request.url.path == "/identity/v1/oauth2/token":
                return httpx.Response(
                    200, json={"access_token": "synthetic-memory-only", "expires_in": 3600}
                )
            if args.synthetic_outcome == "offer":
                from pricerecon.pilot_bounds import QUERIES

                query = request.url.params.get("q", "")
                index = 0 if query == QUERIES[0] or "111" in request.url.path else 1
                item = {
                    "itemId": f"v1|{111 if index == 0 else 222}|0",
                    "title": QUERIES[index],
                    "itemWebUrl": "https://www.ebay.co.uk/itm/fixture",
                    "price": {"value": "10.00", "currency": "GBP"},
                    "conditionId": "1000",
                    "buyingOptions": ["FIXED_PRICE"],
                }
                return httpx.Response(200, json={"itemSummaries": [item]} if query else item)
            return httpx.Response(200, json={"itemSummaries": []})

        policy = pilot_policy()
        if args.execute:
            policy = policy.model_copy(
                update={
                    "permission_reference": permission_reference,
                    "retention_reference": permission_reference,
                }
            )
        receipt = asyncio.run(
            acquire_once(
                transport or httpx.MockTransport(synthetic),
                source,
                policy,
                live_eligible=args.execute,
                duration=duration,
                ui_port=8878 if args.execute else None,
                ui_check=args.ui_check,
            )
        )
        receipt["review_verified"] = args.execute
        receipt["exclusion_verified"] = args.execute
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
