"""Actual desktop/narrow assertions via the existing guarded fixture driver."""

import json


def verify_assessments(command, evaluate, artifacts):
    command("wait", ".discovery-row")
    row = ".discovery-row:has(h2:text-is('Synthetic exact watch'))"
    command("click", row + " > details > summary")
    command("wait", row + " .price-assessments")
    visible = evaluate('document.querySelector(".price-assessments").innerText')
    for expected in (
        "Scoped price assessment",
        "GBP 45.10",
        "Dated observed low",
        "Usual price unavailable",
        "Personal price unavailable",
        "No savings claim",
        "Historical assessment",
        "Unchecked sources: scan",
    ):
        assert expected in visible, (expected, visible)
    command(
        "click", row + " .price-assessments > details[open] > div:first-of-type > details > summary"
    )
    text = evaluate('document.querySelector(".price-assessments").innerText')
    assert "public coupon" in text and "Synthetic verification data" in text
    evaluate('document.querySelector(".price-assessments").scrollIntoView({block:"start"})')
    command("screenshot", str(artifacts / "desktop-assessments.png"))
    command("set", "viewport", "375", "812")
    assert evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    command("screenshot", str(artifacts / "narrow-assessments.png"))
    command("reload")
    command("wait", ".discovery-row")
    command("click", row + " > details > summary")
    assert evaluate('document.querySelector(".price-assessments").innerText.includes("GBP 45.10")')
    assert command("errors")["errors"] == []
    (artifacts / "receipt.json").write_text(
        json.dumps(
            {
                "result": "passed",
                "fixture": "ticket08-assessment-ui",
                "desktop": "1280x900",
                "narrow": "375x812",
                "horizontal_overflow": False,
                "gates": [
                    "scoped coupon payable",
                    "retained dated low",
                    "historical assessment",
                    "independent unavailable gates",
                    "unchecked source",
                    "evidence",
                    "reload",
                ],
                "buyer_acceptance": "unproven",
                "live_evidence": "not attempted",
            },
            indent=2,
        )
        + "\n"
    )
