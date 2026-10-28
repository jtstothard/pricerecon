"""Pilot public boundaries; every transport is controlled, never live."""

import asyncio
import json
import subprocess
import sys

from pricerecon.pilot import preflight


def test_missing_provider_authority_is_a_useful_zero_request_receipt():
    receipt = preflight()
    assert receipt["state"] == "blocked"
    assert receipt["requests"] == 0
    assert receipt["gates"] == [
        "ebay_app_approval_unproven",
        "ebay_transient_retention_unproven",
        "backup_exclusion_unproven",
    ]
    assert set(receipt) == {"schema", "state", "gates", "requests"}


def test_transport_rejects_unapproved_route_before_external_edge():
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
                await client.get("https://api.ebay.com/sell/account/v1/privilege")
        assert seen == []

    asyncio.run(scenario())


def test_pilot_connector_uses_memory_auth_five_leads_and_two_exact_details(tmp_path, monkeypatch):
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
        "title": QUERIES[0],
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
            return httpx.Response(200, json={"itemSummaries": [item]})
        return httpx.Response(200, json=item)

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
                    report = await connector.search_with_evidence(QUERIES[0])
                finally:
                    active_admission.reset(admission_token)
            assert len(report.listings) == 1
            assert report.listings[0].total_landed_cost is None
            assert report.listings[0].exact_variant_confirmed is not True
            assert bounds.details == 1
            assert bounds.requests == 3
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


def test_supervisor_expires_child_and_removes_sidecars(tmp_path):
    from pricerecon.pilot_supervisor import supervise

    root = tmp_path / "pricerecon-pilot"
    child = (
        "from pathlib import Path; import time; "
        f"r=Path({str(root)!r}); r.mkdir(); "
        "(r/'.pilot-run').write_text('pricerecon-one-off-pilot-v1\\n'); "
        "(r/'pricerecon.db-wal').write_bytes(b'synthetic-only'); time.sleep(20)"
    )
    receipt = supervise([sys.executable, "-c", child], root, timeout=0.3)
    assert receipt["state"] == "deadline"
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
