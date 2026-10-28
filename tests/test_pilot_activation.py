"""Activation proof uses an independent fixture reviewer, never live providers."""

import hashlib
import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from pricerecon.pilot_activation import ReviewError, resolve_review


def session_review(tmp_path):
    from pricerecon.pilot_activation import envelope_digest

    documents = []
    for kind in ("app_approval", "transient_use"):
        artifact = tmp_path / (kind + ".txt")
        artifact.write_text("Independent synthetic external evidence fixture: " + kind)
        documents.append(
            {
                "kind": kind,
                "file": artifact.name,
                "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                "issuer": "https://developer.ebay.com/fixture",
                "reviewed_scope": (
                    "fixture app-specific approval"
                    if kind == "app_approval"
                    else "fixture transient display and deletion within retention_seconds"
                ),
            }
        )
    review = {
        "schema": "pricerecon.pilot-review.v1",
        "app_sha256": hashlib.sha256(b"fixture-app").hexdigest(),
        "purpose": "watch-pilot-2026-10-28-once",
        "envelope_sha256": envelope_digest(),
        "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        "operator_started_at": datetime.now(UTC).isoformat(),
        "retention_seconds": 1200,
        "documents": documents,
        "reviewer": "parent active session fixture",
        "source_use": "eBay Browse UK transient comparison display",
        "reviewed_at": datetime.now(UTC).isoformat(),
    }
    manifest = tmp_path / "review.json"

    def save():
        manifest.write_text(json.dumps(review))

    save()
    return manifest, review, save


def test_session_review_binds_external_bytes_app_purpose_envelope_and_expiry(tmp_path):
    manifest, review, save = session_review(tmp_path)
    assert resolve_review(manifest, "fixture-app").retention_seconds == 1200
    for field, value in [
        ("app_sha256", "0" * 64),
        ("purpose", "another-purpose"),
        ("expires_at", "2020-01-01T00:00:00Z"),
        ("envelope_sha256", "0" * 64),
        ("source_use", "buyer approved"),
        ("retention_seconds", 1201),
        ("reviewed_at", "2099-01-01T00:00:00Z"),
    ]:
        old = review[field]
        review[field] = value
        save()
        with pytest.raises(ReviewError):
            resolve_review(manifest, "fixture-app")
        review[field] = old
    save()
    (tmp_path / "app_approval.txt").write_text("replacement assertion")
    with pytest.raises(ReviewError):
        resolve_review(manifest, "fixture-app")


def test_absent_or_incomplete_evidence_is_rejected(tmp_path):
    manifest, review, save = session_review(tmp_path)
    review["documents"] = []
    save()
    with pytest.raises(ReviewError):
        resolve_review(manifest, "fixture-app")
    with pytest.raises(ReviewError):
        resolve_review(tmp_path / "missing", "fixture-app")


def test_eligible_worker_cli_uses_review_normal_acquisition_ui_and_cleanup(tmp_path):
    import os
    import sys
    from uuid import uuid4

    manifest, _review, _sign = session_review(tmp_path)
    root = Path("/private/tmp") / ("pricerecon-pilot-" + uuid4().hex + ".noindex")
    # Only the network transport and the UI lifetime are controlled. CLI parsing,
    # session review, controlled macOS exclusions, grant, guard, normal connector,
    # projection, SQL and read-only HTTP routes all execute normally.
    script = """
import asyncio, os, sys
from pathlib import Path
from unittest.mock import patch
import httpx
import pricerecon.pilot_activation as activation
import pricerecon.pilot_worker as worker
import pricerecon.pilot_ui as ui
from pricerecon.pilot_bounds import QUERIES
calls = []
serve_actual = ui.serve_ui
def edge(request):
    calls.append(request)
    if 'oauth2' in request.url.path:
        return httpx.Response(200, json={'access_token':'fixture-secret-token', 'expires_in':3600})
    query = request.url.params.get('q', '')
    index = 0 if query == QUERIES[0] or '111' in request.url.path else 1
    item = {'itemId': f'v1|{111 if index == 0 else 222}|0', 'title':QUERIES[index], 'itemWebUrl':'https://www.ebay.co.uk/itm/fixture', 'price':{'value':'10', 'currency':'GBP'}, 'conditionId':'1000', 'buyingOptions':['FIXED_PRICE']}
    return httpx.Response(200, json={'itemSummaries':[item]} if query else item)
async def review_ui(app, port, seconds):
    assert port == 8878 and 0 < seconds <= 1200
    await ui.check_ui(app)
    await serve_actual(app, port, 0.2)
activation.GRANT = Path(sys.argv[1])
sys.argv = ['pilot_worker', '--execute', '--review', sys.argv[2], sys.argv[3]]
with patch.object(httpx, 'AsyncHTTPTransport', lambda **kw: httpx.MockTransport(edge)), patch.object(worker.socket, 'getaddrinfo', return_value=[]), patch.object(activation, 'prepare_excluded_root', return_value={}), patch.object(ui, 'serve_ui', review_ui):
    try:
        worker.main()
    except FileExistsError:
        assert calls == []
        raise
assert len(calls) == 5
"""
    env = {**os.environ, "EBAY_APP_ID": "fixture-app", "EBAY_CERT_ID": "fixture-cert"}
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(tmp_path / "live.consumed"),
            str(manifest),
            str(root),
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["state"] == "success"
    assert receipt["live_eligible"] is True
    assert receipt["cleanup"] is True
    assert receipt["requests"] == 5
    assert (tmp_path / "live.consumed").is_file()
    assert not root.exists()
    assert "fixture-secret" not in result.stdout
    assert "10.00" not in result.stdout
    second = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(tmp_path / "live.consumed"),
            str(manifest),
            str(root),
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert second.returncode != 0
    assert "FileExistsError" in second.stderr
    assert not root.exists()


