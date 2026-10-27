"""Focused actual-browser check against discovery_ui_server; no browser installs.

Run with the fixture server on port 8877. Uses a fresh agent-browser session and
existing Google Chrome. Screenshots/receipts go to a temporary directory.
"""

import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8877)
    parser.add_argument(
        "--chrome", default="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    )
    parser.add_argument(
        "--artifacts",
        type=Path,
        default=Path(tempfile.gettempdir()) / "pricerecon-ticket02-browser",
    )
    args = parser.parse_args()
    args.artifacts.mkdir(exist_ok=True)
    config = args.artifacts / "config.json"
    config.write_text("{}\n")
    base = [
        "agent-browser",
        "--config",
        str(config),
        "--session",
        f"ticket02-discovery-{uuid4().hex[:8]}",
        "--executable-path",
        args.chrome,
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
        fixture = evaluate('fetch("/api/offline-verification").then(response => response.json())')
        assert fixture["fixture"] == "ticket02-discovery-ui", fixture
        assert fixture["temporary_storage"] is True, fixture
        assert fixture["automatic_checks"] is False, fixture
        assert fixture["blocked_edges"] == [], fixture
        assert fixture["notifications_sent"] == 0, fixture
        command("wait", "#page-title")
        assert evaluate('document.querySelector("h1")?.textContent') == "Find your next watch"
        command("wait", ".discovery-row")
        assert evaluate('document.querySelectorAll(".discovery-row").length') == 5
        assert evaluate('document.querySelectorAll(".discovery-picture svg").length') == 5
        assert evaluate('document.querySelectorAll(".discovery-row img").length') == 0
        assert evaluate('document.querySelectorAll(".discovery-total").length') == 5
        assert evaluate(
            'Array.from(document.querySelectorAll(".discovery-total")).every(e => e.textContent === "Total unknown")'
        )
        command("click", "summary:has-text('Edit preferences')")
        command("fill", "#discovery-width", "37.5")
        command("fill", "#discovery-colours", "mint, salmon")
        command("fill", "#discovery-budget", "120.25")
        command("select", "#discovery-colour-strength", "soft")
        command("focus", "button:has-text('Save preferences')")
        command("press", "Enter")
        command("wait", "text=Preferences saved.")
        command("reload")
        command("wait", ".discovery-row")
        command("click", "summary:has-text('Edit preferences')")
        assert evaluate('document.querySelector("#discovery-width").value') == "37.5"
        assert evaluate('document.querySelector("#discovery-budget").value') == "120.25"
        assert evaluate('document.querySelector("#discovery-colours").value') == "mint, salmon"
        assert evaluate('document.querySelectorAll(".discovery-row").length') == 5
        command("click", ".discovery-row:first-of-type > details > summary")
        assert evaluate('document.querySelector(".discovery-row:first-of-type details").open')
        assert evaluate('document.body.textContent.includes("Usual price unavailable")')
        assert evaluate('document.body.textContent.includes("No bargain alerts")')
        command("screenshot", str(args.artifacts / "desktop.png"), "--full")
        command("set", "viewport", "375", "812")
        command("screenshot", str(args.artifacts / "narrow.png"), "--full")
        assert evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        command("click", "button[aria-label='Open menu']")
        command("click", ".mobile-nav-panel a[href='/']")
        command("wait", "text=Saved wristwatch search")
        assert evaluate('document.body.textContent.includes("Paused saved search")')
        assert command("errors")["errors"] == []
        receipt = {
            "result": "passed",
            "fixture": "five unresolved original test leads",
            "fixture_identity_checked_before_writes": True,
            "gates": [
                "image-led feed",
                "keyboard save",
                "preferences survive reload",
                "expanded evidence",
                "375px no overflow",
                "legacy queue navigation",
            ],
            "buyer_acceptance": "unproven",
            "live_acquisition": "not attempted",
        }
        (args.artifacts / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(receipt))
    finally:
        command("close")


if __name__ == "__main__":
    main()
