"""Actual loopback correction UI proof; synthetic data, no buyer acceptance."""

import json


def verify_corrections(command, evaluate, artifacts):
    command("wait", ".discovery-row")
    feed = evaluate('fetch("/api/discovery/watches").then(r=>r.json())')
    candidate = next(c for c in feed["candidates"] if c["title"] == "Addiesdive AD2066 mint")
    row = f'.discovery-row[data-candidate="{candidate["id"]}"]'
    before = evaluate('fetch("/api/watches").then(r=>r.json())')
    command("click", row + " .exact-tracking-editor > summary")
    command("fill", row + ' input[name="target_gbp"]', "60")
    command("focus", row + " button:has-text('Save delivered target')")
    command("press", "Enter")
    command("wait", "text=Delivered target saved. Collection remains staged.")
    command("click", row + " > details > summary")
    command("click", row + " .identity-correction > summary")
    command("select", row + ' select[name="correction_field"]', "dial")
    command("fill", row + ' input[name="correction_value"]', "salmon")
    command("fill", row + ' input[name="correction_actor"]', "Synthetic buyer")
    command(
        "fill", row + ' textarea[name="correction_rationale"]', "Synthetic selected dial mismatch"
    )
    command("focus", row + " button:has-text('Save identity correction')")
    command("press", "Enter")
    command("wait", row + " .correction-state")
    assert (
        evaluate(f'document.querySelector({json.dumps(row + " .discovery-total")}).textContent')
        == "Total unknown"
    )
    assert evaluate(
        f'document.querySelector({json.dumps(row + " .correction-lineage")}).textContent.includes("mint → salmon")'
    )
    assert evaluate(
        f'document.querySelector({json.dumps(row + " .exact-tracking-state")}).textContent.includes("target £60")'
    )
    command("click", row + " .correction-original > summary")
    assert evaluate(
        f'document.querySelector({json.dumps(row + " .correction-original")}).innerText.includes("dial: mint")'
    )
    command("click", row + " .discovery-history > summary")
    command("wait", row + " .discovery-history-observations")
    assert evaluate(
        f'document.querySelector({json.dumps(row + " .discovery-history")}).innerText.includes("invalidated")'
    )
    # Assert the same durable withdrawals exposed to the browser via API.
    after = evaluate('fetch("/api/discovery/watches").then(r=>r.json())')
    updated = next(c for c in after["candidates"] if c["id"] == candidate["id"])
    coupon = updated["offers"][0]["coupons"][0]
    assert coupon["state"] == "invalidated" and coupon["resulting_cost"] is None
    assert coupon["historical_resulting_cost"]["total"]["amount"] == "45.10"
    assert updated["offers"][0]["cost_scenarios"][0]["historical_total"]["amount"] == "50.10"
    command("screenshot", str(artifacts / "desktop-history-withdrawn.png"))
    evaluate(
        f'document.querySelector({json.dumps(row + " .identity-correction")}).scrollIntoView({{block:"start"}})'
    )
    command("screenshot", str(artifacts / "desktop-correction.png"))
    command("reload")
    command("wait", ".discovery-row")
    command("click", row + " > details > summary")
    command("click", row + " .identity-correction > summary")
    assert evaluate(
        f'document.querySelector({json.dumps(row + " .correction-state")}).textContent.includes("Synthetic buyer")'
    )
    # Another browser/API writer advances the revision while this form is open.
    correction_url = f"/api/discovery/candidates/{candidate['id']}/corrections/{candidate['configuration']['id']}"
    payload = {
        "expected_revision": 1,
        "capture_id": candidate["capture_id"],
        "configuration_revision": candidate["configuration"]["revision"],
        "field": "dial",
        "value": "blue",
        "state": "disputed",
        "actor": "Synthetic second editor",
        "rationale": "Conflicting correction",
    }
    result = evaluate(
        f'fetch({json.dumps(correction_url)}, {{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify({json.dumps(payload)})}}).then(r=>r.status)'
    )
    assert result == 201
    command("fill", row + ' input[name="correction_value"]', "green")
    command("fill", row + ' input[name="correction_actor"]', "Synthetic stale editor")
    command("fill", row + ' textarea[name="correction_rationale"]', "This stale edit must fail")
    command("click", row + " button:has-text('Save identity correction')")
    command("wait", row + ' [role="alert"]')
    assert evaluate(
        f'document.querySelector({json.dumps(row + " [role=alert]")}).textContent.includes("reload before saving")'
    )
    assert (
        evaluate(f"fetch({json.dumps(correction_url)}).then(r=>r.json()).then(v=>v.revision)") == 2
    )
    command("reload")
    command("wait", ".discovery-row")
    command("click", row + " > details > summary")
    command("click", row + " .identity-correction > summary")
    command("set", "viewport", "375", "812")
    assert evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert evaluate(
        f'document.querySelector({json.dumps(row + " .correction-state")}).textContent.includes("Identity disputed")'
    )
    command("fill", row + ' input[name="correction_value"]', "salmon")
    command("fill", row + ' input[name="correction_actor"]', "Synthetic buyer")
    command("fill", row + ' textarea[name="correction_rationale"]', "Resolve synthetic dispute")
    command("focus", row + " button:has-text('Save identity correction')")
    command("press", "Enter")
    command(
        "wait",
        "text=Correction saved. Target retained; dependent results withdrawn until fresh evidence qualifies.",
    )
    assert evaluate(
        f"fetch({json.dumps(correction_url)}).then(r=>r.json()).then(v=>[v.revision,v.state])"
    ) == [3, "corrected"]
    evaluate(
        f'document.querySelector({json.dumps(row + " .identity-correction")}).scrollIntoView({{block:"start"}})'
    )
    command("screenshot", str(artifacts / "narrow-correction.png"))
    assert evaluate('fetch("/api/watches").then(r=>r.json())') == before
    command("click", "button[aria-label='Open menu']")
    command("click", ".mobile-nav-panel a[href='/']")
    command("wait", "text=Saved wristwatch search")
    assert command("errors")["errors"] == []
    guard = evaluate('fetch("/api/offline-verification").then(r=>r.json())')
    assert guard["blocked_edges"] == [] and guard["notifications_sent"] == 0
    (artifacts / "receipt.json").write_text(
        json.dumps(
            {
                "result": "passed",
                "fixture": "ticket07-correction-ui",
                "fixture_identity_checked_before_writes": True,
                "gates": [
                    "keyboard target creation",
                    "field/value correction",
                    "attribution/rationale/lineage",
                    "original mint evidence retained",
                    "target retained",
                    "price/cost/coupon/history withdrawn",
                    "reload persistence",
                    "stale edit 409",
                    "dispute and resolution",
                    "375px no overflow",
                    "keyboard correction submission",
                    "legacy intent unchanged",
                    "no browser errors",
                ],
                "guard": guard,
                "buyer_acceptance": "unproven",
                "live_acquisition": "not attempted",
            },
            indent=2,
        )
        + "\n"
    )