def test_current_platform_exclusion_is_checked_and_active_backup_tool_blocks(tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace

    import pricerecon.pilot_activation as activation

    if sys.platform != "darwin":
        pytest.skip("pilot supports current macOS platform only")
    seen = []

    def tooling(command, **kwargs):
        seen.append(command)
        if command[0] == "/bin/ps":
            return SimpleNamespace(stdout="/usr/local/bin/restic\n")
        raise AssertionError("exclusion must not proceed with an unhandled active backup tool")

    monkeypatch.setattr(activation.subprocess, "run", tooling)
    with pytest.raises(ReviewError, match="active_backup_sync_tool"):
        activation.prepare_excluded_root(Path("/private/tmp/pricerecon-pilot-fixture.noindex"))
    assert len(seen) == 1


def test_shorter_external_retention_and_elapsed_operator_budget_bound_runtime(tmp_path):
    manifest, review, save = session_review(tmp_path)
    review["retention_seconds"] = 3
    save()
    assert 0 < resolve_review(manifest, "fixture-app").remaining_seconds() <= 3
    review["operator_started_at"] = (datetime.now(UTC) - timedelta(minutes=31)).isoformat()
    save()
    with pytest.raises(ReviewError):
        resolve_review(manifest, "fixture-app")


def test_supervisor_activation_applies_external_shorter_deadline(tmp_path, monkeypatch, capsys):
    import sys
    import time

    import pricerecon.pilot_supervisor as supervisor

    manifest, review, save = session_review(tmp_path)
    review["retention_seconds"] = 3
    save()
    monkeypatch.setenv("EBAY_APP_ID", "fixture-app")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pilot_supervisor",
            "--execute",
            "--review",
            str(manifest),
            str(tmp_path / "run"),
        ],
    )
    observed = []

    def controlled_owner(command, root, *, timeout, owner_pid):
        observed.append((command, timeout))
        return {"state": "controlled_no_execution"}

    monkeypatch.setattr(supervisor, "supervise", controlled_owner)
    before = time.monotonic()
    supervisor.main()
    command, timeout = observed[0]
    assert 0 < timeout <= 3
    deadline = float(command[command.index("--deadline-monotonic") + 1])
    assert before < deadline <= time.monotonic() + 3
    assert json.loads(capsys.readouterr().out)["state"] == "controlled_no_execution"


def test_public_cli_accepts_session_review_without_keys_and_blocks_changed_documents(tmp_path):
    import os
    import sys

    manifest, _review, _save = session_review(tmp_path)
    env = {**os.environ, "EBAY_APP_ID": "fixture-app", "EBAY_CERT_ID": "fixture-cert"}
    command = [sys.executable, "-m", "pricerecon.pilot", "--review", str(manifest)]
    ready = subprocess.run(command, env=env, capture_output=True, text=True, check=False)
    assert ready.returncode == 0, ready.stderr
    assert json.loads(ready.stdout)["state"] == "ready_for_exclusion_check"
    (tmp_path / "transient_use.txt").unlink()
    blocked = subprocess.run(command, env=env, capture_output=True, text=True, check=False)
    receipt = json.loads(blocked.stdout)
    assert receipt["state"] == "blocked"
    assert receipt["requests"] == 0
    force = subprocess.run(
        command + ["--force"], env=env, capture_output=True, text=True, check=False
    )
    assert force.returncode != 0
