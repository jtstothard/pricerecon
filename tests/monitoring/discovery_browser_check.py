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
    parser.add_argument("--qualification", action="store_true")
    parser.add_argument("--costs", action="store_true")
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
        command("set", "viewport", "1280", "900")
        fixture = evaluate('fetch("/api/offline-verification").then(response => response.json())')
        assert fixture["fixture"] == (
            "ticket04-cost-ui"
            if args.costs
            else "ticket03-qualification-ui" if args.qualification else "ticket02-discovery-ui"
        ), fixture
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
        if args.costs:
            assert evaluate(
                'Array.from(document.querySelectorAll(".discovery-total")).some(e => e.textContent.includes("GBP 50.10"))'
            )
            assert evaluate('document.body.textContent.includes("Verified at observation")')
            assert evaluate('document.body.textContent.includes("Conditional")')
        else:
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
        if args.qualification:
            assert evaluate('document.querySelectorAll(".discovery-qualification").length') == 5
            command(
                "click",
                ".discovery-row:has(h2:text-is('Addiesdive AD2066 mint')) > details > summary",
            )
            assert evaluate('document.body.textContent.includes("Synthetic merchant")')
            assert evaluate('document.body.textContent.includes("Configuration supported")')
            assert evaluate('document.body.textContent.includes("Selected variation supported")')
            assert evaluate('document.body.textContent.includes("Comparison unresolved")')
            command(
                "click",
                ".discovery-row:has(h2:text-is('Addiesdive AD2066 mint')) details details > summary:has-text('Field claims')",
            )
            assert evaluate(
                'Array.from(document.querySelectorAll(".discovery-row")).find(row => row.querySelector("h2").textContent === "Addiesdive AD2066 mint").innerText.includes("synthetic-fixture-v1")'
            )
            command(
                "click", ".discovery-row:has(h2:text-is('San Martin SN0144')) > details > summary"
            )
            assert evaluate('document.body.textContent.includes("configuration_mismatch")')
            assert evaluate('document.body.textContent.includes("Space Gray")')
            assert evaluate(
                'document.body.textContent.includes("Authenticity unknown; internal health unknown")'
            )
            assert evaluate('document.body.textContent.includes("used · auction")')
        if args.costs:
            command(
                "click",
                ".discovery-row:has(h2:text-is('Addiesdive AD2066 mint')) > details > summary",
            )
            command(
                "click",
                ".discovery-row:has(h2:text-is('Addiesdive AD2066 mint')) .discovery-costs > summary",
            )
            assert evaluate('document.body.textContent.includes("Merchant payable: GBP 50.10")')
            assert evaluate('document.body.textContent.includes("included in item")')
            assert evaluate('document.body.textContent.includes("cashback")')
            assert evaluate('document.body.textContent.includes("excluded from payable")')
            command(
                "click",
                ".discovery-row:has(h2:text-is('Addiesdive AD2066 mint')) .discovery-costs > section:first-of-type > details:has(> summary:text-is('Cost evidence and provenance (1)'))",
            )
            assert evaluate('document.body.innerText.includes("synthetic-cost-fixture-v1")')
            command(
                "click", ".discovery-row:has(h2:text-is('San Martin SN0144')) > details > summary"
            )
            command(
                "click",
                ".discovery-row:has(h2:text-is('San Martin SN0144')) .discovery-costs > summary",
            )
            assert evaluate(
                'document.body.textContent.includes("Synthetic shipping quote assumes the stated region")'
            )
            command(
                "click",
                ".discovery-row:has(h2:text-is('Casio MTP-B145D-2A2VEF')) > details > summary",
            )
            command(
                "click",
                ".discovery-row:has(h2:text-is('Casio MTP-B145D-2A2VEF')) .discovery-costs > summary",
            )
            assert evaluate('document.body.textContent.includes("Known subtotal: GBP 48.00")')
            assert evaluate('document.body.textContent.includes("shipping:unknown")')
        if not evaluate('document.querySelector(".discovery-row:first-of-type details").open'):
            command("click", ".discovery-row:first-of-type > details > summary")
        assert evaluate('document.querySelector(".discovery-row:first-of-type details").open')
        assert evaluate('document.body.textContent.includes("Usual price unavailable")')
        assert evaluate('document.body.textContent.includes("No bargain alerts")')
        if args.costs:
            evaluate(
                "Array.from(document.querySelectorAll('.discovery-row')).find(row => row.querySelector('h2').textContent === 'Addiesdive AD2066 mint').querySelector('.discovery-costs > summary').scrollIntoView({block: 'start'})"
            )
            command("screenshot", str(args.artifacts / "desktop-costs.png"))
        command("screenshot", str(args.artifacts / "desktop.png"), "--full")
        command("set", "viewport", "375", "812")
        if args.costs:
            evaluate(
                "Array.from(document.querySelectorAll('.discovery-row')).find(row => row.querySelector('h2').textContent === 'Addiesdive AD2066 mint').querySelector('.discovery-costs > summary').scrollIntoView({block: 'start'})"
            )
            command("screenshot", str(args.artifacts / "narrow-costs.png"))
        command("screenshot", str(args.artifacts / "narrow.png"), "--full")
        assert evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        command("click", "button[aria-label='Open menu']")
        command("click", ".mobile-nav-panel a[href='/']")
        command("wait", "text=Saved wristwatch search")
        assert evaluate('document.body.textContent.includes("Paused saved search")')
        assert command("errors")["errors"] == []
        receipt = {
            "result": "passed",
            "fixture": (
                "synthetic verified / conditional / unknown costs; Militado/Merkur abstain"
                if args.costs
                else (
                    "five named synthetic cases; Militado/Merkur abstain"
                    if args.qualification
                    else "five unresolved original test leads"
                )
            ),
            "fixture_identity_checked_before_writes": True,
            "gates": [
                "image-led feed",
                "keyboard save",
                "preferences survive reload",
                "expanded evidence",
                "375px no overflow",
                "legacy queue navigation",
                *(
                    [
                        "separate qualification states",
                        "visible synthetic provenance",
                        "rejected dial mapping",
                        "used auction separation",
                    ]
                    if args.qualification
                    else []
                ),
            ],
            "cost_workflow": args.costs,
            "viewports": ["1280x900", "375x812"],
            "cost_gates": (
                [
                    "verified / conditional / unknown",
                    "included VAT once",
                    "separate cashback",
                    "known subtotal",
                    "visible provenance",
                    "conditional assumptions",
                ]
                if args.costs
                else []
            ),
            "buyer_acceptance": "unproven",
            "live_acquisition": "not attempted",
        }
        (args.artifacts / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(receipt))
    finally:
        command("close")


if __name__ == "__main__":
    main()
