import asyncio
import base64
import json
import logging
import sqlite3
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import httpx
import pytest

from pricerecon.connectors import ebay

APP = "synthetic-app-identity-private"
CERT = "synthetic-cert-secret-private"
TOKEN = "synthetic-access-token-private"


@pytest.fixture(autouse=True)
def isolated_coordinator(monkeypatch):
    # Coordinator state belongs to a running worker/event loop. Do not let
    # this test's concurrent fetch bind the shared lock for another test loop.
    monkeypatch.setattr(ebay._EBayTokenFetchCoordinator, "_active_fetches_lock", asyncio.Lock())
    monkeypatch.setattr(ebay._EBayTokenFetchCoordinator, "_active_fetches", {})


def assert_no_auth_material(text):
    for value in (APP, APP[:8], CERT, TOKEN, base64.b64encode(f"{APP}:{CERT}".encode()).decode()):
        assert value not in text


async def test_coordinator_success_and_waiter_diagnostics_do_not_retain_credentials(caplog):
    calls = 0

    async def handler(request):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        return httpx.Response(200, json={"access_token": TOKEN, "expires_in": 7200})

    caplog.set_level(logging.INFO)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        tokens = await asyncio.gather(
            *(
                ebay._EBayTokenFetchCoordinator.fetch_token(APP, CERT, client, max_retries=1)
                for _ in range(3)
            )
        )
    assert calls == 1
    assert all(token.access_token == TOKEN for token in tokens)
    assert_no_auth_material(caplog.text)
    assert_no_auth_material(repr(getattr(ebay, "_token_fetch_calls", {})))


@pytest.mark.parametrize("failure", ["provider_body", "transport"])
async def test_auth_errors_do_not_expose_provider_body_or_transport_secrets(caplog, failure):
    def handler(request):
        if failure == "transport":
            raise httpx.ConnectError(f"failed {CERT} {TOKEN}", request=request)
        return httpx.Response(400, json={"error_description": f"invalid {CERT} {TOKEN}"})

    caplog.set_level(logging.INFO)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(Exception) as error:
            await ebay._EBayTokenFetchCoordinator.fetch_token(APP, CERT, client, max_retries=1)
    assert_no_auth_material(caplog.text)
    assert_no_auth_material(str(error.value))


async def test_cached_token_diagnostics_do_not_include_identity_or_token(caplog, monkeypatch):
    token = ebay.eBayOAuthToken(
        access_token=TOKEN,
        expires_in=7200,
        expires_at=datetime.now(UTC) + timedelta(hours=2),
    )
    connector = ebay.eBayConnector(APP, CERT)
    connector.token_store = Mock()
    connector.token_store.get_token.return_value = token
    monkeypatch.setattr(connector, "_clear_health_error", lambda: None)
    caplog.set_level(logging.INFO)
    assert await connector.ensure_token() == TOKEN
    assert_no_auth_material(caplog.text)


def test_invalid_persisted_token_does_not_dump_validation_input(tmp_path, caplog):
    path = tmp_path / "tokens.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE connector_configs (connector_id TEXT, config_json TEXT)")
        db.execute(
            "INSERT INTO connector_configs VALUES (?, ?)",
            (
                "ebay",
                json.dumps({"oauth_token": {"access_token": TOKEN, "expires_in": CERT}}),
            ),
        )
    caplog.set_level(logging.WARNING)
    assert ebay.eBayTokenStore(str(path)).get_token() is None
    assert_no_auth_material(caplog.text)
