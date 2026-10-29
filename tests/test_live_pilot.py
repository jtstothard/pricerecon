"""Pilot public boundaries; every transport is controlled, never live."""

import asyncio
import json
import subprocess
import sys

import pytest

from pricerecon.pilot import preflight


def test_missing_provider_authority_is_a_useful_zero_request_receipt():
    receipt = preflight()
    assert receipt["state"] == "blocked"
    assert receipt["requests"] == 0
    assert receipt["gates"] == [
        "ebay_endpoint_access_unreviewed",
        "ebay_transient_retention_unproven",
        "backup_exclusion_unproven",
    ]
    assert set(receipt) == {"schema", "state", "gates", "requests"}


@pytest.mark.parametrize(
    "url",
    [
        "https://api.ebay.com/sell/account/v1/privilege",
        "https://api.ebay.com/buy/browse/v1/item?item_ids=v1%7C111%7C0",
        "https://api.ebay.com/buy/browse/v1/item/v1%7C111%7C0?fieldgroups=WATCH_COUNT",
    ],
)
def test_transport_rejects_unapproved_route_before_external_edge(url):
    import httpx
    import pytest

    from pricerecon.core.rate_limiter import AdmissionDenied
    from pricerecon.pilot_bounds import PilotBounds, PilotTransport

    seen = []

    async def external(request):
        seen.append(request)
        return httpx.Response(200, content=b"{}")

    async def scenario():
        async with httpx.AsyncClient(
            transport=PilotTransport(httpx.MockTransport(external), PilotBounds())
        ) as client:
            with pytest.raises(AdmissionDenied, match="pilot_route_denied"):
                await client.get(url)
        assert seen == []

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "query_index,title,selected",
    [
        (0, "Addiesdive green mint watch AD2066", True),
        (0, "ADDIESDIVE AD2066 Mint-Green", True),
        (0, "Addiesdive AD20660 Mint Green", False),
        (0, "Addiesdive AD2066 Mint Green strap", False),
        (0, "Other AD2066 Mint Green", False),
        (0, "Addiesdive AD2066 Blue", False),
        (1, "Watch MTP B145D 2A2VEF by CASIO", True),
        (1, "Casio MTP-B145D-2A2VEF watch", True),
        (1, "Casio MTP-B145D-2A1VEF", False),
        (1, "Casio MTP-B145D-2A2VEFX", False),
    ],
)
@pytest.mark.parametrize("malformed", ["none", "summary", "detail", "mismatch", "cap"])
def test_pilot_connector_uses_memory_auth_five_leads_and_two_exact_details(
    tmp_path, monkeypatch, malformed, query_index, title, selected
):
    import httpx

    from pricerecon.connectors.ebay import eBayConnector
    from pricerecon.core.collection_policy import operating_policy
    from pricerecon.core.collection_transport import active_admission
    from pricerecon.core.rate_limiter import DurableAdmission
    from pricerecon.db import schema
    from pricerecon.pilot_bounds import (
        QUERIES,
        PilotBounds,
        active_pilot,
        pilot_policy,
        pilot_transport,
    )

    database = tmp_path / "ledger.db"
    monkeypatch.setattr(schema, "DB_PATH", database)
    schema.init_db(database)
    calls = []
    item = {
        "itemId": "v1|123|0",
        "title": title,
        "itemWebUrl": "https://www.ebay.co.uk/itm/123",
        "price": {"value": "10", "currency": "GBP"},
        "conditionId": "1000",
        "buyingOptions": ["FIXED_PRICE"],
    }

    def edge(request):
        calls.append(request)
        if "oauth2" in request.url.path:
            return httpx.Response(200, json={"access_token": "sensitive-token", "expires_in": 3600})
        if request.url.path.endswith("search"):
            return httpx.Response(
                200,
                json={
                    "itemSummaries": (
                        [item, {}]
                        if malformed == "summary"
                        else (
                            [{**item, "itemId": f"v1|{123 + i}|0"} for i in range(5)]
                            if malformed == "cap"
                            else (
                                [item, {**item, "itemId": "v1|456|0"}]
                                if malformed in {"detail", "mismatch"}
                                else [item]
                            )
                        )
                    )
                },
            )
        if "456" in request.url.path:
            return httpx.Response(200, json={} if malformed == "detail" else item)
        return httpx.Response(
            200,
            json={
                **item,
                "itemId": request.url.path.rsplit("/", 1)[1],
                "title": QUERIES[0] + " Mint Green detail description",
                "localizedAspects": [{"name": "Reference Number", "value": "AD2066"}],
                "seller": {"username": "detail-seller"},
                "shippingOptions": [
                    {
                        "shippingCostType": "FIXED",
                        "shippingCost": {"value": "2.50", "currency": "GBP"},
                    }
                ],
                "shipToLocationUsedForEstimate": {"country": "GB"},
            },
        )

    async def scenario():
        bounds = PilotBounds()
        token = active_pilot.set(bounds)
        transport_token = pilot_transport.set(httpx.MockTransport(edge))
        connector = eBayConnector(
            "app",
            "cert",
            str(tmp_path / "must-not-exist.db"),
            evidence_use={
                "permission_reference": "controlled synthetic test only",
                "retention": "synthetic",
            },
        )
        try:
            with operating_policy(pilot_policy()):
                from pricerecon.core.collection_policy import current_policy

                admission = DurableAdmission(current_policy(), "ebay", "discovery", "test")
                admission.begin()
                admission_token = active_admission.set(admission)
                try:
                    await connector.initialize()
                    report = await connector.search_with_evidence(QUERIES[query_index])
                finally:
                    active_admission.reset(admission_token)
            if not selected:
                assert bounds.details == 0
                assert bounds.requests == 2
                assert report.source_evidence.inspected_count == 0
                return
            assert len(report.listings) == (5 if malformed == "cap" else 1)
            assert report.listings[0].title_raw.endswith("Mint Green detail description")
            assert report.listings[0].total_landed_cost is None
            assert report.listings[0].exact_variant_confirmed is not True
            assert bounds.details == (2 if malformed in {"detail", "mismatch", "cap"} else 1)
            assert bounds.requests == (4 if malformed in {"detail", "mismatch", "cap"} else 3)
            assert report.source_evidence.inspected_count == (2 if malformed == "cap" else 1)
            evidence = report.evidence[0]
            assert evidence.source_evidence.shipping_claim == "FIXED GBP 2.50"
            assert evidence.source_evidence.destination == "GB"
            seller = next(c for c in evidence.claims if c.field == "seller")
            assert seller.value == "detail-seller"
            assert seller.route == "ebay_browse_item_v1"
            reference = next(c for c in evidence.claims if c.field == "reference")
            assert reference.value == "AD2066"
            assert reference.issuer_kind == "seller"
            assert reference.locator.endswith("localizedAspects[0]")
            assert seller.locator.startswith("itemDetails[")
            assert seller.pointer.startswith("https://api.ebay.com/buy/browse/v1/item/")
            if malformed not in {"none", "cap"}:
                assert report.acquisition_state == "partial"
                assert report.source_evidence.completeness == "partial"
                assert any(issue.startswith("invalid_") for issue in report.source_evidence.issues)
            assert report.source_evidence.item_limit == 5
        finally:
            await connector.cleanup()
            active_pilot.reset(token)
            pilot_transport.reset(transport_token)
        assert not (tmp_path / "must-not-exist.db").exists()
        assert b"sensitive-token" not in database.read_bytes()
        assert calls[1].url.params["limit"] == "5"

    asyncio.run(scenario())


