"""Actual browser acceptance via the retained driver, existing Chrome only."""

import json


def verify_history(command, evaluate, artifacts):
    command("wait", ".discovery-row")
    assert evaluate('document.querySelectorAll(".discovery-row").length') == 5
    row = ".discovery-row:has(h2:text-is('Addiesdive AD2066 mint'))"
    command("click", row + " > details > summary")
    command("click", row + " .discovery-history > summary")
    command("wait", row + " .discovery-history-observations")
    history_text = evaluate('document.querySelector(".discovery-history[open]").innerText')
    for expected in (
        "initial",
        "unchanged",
        "increased",
        "decreased",
        "Duplicate acquisition lineage",
        "cache reuse",
        "partial",
        "failed",
        "capped",
        "success empty",
        "unobserved interval",
        "age 28 hours",
        "current price and availability unknown",
        "Usual price unavailable",
        "No savings claim",
        "Synthetic test evidence; no real longitudinal history",
    ):
        assert expected in history_text, (expected, history_text)
    command(
        "click",
        row
        + " .discovery-history-observations > li:first-child > section:first-of-type > details > summary:text-is('Retained monetary, eligibility and context basis')",
    )
    assert evaluate(
        'document.querySelector(".discovery-history[open]").innerText.includes("synthetic-cost-fixture-v1")'
    )
    assert evaluate(
        'document.querySelector(".discovery-history[open]").innerText.includes("destination country")'
    )
    command(
        "click",
        row
        + " .discovery-history-observations > li:first-child details > summary:text-is('Exact revisions, policies and field evidence')",
    )
    assert evaluate(
        'document.querySelector(".discovery-history[open]").innerText.includes("observation-history-v1")'
    )
    assert evaluate('document.querySelectorAll(".discovery-history svg path").length') == 0
    evaluate('document.querySelector(".discovery-history[open]").scrollIntoView({block:"start"})')
    command("screenshot", str(artifacts / "desktop-history.png"))
    command("set", "viewport", "375", "812")
    assert evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    command("screenshot", str(artifacts / "narrow-history.png"))
    command("reload")
    command("wait", ".discovery-row")
    command("click", row + " > details > summary")
    command("click", row + " .discovery-history > summary")
    command("wait", row + " .discovery-history-observations")
    assert evaluate(
        'document.querySelector(".discovery-history[open]").innerText.includes("age 28 hours")'
    )
    command("click", "button[aria-label='Open menu']")
    command("click", ".mobile-nav-panel a[href='/']")
    command("wait", "text=Saved wristwatch search")
    assert evaluate('document.body.textContent.includes("Paused saved search")')
    assert command("errors")["errors"] == []
    receipt = {
        "result": "passed",
        "fixture": "ticket06-history-ui",
        "fixture_identity_checked_before_writes": True,
        "gates": [
            "initial unchanged increased decreased",
            "copied lineage",
            "cache partial failed capped empty",
            "unobserved intervals",
            "retained age 28 hours",
            "complete basis and policy evidence",
            "reload retained history",
            "375px no overflow",
            "legacy navigation",
        ],
        "buyer_acceptance": "unproven",
        "live_acquisition": "not attempted",
        "real_longitudinal_history": "not established",
    }
    (artifacts / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))
