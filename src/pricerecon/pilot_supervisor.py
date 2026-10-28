"""Detached deadline/cleanup owner for a pilot worker. No acquisition here."""

import argparse
import json
import os
import selectors
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from tempfile import gettempdir

from pricerecon.pilot_worker import MARKER


def supervise(
    command: list[str], root: Path, *, timeout: float = 1200, owner_pid: int | None = None
) -> dict[str, object]:
    """Bound worker lifetime and stdout even when its event loop is wedged.

    The CLI launches this owner in a separate session. Loss of the invoking
    orchestrator cannot cancel the deadline; TERM/INT still run finally cleanup.
    SIGKILL/host failure cannot promise deletion and never grants restart.
    """
    root = root.resolve()
    if root.exists():
        raise ValueError("new pilot root required")
    if not any(
        root.is_relative_to(base) for base in (Path(gettempdir()).resolve(), Path("/tmp").resolve())
    ):
        raise ValueError("temporary pilot root required")
    started = time.monotonic()
    child = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True
    )
    state = "failed"
    output = bytearray()
    try:
        if child.stdout is None:
            raise RuntimeError("pilot_output_pipe_required")
        with selectors.DefaultSelector() as selector:
            selector.register(child.stdout, selectors.EVENT_READ)
            while selector.get_map():
                if owner_pid is not None and os.getppid() != owner_pid:
                    state = "session_lost"
                    break
                remaining = timeout - (time.monotonic() - started)
                if remaining <= 0:
                    state = "deadline"
                    break
                for key, _ in selector.select(min(remaining, 0.2)):
                    chunk = os.read(key.fd, 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                    elif len(output) + len(chunk) > 1024 * 1024:
                        state = "log_cap"
                        break
                    else:
                        output.extend(chunk)
                if state == "log_cap":
                    break
            if not selector.get_map():
                child.wait(timeout=max(0.001, timeout - (time.monotonic() - started)))
                state = "completed" if child.returncode == 0 else "failed"
    except subprocess.TimeoutExpired:
        state = "deadline"
    finally:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.wait()
        if child.stdout:
            child.stdout.close()
        if root.exists():
            if (root / ".pilot-run").read_text() != MARKER:
                raise RuntimeError("pilot_cleanup_marker_missing")
            shutil.rmtree(root)
    receipt: dict[str, object] = {
        "schema": "pricerecon.watch-pilot.v1",
        "code_version": "bounded-pilot-v2",
        "policy_version": "live-pilot-plan-2026-10-28-v1",
        "state": state,
        "cleanup": not root.exists(),
        "log_bytes": len(output),
        "duration_seconds": round(time.monotonic() - started, 3),
    }
    # Only explicitly allow the minimal receipt fields across the process seam.
    # Never forward arbitrary child output, error text, titles, IDs or secrets.
    if state == "completed":
        try:
            parsed = json.loads(output)
        except (ValueError, UnicodeError):
            receipt["state"] = "invalid_receipt"
        else:
            if isinstance(parsed, dict):
                for field in ("review_verified", "exclusion_verified"):
                    if isinstance(parsed.get(field), bool):
                        receipt[field] = parsed[field]
                for field in (
                    "requests",
                    "pages",
                    "details",
                    "response_bytes",
                    "normalized_bytes",
                    "physical_bytes",
                ):
                    value = parsed.get(field)
                    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                        receipt[field] = value
                if parsed.get("state") in {
                    "success",
                    "success_empty",
                    "partial",
                    "failed",
                    "blocked",
                    "capped",
                }:
                    receipt["state"] = parsed["state"]
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--synthetic", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--review", type=Path)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    signal.signal(signal.SIGHUP, signal.SIG_IGN)

    def interrupted(signum: int, frame: object) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupted)
    command = [sys.executable, "-m", "pricerecon.pilot_worker"]
    duration = 1200.0
    if args.execute:
        from pricerecon.pilot_activation import resolve_review

        review = resolve_review(
            args.review,
            os.environ.get("EBAY_APP_ID", ""),
        )
        duration = review.remaining_seconds()
        command.extend(
            [
                "--execute",
                "--deadline-monotonic",
                str(time.monotonic() + duration),
                "--review",
                str(args.review),
            ]
        )
    else:
        command.append("--synthetic")
    command.append(str(args.directory))
    receipt = supervise(
        command,
        args.directory,
        owner_pid=os.getppid(),
        timeout=duration,
    )
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