def test_controlled_runner_crosses_normal_acquisition_and_cleans_all_storage(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "pricerecon.pilot_worker", "--synthetic", str(tmp_path / "run")],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["state"] == "success_empty"
    assert receipt["requests"] == 3
    assert receipt["pages"] == 2
    assert receipt["cleanup"] is True
    assert not (tmp_path / "run").exists()


@pytest.mark.parametrize("disconnected", [False, True])
def test_supervisor_expires_child_and_removes_sidecars(tmp_path, disconnected):
    from pricerecon.pilot_supervisor import supervise

    root = tmp_path / "pricerecon-pilot"
    child = (
        "from pathlib import Path; import time; "
        f"r=Path({str(root)!r}); r.mkdir(); "
        "(r/'.pilot-run').write_text('pricerecon-one-off-pilot-v1\\n'); "
        "(r/'pricerecon.db-wal').write_bytes(b'synthetic-only'); time.sleep(20)"
    )
    receipt = supervise(
        [sys.executable, "-c", child], root, timeout=0.3, owner_pid=-1 if disconnected else None
    )
    assert receipt["state"] == ("session_lost" if disconnected else "deadline")
    assert receipt["cleanup"] is True
    assert not root.exists()


def test_streaming_body_cap_stops_without_retry():
    import httpx
    import pytest

    from pricerecon.core.rate_limiter import AdmissionDenied
    from pricerecon.pilot_bounds import MIB, PilotBounds, PilotTransport

    class Body(httpx.AsyncByteStream):
        async def __aiter__(self):
            for _ in range(34):
                yield b"x" * 65536

    async def scenario():
        b = PilotBounds()
        transport = httpx.MockTransport(lambda request: httpx.Response(200, stream=Body()))
        async with httpx.AsyncClient(transport=PilotTransport(transport, b)) as client:
            with pytest.raises(AdmissionDenied, match="pilot_response_cap"):
                await client.post("https://api.ebay.com/identity/v1/oauth2/token")
            assert b.response_bytes == 2 * MIB + 65536
            with pytest.raises(AdmissionDenied, match="pilot_stopped"):
                await client.post("https://api.ebay.com/identity/v1/oauth2/token")
            assert b.requests == 1

    asyncio.run(scenario())


