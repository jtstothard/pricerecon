"""Focused actual Chrome verification using the retained agent-browser harness."""

import argparse
import json
import subprocess
from pathlib import Path
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    args.artifacts.mkdir(parents=True, exist_ok=True)
    config = args.artifacts / "config.json"
    config.write_text("{}\n")
    session = f"ticket10-collection-{uuid4().hex[:8]}"
    base = [
        "agent-browser",
        "--config",
        str(config),
        "--session",
        session,
        "--executable-path",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--allowed-domains",
        "127.0.0.1",
        "--json",
    ]

    def command(*parts):
        result = subprocess.run(
            [*base, *parts], text=True, capture_output=True, timeout=40, check=False
        )
        assert result.returncode == 0, result.stdout + result.stderr
        payload = json.loads(result.stdout)
        assert payload["success"], payload
        return payload["data"]

    def evaluate(script):
        return command("eval", script)["result"]

    try:
        command("open", f"http://127.0.0.1:{args.port}/discover")
        command("wait", ".discovery-row")
        fixture = evaluate('fetch("/api/offline-verification").then(r=>r.json())')
        assert fixture == {
            "fixture": "ticket10-collection-ui",
            "temporary_storage": True,
            "automatic_checks": False,
            "blocked_edges": [],
            "notifications_sent": 0,
        }
        command("focus", ".collection-coverage > summary")
        command("press", "Enter")
        command("wait", "text=Operating policy: supplied.")
        text = evaluate('document.querySelector(".collection-coverage").textContent')
        for expected in (
            "tracking capacity reserved:requests",
            "capped",
            "failed",
            "success empty",
            "3600 seconds old",
            "unrefreshed",
            "Transport health does not renew",
        ):
            assert expected in text, (expected, text)
        assert evaluate('document.querySelectorAll(".discovery-row").length') == 5
        # Blocked source remains explicit in the retained acquisition coverage.
        command("click", 'summary:has-text("Collection attempts")')
        assert evaluate('document.body.textContent.includes("fresh auth failed")')
        command("scrollintoview", ".collection-coverage")
        command("set", "viewport", "1280", "900")
        command("screenshot", str(args.artifacts / "desktop-collection.png"))
        snapshot = command("snapshot", "-i")
        command("set", "viewport", "375", "812")
        command("scrollintoview", ".collection-coverage")
        command("screenshot", str(args.artifacts / "narrow-collection.png"))
        assert evaluate("document.documentElement.scrollWidth <= innerWidth")
        state = evaluate('fetch("/api/discovery/collection").then(r=>r.json())')
        (args.artifacts / "receipt.json").write_text(
            json.dumps(
                {
                    "date": "2026-10-27",
                    "session": session,
                    "port": args.port,
                    "fixture": fixture,
                    "collection": state,
                    "snapshot": snapshot,
                    "keyboard": "Enter opens coverage",
                    "viewports": ["1280x900", "375x812"],
                    "horizontal_overflow": False,
                    "scope": "original synthetic fixture only; no live acceptance",
                },
                indent=2,
            )
            + "\n"
        )
        print(
            json.dumps(
                {
                    "session": session,
                    "artifacts": str(args.artifacts),
                    "states": "capped/blocked/failed/empty",
                }
            )
        )
    finally:
        command("close")


if __name__ == "__main__":
    main()
