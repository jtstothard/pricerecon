"""Actual Chrome proof of adapter evidence and mandatory-family coverage."""

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
    session = f"ticket11-evidence-{uuid4().hex[:8]}"
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
        assert fixture["fixture"] == "ticket11-source-evidence-ui"
        assert fixture["temporary_storage"] and not fixture["automatic_checks"]
        assert fixture["blocked_edges"] == [] and fixture["notifications_sent"] == 0
        command("focus", ".source-coverage > summary")
        command("press", "Enter")
        text = evaluate('document.querySelector(".source-coverage").textContent')
        for expected in (
            "AliExpress browser-first",
            "eBay Browse new / used",
            "Militado",
            "Watch Shop",
            "WatchGecko",
            "Sakura Watches",
            "San Martin independent retailer",
            "Brave API",
            "SearXNG",
            "Google Shopping",
            "HotUKDeals",
            "Reddit watch communities",
            "recognized Web Bot Auth signer",
            "history rights unqualified",
            "product_inspection_capped",
            "next_page_not_followed",
        ):
            assert expected in text, (expected, text)
        assert evaluate('document.querySelectorAll(".source-coverage [data-route]").length') == 16
        command("set", "viewport", "1280", "900")
        command("scrollintoview", ".source-coverage > summary")
        command("screenshot", str(args.artifacts / "desktop-source-coverage.png"))
        # Open one actual unbound AliExpress lead, using its observed row.
        command("click", '.discovery-row:has(h2:has-text("Addiesdive")) > details > summary')
        command(
            "scrollintoview", '.discovery-row:has(h2:has-text("Addiesdive")) .source-offer-evidence'
        )
        detail = evaluate(
            'Array.from(document.querySelectorAll(".discovery-row")).find(r=>r.querySelector("h2").textContent.includes("Addiesdive")).textContent'
        )
        for expected in (
            "Space Gray",
            "display_unbound",
            "Selected SKU unknown",
            "selected_sku_stock",
            "Total unknown",
        ):
            assert expected in detail, (expected, detail)
        command("screenshot", str(args.artifacts / "desktop-source-evidence.png"))
        command("set", "viewport", "375", "812")
        command("scrollintoview", '.discovery-row:has(h2:has-text("Addiesdive")) .source-offer-evidence h4')
        command("screenshot", str(args.artifacts / "narrow-source-evidence.png"))
        assert evaluate("document.documentElement.scrollWidth <= innerWidth")
        command("scrollintoview", ".source-coverage > summary")
        command("screenshot", str(args.artifacts / "narrow-source-coverage.png"))
        assert evaluate("document.documentElement.scrollWidth <= innerWidth")
        command("reload")
        command("wait", ".discovery-row")
        assert evaluate('document.querySelectorAll(".source-coverage [data-route]").length') == 16
        errors = command("errors")
        assert not errors.get("errors"), errors
        (args.artifacts / "receipt.json").write_text(
            json.dumps(
                {
                    "date": "2026-10-27",
                    "fixture": fixture,
                    "session": session,
                    "viewports": ["1280x900", "375x812"],
                    "horizontal_overflow": False,
                    "keyboard": "Enter expands mandatory-family coverage",
                    "reload": "persisted source coverage retained",
                    "errors": errors,
                    "snapshot": command("snapshot", "-i"),
                    "feed": evaluate('fetch("/api/discovery/watches").then(r=>r.json())'),
                    "limitations": "original synthetic payloads; no merchant/rights/freshness/buyer acceptance",
                },
                indent=2,
            )
            + "\n"
        )
        print(json.dumps({"passed": True, "artifacts": str(args.artifacts)}))
    finally:
        command("close")


if __name__ == "__main__":
    main()