def test_sqlite_refuses_growth_before_physical_cap_and_denies_disk_journals(tmp_path):
    import sqlite3

    import pytest

    from pricerecon.db.connection import connect, isolated_database

    database = tmp_path / "bounded.db"
    token = isolated_database.set(database)
    try:
        with connect(database) as connection:
            connection.execute("CREATE TABLE payload(value BLOB)")
            with pytest.raises(sqlite3.OperationalError, match="full"):
                connection.execute("INSERT INTO payload VALUES (zeroblob(33554432))")
            with pytest.raises(sqlite3.DatabaseError, match="authorized"):
                connection.execute("PRAGMA journal_mode=WAL")
            assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "memory"
        assert database.stat().st_size <= 33554432
        assert not database.with_name("bounded.db-wal").exists()
    finally:
        isolated_database.reset(token)


def test_completed_pilot_cannot_restart_using_deleted_storage(tmp_path):
    command = [
        sys.executable,
        "-m",
        "pricerecon.pilot_worker",
        "--synthetic",
        str(tmp_path / "run"),
    ]
    first = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    assert first.returncode == 0, first.stderr
    second = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    assert second.returncode != 0
    assert not (tmp_path / "run").exists()


def test_default_and_execute_cli_remain_blocked_without_credentials_or_storage(tmp_path):
    from pathlib import Path

    source = str(Path(__file__).resolve().parents[1] / "src")
    for args in ([], ["--execute"]):
        result = subprocess.run(
            [sys.executable, "-m", "pricerecon.pilot", *args],
            cwd=tmp_path,
            env={"PYTHONPATH": source},
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0
        assert json.loads(result.stdout)["state"] == "blocked"
        assert json.loads(result.stdout)["requests"] == 0
    assert list(tmp_path.iterdir()) == []


def test_marked_fallback_is_rejected_before_transport():
    import httpx
    import pytest

    from pricerecon.core.rate_limiter import AdmissionDenied
    from pricerecon.pilot_bounds import PilotBounds, PilotTransport

    async def scenario():
        seen = []

        def edge(request):
            seen.append(request)
            return httpx.Response(200, json={})

        async with httpx.AsyncClient(
            transport=PilotTransport(httpx.MockTransport(edge), PilotBounds())
        ) as client:
            with pytest.raises(AdmissionDenied, match="pilot_fallback_denied"):
                await client.post(
                    "https://api.ebay.com/identity/v1/oauth2/token",
                    extensions={"collection_fallback": True},
                )
        assert seen == []

    asyncio.run(scenario())


def test_source_denial_stops_whole_runner_and_reports_blocked(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pricerecon.pilot_worker",
            "--synthetic",
            "--synthetic-outcome",
            "denied",
            str(tmp_path / "run"),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["state"] == "blocked"
    assert receipt["requests"] == 1
    assert receipt["pages"] == 0
    assert receipt["cleanup"] is True


def test_documented_offline_cli_uses_tmp_and_supervised_application_seam():
    from pathlib import Path
    from tempfile import TemporaryDirectory

    with TemporaryDirectory(prefix="pilot-cli-proof-", dir="/tmp") as parent:
        root = Path(parent) / "run"
        result = subprocess.run(
            [sys.executable, "-m", "pricerecon.pilot", "--offline-check", str(root)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0
        receipt = json.loads(result.stdout)
        assert receipt["state"] == "success_empty"
        assert receipt["requests"] == 3
        assert receipt["cleanup"] is True


def test_transient_ui_reads_normal_discovery_feed_and_denies_mutations(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pricerecon.pilot_worker",
            "--synthetic",
            "--synthetic-outcome",
            "offer",
            "--ui-check",
            str(tmp_path / "ui-run"),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["state"] == "success"
    assert receipt["ui_checked"] is True
    assert receipt["requests"] == 5
    assert receipt["cleanup"] is True


def test_second_query_terminal_stop_never_opens_ui_and_deletes_run(tmp_path):
    # Drive the worker CLI, controlling only provider transport and UI serving.
    script = """
import sys
from unittest.mock import patch
import httpx
import pricerecon.pilot_worker as worker
import pricerecon.pilot_ui as ui
from pricerecon.pilot_bounds import QUERIES
calls = []
def edge(request):
    calls.append(request)
    if 'oauth2' in request.url.path:
        return httpx.Response(200, json={'access_token':'fixture-token'})
    query = request.url.params.get('q', '')
    if query == QUERIES[1]:
        return httpx.Response(200, content=b'x' * (2 * 1024 * 1024 + 1)) if STATUS == 200 else httpx.Response(STATUS, json={})
    item = {'itemId':'v1|111|0','title':QUERIES[0],'itemWebUrl':'https://www.ebay.co.uk/itm/111','price':{'value':'10','currency':'GBP'},'conditionId':'1000','buyingOptions':['FIXED_PRICE']}
    return httpx.Response(200, json={'itemSummaries':[item]} if query else item)
def forbidden_ui(**kwargs):
    raise AssertionError('terminal stop exposed retained data to UI')
actual = worker.acquire_once
async def run(*args, **kwargs):
    kwargs['ui_port'] = 8878
    return await actual(httpx.MockTransport(edge), *args[1:], **kwargs)
sys.argv = ['worker','--synthetic',sys.argv[1]]
with patch.object(worker, 'acquire_once', run), patch.object(ui, 'create_ui', forbidden_ui):
    worker.main()
assert len(calls) == 4
"""
    for status in (403, 429, 500, 200):
        root = tmp_path / str(status)
        result = subprocess.run(
            [sys.executable, "-c", script.replace("STATUS", str(status)), str(root)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        receipt = json.loads(result.stdout)
        assert receipt["state"] in {"blocked", "failed", "capped"}
        assert receipt["cleanup"] is True
        assert receipt["ui_checked"] is False
        assert not root.exists()
        assert "fixture-token" not in result.stdout


@pytest.mark.parametrize("supervised", [False, True, "cli"])
@pytest.mark.parametrize("stop_signal", ["SIGINT", "SIGTERM"])
def test_worker_operator_stop_preserves_terminal_counters_and_consumption(
    tmp_path, stop_signal, supervised
):
    # Public worker CLI, controlled transport and UI edge. Signal the exact owner
    # after normal acquisition; no live eligibility/grant is touched.
    script = """
import asyncio, os, signal, sys
from unittest.mock import patch
import pricerecon.pilot_worker as worker
import pricerecon.pilot_ui as ui
actual_serve = ui.serve_ui
async def serve(app, port, seconds):
    asyncio.get_running_loop().call_later(.5, os.kill, os.getpid(), getattr(signal, sys.argv[2]))
    await actual_serve(app, port, seconds)
actual_guard = worker.install_storage_guard
def guard(root, **kwargs):
    kwargs['ui_port'] = 8878
    actual_guard(root, **kwargs)
actual = worker.acquire_once
async def acquire(*args, **kwargs):
    kwargs['ui_port'] = 8878
    return await actual(*args, **kwargs)
root = sys.argv[1]
sys.argv = ['worker', '--synthetic', root]
with patch.object(worker, 'acquire_once', acquire), patch.object(ui, 'serve_ui', serve), patch.object(worker, 'install_storage_guard', guard):
    worker.main()
""".replace("getattr(signal, sys.argv[2])", f"signal.{stop_signal}")
    root = tmp_path / "stop"
    command = [sys.executable, "-c", script, str(root)]
    if supervised:
        wrapper = (
            "import json; from pathlib import Path; "
            "from pricerecon.pilot_supervisor import supervise; "
            f"print(json.dumps(supervise({command!r}, Path({str(root)!r}), timeout=10)))"
        )
        if supervised == "cli":
            # Enter the outer public CLI; replace only its subprocess launch
            # with the same synthetic supervised worker, preserving signals.
            child_script = script.replace(
                "os.getpid(), signal.", "int(os.environ['PILOT_TEST_OWNER_PID']), signal."
            )
            child_command = [sys.executable, "-c", child_script, str(root)]
            supervisor_script = (
                "import json; from pathlib import Path; "
                "from pricerecon.pilot_supervisor import supervise; "
                f"print(json.dumps(supervise({child_command!r}, Path({str(root)!r}), timeout=10)))"
            )
            wrapper = (
                "import os, sys; from unittest.mock import patch; "
                "import pricerecon.pilot as pilot; "
                "os.environ['PILOT_TEST_OWNER_PID'] = str(os.getpid()); "
                "original = pilot.subprocess.Popen; "
                f"replacement = lambda command, **kwargs: original([sys.executable, '-c', {supervisor_script!r}], **kwargs); "
                f"sys.argv = ['pilot', '--offline-check', {str(root)!r}]; "
                "\nwith patch.object(pilot.subprocess, 'Popen', replacement): pilot.main()"
            )
        run_command = [sys.executable, "-c", wrapper]
    else:
        run_command = command
    result = subprocess.run(run_command, capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["state"] == "operator_stopped"
    assert receipt["requests"] == 3
    assert receipt["pages"] == 2
    assert receipt["details"] == 0
    assert receipt["cleanup"] is True
    import socket

    with socket.socket() as probe:
        assert probe.connect_ex(("127.0.0.1", 8878)) != 0
    assert not root.exists()
    assert root.with_suffix(".consumed").read_text() == "synthetic pilot consumed\n"
    again = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    assert again.returncode != 0
    assert "synthetic-memory-only" not in result.stdout


def test_abnormal_worker_exit_cannot_promote_receipt_to_success(tmp_path):
    from pricerecon.pilot_supervisor import supervise

    child = 'import sys; print(\'{"state":"success","requests":7}\'); sys.exit(1)'
    receipt = supervise([sys.executable, "-c", child], tmp_path / "failed", timeout=2)
    assert receipt["state"] == "failed"
    assert "requests" not in receipt
    assert receipt["cleanup"] is True
