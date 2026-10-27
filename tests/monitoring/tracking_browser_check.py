"""Exact-target browser acceptance driven by the retained Chrome driver."""

import json


def run_tracking_browser(command, evaluate, artifacts, fixture):
    command("wait", ".discovery-row")
    snapshot = command("snapshot", "-i")
    (artifacts / "initial-snapshot.json").write_text(json.dumps(snapshot, indent=2) + "\n")
    assert evaluate('document.querySelectorAll(".discovery-row").length') == 5
    before = evaluate('fetch("/api/watches").then(r => r.json())')
    assert (
        evaluate('fetch("/api/discovery/tracking").then(r => r.json()).then(v => v.items.length)')
        == 0
    )
    candidate_id = evaluate(
        'fetch("/api/discovery/watches").then(r => r.json()).then(v => v.candidates.find(c => c.title === "Addiesdive AD2066 mint").id)'
    )
    row = f'.discovery-row[data-candidate="{candidate_id}"]'
    command("click", row + " .exact-tracking-editor > summary")
    command("fill", row + ' input[name="target_gbp"]', "60")
    command("check", row + ' input[name="webhook"]')
    command("focus", row + " button:has-text('Save delivered target')")
    command("press", "Enter")
    command("wait", "text=Delivered target saved. Collection remains staged.")
    command("reload")
    command("wait", ".exact-tracking-state")
    assert evaluate(
        'document.querySelector(".exact-tracking-state").textContent.includes("target £60")'
    )
    assert evaluate(
        'document.body.textContent.includes("Freshness and buyer eligibility policy have not been supplied")'
    )
    command("click", row + " .exact-tracking-editor > summary")
    command("fill", row + ' input[name="target_gbp"]', "55.25")
    command("click", row + " button:has-text('Save delivered target')")
    command("wait", "text=Delivered target saved. Collection remains staged.")
    assert (
        evaluate(
            'fetch("/api/discovery/tracking").then(r => r.json()).then(v => v.items[0].target_gbp)'
        )
        == "55.25"
    )
    command("fill", row + ' input[name="target_gbp"]', "60.00")
    command("click", row + " button:has-text('Save delivered target')")
    command("wait", "text=Delivered target saved. Collection remains staged.")
    assert (
        evaluate(
            'fetch("/api/offline-verification").then(r => r.json()).then(v => v.notifications_sent)'
        )
        == 0
    )
    results = []
    for action, expected in (("baseline", 0), ("cross", 1), ("duplicate", 1), ("drop", 2)):
        payload = json.dumps({"fixture_id": fixture["fixture_id"], "action": action})
        result = evaluate(
            f"fetch('/api/offline-tracking-step', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({payload})}}).then(async r => ({{status:r.status, body:await r.json()}}))"
        )
        assert result["status"] == 200, result
        assert result["body"]["notifications_sent"] == expected, result
        assert result["body"]["blocked_edges"] == []
        results.append({"action": action, "captured_sends": expected})
        command("reload")
        command("wait", ".exact-tracking-state")
        if action == "baseline":
            assert evaluate(
                'document.querySelector(".exact-tracking-state").textContent.includes("Above target")'
            )
        else:
            assert evaluate(
                'document.querySelector(".exact-tracking-state").textContent.includes("Eligible at target")'
            )
    command("click", row + " .exact-tracking-deliveries > summary")
    command("wait", "text=webhook: sent")
    assert evaluate('document.body.textContent.includes("exactly-once delivery is not guaranteed")')
    command("scrollintoview", row + " .exact-tracking")
    command("screenshot", str(artifacts / "desktop-tracking.png"))
    command("set", "viewport", "375", "812")
    command("scrollintoview", row + " .exact-tracking")
    command("screenshot", str(artifacts / "narrow-tracking.png"))
    assert evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    payload = json.dumps({"fixture_id": fixture["fixture_id"], "action": "stale"})
    result = evaluate(
        f"fetch('/api/offline-tracking-step', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({payload})}}).then(r => r.json())"
    )
    assert result["notifications_sent"] == 2
    command("reload")
    command("wait", ".exact-tracking-state")
    assert evaluate(
        'document.querySelector(".exact-tracking-state").textContent.includes("Alert withheld")'
    )
    assert evaluate(
        'document.querySelector(".exact-tracking-state").textContent.includes("Evidence is stale or expired")'
    )
    assert evaluate('fetch("/api/watches").then(r => r.json())') == before
    assert (
        evaluate(
            'fetch("/api/discovery/watches").then(r => r.json()).then(v => v.collection_state)'
        )
        == "staged"
    )
    assert command("errors")["errors"] == []
    receipt = {
        "result": "passed",
        "fixture": "ticket05-tracking-ui",
        "port": 8885,
        "fixture_identity_checked_before_writes": True,
        "temporary_storage": True,
        "gates": [
            "keyboard Track",
            "target editing and reload",
            "explicit channel choice",
            "policy withholding",
            "above target",
            "crossing",
            "duplicate route suppression",
            "further drop",
            "captured transport",
            "delivery explanation",
            "stale withholding",
            "375px no overflow",
            "legacy intent preserved",
            "staged collection",
        ],
        "steps": results,
        "blocked_edges": [],
        "captured_sends": 2,
        "viewports": ["1280x900", "375x812"],
        "buyer_acceptance": "unproven",
        "live_acquisition": "not attempted",
    }
    (artifacts / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))
