"""Small actual Chrome layer over the connected guarded synthetic fixture."""

import argparse
import gzip
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
    session = "ticket12-" + uuid4().hex[:8]
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

    def api(path):
        return evaluate(f"fetch({json.dumps(path)}).then(r=>r.json())")

    def keyboard(selector):
        command("focus", selector)
        command("press", "Enter")

    def shot(name, selector):
        command("scrollintoview", selector)
        assert evaluate("document.documentElement.scrollWidth <= innerWidth")
        command("screenshot", str(args.artifacts / (name + ".png")))

    def step(action):
        payload = {"fixture_id": fixture["fixture_id"], "action": action}
        result = evaluate(
            f"fetch('/api/offline-workflow-step',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({json.dumps(payload)})}}).then(async r=>({{status:r.status,body:await r.json()}}))"
        )
        assert result["status"] == 200 and result["body"]["blocked_edges"] == [], result
        command("reload")
        command("wait", ".discovery-row")
        steps.append({"action": action, "observed": result["body"]})
        return result["body"]

    steps = []
    try:
        command("open", f"http://127.0.0.1:{args.port}/discover")
        command("set", "viewport", "1280", "900")
        command("wait", ".discovery-row")
        fixture = api("/api/offline-verification")
        assert fixture["fixture"] == "ticket12-connected-ui-v1"
        assert fixture["temporary_storage"] and not fixture["automatic_checks"]
        assert fixture["notifications_sent"] == 0 and fixture["blocked_edges"] == []
        before = api("/api/watches")
        feed = api("/api/discovery/watches")
        assert len(feed["candidates"]) == 5
        candidate = next(c for c in feed["candidates"] if c["source_listing_id"] == "addies")
        row = f'.discovery-row[data-candidate="{candidate["id"]}"]'
        (args.artifacts / "initial-snapshot.json").write_text(
            json.dumps(command("snapshot", "-i"), indent=2) + "\n"
        )
        shot("desktop-feed", "#page-title")
        keyboard(".discovery-preferences > summary")
        command("fill", "#discovery-width", "38")
        command("fill", "#discovery-colours", "mint, salmon")
        command("fill", "#discovery-budget", "150")
        keyboard("button:has-text('Save preferences')")
        command("wait", "text=Preferences saved.")
        command("reload")
        command("wait", ".discovery-row")
        keyboard(".discovery-preferences > summary")
        assert evaluate('document.querySelector("#discovery-budget").value') == "150"
        shot("desktop-preferences", ".discovery-preferences")
        keyboard(row + " > details > summary")
        keyboard(row + " .discovery-costs > summary")
        text = evaluate(f"document.querySelector({json.dumps(row)}).innerText")
        for expected in (
            "70.10",
            "cashback",
            "excluded from payable",
            "counted once",
            "Usual price unavailable",
            "No savings claim",
        ):
            assert expected in text, (expected, text)
        shot("desktop-prices", row + " .discovery-costs")
        benefit = row + " .discovery-costs > section:last-child > div:last-child"
        shot("desktop-cashback", benefit)
        command("set", "viewport", "375", "812")
        shot("narrow-cashback", benefit)
        command("set", "viewport", "1280", "900")
        keyboard(row + " .exact-tracking-editor > summary")
        command("fill", row + ' input[name="target_gbp"]', "60")
        command("check", row + ' input[name="webhook"]')
        keyboard(row + " button:has-text('Save delivered target')")
        command("wait", "text=Delivered target saved. Collection remains staged.")
        assert step("baseline")["notifications_sent"] == 0
        assert step("cross")["notifications_sent"] == 1
        assert step("duplicate")["notifications_sent"] == 1
        assert step("drop")["notifications_sent"] == 2
        shot("desktop-tracking", row + " .exact-tracking")
        # Narrow keyboard editing and reload retain the same intent and preferences.
        command("set", "viewport", "375", "812")
        keyboard(".discovery-preferences > summary")
        command("fill", "#discovery-width", "37.5")
        keyboard("button:has-text('Save preferences')")
        command("wait", "text=Preferences saved.")
        shot("narrow-preferences", ".discovery-preferences")
        keyboard(".discovery-preferences > summary")
        shot("narrow-feed", "#page-title")
        keyboard(row + " .exact-tracking-editor > summary")
        command("fill", row + ' input[name="target_gbp"]', "59")
        keyboard(row + " button:has-text('Save delivered target')")
        command("wait", "text=Delivered target saved. Collection remains staged.")
        command("fill", row + ' input[name="target_gbp"]', "60")
        keyboard(row + " button:has-text('Save delivered target')")
        command("wait", "text=Delivered target saved. Collection remains staged.")
        shot("narrow-tracking", row + " .exact-tracking")
        step("costs")
        san = '.discovery-row:has(h2:text-is("San Martin SN0144"))'
        keyboard(san + " > details > summary")
        keyboard(san + " .discovery-costs > summary")
        shot("narrow-conditional", san + " .discovery-costs")
        command("set", "viewport", "1280", "900")
        shot("desktop-conditional", san + " .discovery-costs")
        command("set", "viewport", "375", "812")
        step("coupon")
        keyboard(row + " > details > summary")
        visible = evaluate(f"document.querySelector({json.dumps(row)}).innerText")
        assert "45.10" in visible and "Dated observed low" in visible
        shot("narrow-prices", row + " .price-assessments")
        command("set", "viewport", "1280", "900")
        shot("desktop-assessments", row + " .price-assessments")
        keyboard(".source-coverage > summary")
        assert evaluate('document.querySelectorAll(".source-coverage [data-route]").length') == 16
        shot("desktop-coverage", ".source-coverage")
        command("set", "viewport", "375", "812")
        shot("narrow-coverage", ".source-coverage")
        # Actual form, API persistence, stale-write error, correction and invalidation.
        keyboard(row + " .identity-correction > summary")
        command("select", row + ' select[name="correction_field"]', "dial")
        command("fill", row + ' input[name="correction_value"]', "salmon")
        command("fill", row + ' input[name="correction_actor"]', "Synthetic reviewer")
        command(
            "fill", row + ' textarea[name="correction_rationale"]', "Offline selected dial mismatch"
        )
        keyboard(row + " button:has-text('Save identity correction')")
        command("wait", row + " .correction-state")
        shot("narrow-correction", row + " .identity-correction")
        changed = next(
            c for c in api("/api/discovery/watches")["candidates"] if c["id"] == candidate["id"]
        )
        assert changed["public_delivered_total"]["amount"] is None
        assert changed["offers"][0]["coupons"][0]["state"] == "invalidated"
        assert api("/api/discovery/tracking")["items"][0]["intended_values"]["dial"] == "salmon"
        correction_url = f"/api/discovery/candidates/{candidate['id']}/corrections/{candidate['configuration']['id']}"
        correction = api(correction_url)
        payload = {
            "expected_revision": correction["revision"],
            "capture_id": changed["capture_id"],
            "configuration_revision": changed["configuration"]["revision"],
            "field": "dial",
            "value": "blue",
            "state": "disputed",
            "actor": "Second synthetic editor",
            "rationale": "Force stale form conflict",
        }
        assert (
            evaluate(
                f"fetch({json.dumps(correction_url)},{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({json.dumps(payload)})}}).then(r=>r.status)"
            )
            == 201
        )
        command("fill", row + ' input[name="correction_value"]', "green")
        command(
            "fill", row + ' textarea[name="correction_rationale"]', "Stale form must be rejected"
        )
        keyboard(row + " button:has-text('Save identity correction')")
        command("wait", row + ' [role="alert"]')
        shot("narrow-error", row + " .identity-correction")
        command("set", "viewport", "1280", "900")
        shot("desktop-error", row + ' [role="alert"]')
        command("reload")
        command("wait", ".discovery-row")
        keyboard(row + " > details > summary")
        keyboard(row + " .identity-correction > summary")
        assert evaluate(
            f'document.querySelector({json.dumps(row)}).innerText.includes("Identity disputed")'
        )
        command("fill", row + ' input[name="correction_value"]', "salmon")
        command("fill", row + ' input[name="correction_actor"]', "Synthetic reviewer")
        command(
            "fill", row + ' textarea[name="correction_rationale"]', "Resolve the synthetic dispute"
        )
        keyboard(row + " button:has-text('Save identity correction')")
        command(
            "wait",
            "text=Correction saved. Target retained; dependent results withdrawn until fresh evidence qualifies.",
        )
        shot("desktop-correction", row + " .identity-correction")
        step("stale")
        assert api("/api/discovery/tracking")["items"][0]["assessment"]["state"] == "withheld"
        assert api("/api/watches") == before
        assert command("errors")["errors"] == []
        final = api("/api/offline-verification")
        assert final["blocked_edges"] == []
        (args.artifacts / "feed.json.gz").write_bytes(
            gzip.compress(json.dumps(api("/api/discovery/watches"), indent=2).encode(), mtime=0)
        )
        (args.artifacts / "receipt.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "gate": "passed",
                    "fixture": fixture,
                    "final_guard": final,
                    "steps": steps,
                    "viewports": ["1280x900", "375x812"],
                    "keyboard": "Enter opens evidence/preferences and submits preferences/targets/corrections at both widths",
                    "reload": "preferences, target, correction and error recovery checked",
                    "horizontal_overflow": False,
                    "browser_errors": [],
                    "buyer_feedback": "unproven",
                    "live_evidence": "unproven",
                    "feed_evidence": "feed.json.gz",
                },
                indent=2,
            )
            + "\n"
        )
        print(json.dumps({"passed": True, "session": session}))
    finally:
        command("close")


if __name__ == "__main__":
    main()
