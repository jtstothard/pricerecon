"""Test OAuth token store utility."""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import aiosqlite

from pricerecon.core.token_store import OAuthTokenStore, TokenData


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        yield db_path


@pytest.fixture
def store(temp_db):
    """Create token store instance."""
    return OAuthTokenStore(temp_db)


@pytest.mark.asyncio
async def test_token_data_serialization():
    """Test TokenData to_dict/from_dict."""
    now = datetime.utcnow()
    token = TokenData(
        access_token="test_token",
        expires_at=now,
        scope="read write",
        token_type="Bearer",
        refresh_token="refresh_token_value",
        raw_data={"extra": "data"},
    )

    token_dict = token.to_dict()
    assert token_dict["access_token"] == "test_token"
    assert token_dict["expires_at"] == now.isoformat()
    assert token_dict["scope"] == "read write"
    assert token_dict["token_type"] == "Bearer"
    assert token_dict["refresh_token"] == "refresh_token_value"
    assert token_dict["raw_data"] == {"extra": "data"}

    restored = TokenData.from_dict(token_dict)
    assert restored.access_token == "test_token"
    assert restored.expires_at == now
    assert restored.scope == "read write"
    assert restored.token_type == "Bearer"
    assert restored.refresh_token == "refresh_token_value"
    assert restored.raw_data == {"extra": "data"}


@pytest.mark.asyncio
async def test_token_expiry_check():
    """Test TokenData.is_expired."""
    now = datetime.utcnow()

    # Fresh token (1 hour from now)
    fresh_token = TokenData(
        access_token="fresh", expires_at=now + timedelta(hours=1)
    )
    assert not fresh_token.is_expired()

    # Expired token (1 hour ago)
    expired_token = TokenData(
        access_token="expired", expires_at=now - timedelta(hours=1)
    )
    assert expired_token.is_expired()

    # Token expiring in 2 minutes (within 5 min buffer)
    near_expiry = TokenData(
        access_token="near", expires_at=now + timedelta(minutes=2)
    )
    assert near_expiry.is_expired(buffer_seconds=300)

    # Token expiring in 10 minutes (outside buffer)
    outside_buffer = TokenData(
        access_token="ok", expires_at=now + timedelta(minutes=10)
    )
    assert not outside_buffer.is_expired(buffer_seconds=300)


@pytest.mark.asyncio
async def test_store_and_retrieve_token(store):
    """Test storing and retrieving tokens."""
    now = datetime.utcnow() + timedelta(hours=1)
    token = TokenData(
        access_token="test_access_token",
        expires_at=now,
        scope="read",
        token_type="Bearer",
    )

    await store.store_token("test_connector", token)

    retrieved = await store.get_token("test_connector")
    assert retrieved is not None
    assert retrieved.access_token == "test_access_token"
    assert retrieved.expires_at == now
    assert retrieved.scope == "read"
    assert retrieved.token_type == "Bearer"


@pytest.mark.asyncio
async def test_retrieve_expired_token(store):
    """Test that expired tokens are not returned."""
    now = datetime.utcnow()
    expired_token = TokenData(
        access_token="expired_token", expires_at=now - timedelta(hours=1)
    )

    await store.store_token("test_connector", expired_token)

    retrieved = await store.get_token("test_connector")
    assert retrieved is None


@pytest.mark.asyncio
async def test_is_valid(store):
    """Test is_valid method."""
    now = datetime.utcnow()

    # Valid token
    valid_token = TokenData(
        access_token="valid", expires_at=now + timedelta(hours=1)
    )
    await store.store_token("valid_connector", valid_token)
    assert await store.is_valid("valid_connector")

    # Expired token
    expired_token = TokenData(
        access_token="expired", expires_at=now - timedelta(hours=1)
    )
    await store.store_token("expired_connector", expired_token)
    assert not await store.is_valid("expired_connector")

    # No token
    assert not await store.is_valid("nonexistent_connector")


@pytest.mark.asyncio
async def test_refresh_if_needed_with_valid_token(store):
    """Test refresh_if_needed skips refresh when token is valid."""
    now = datetime.utcnow() + timedelta(hours=1)
    token = TokenData(access_token="valid_token", expires_at=now)
    await store.store_token("test_connector", token)

    refresh_called = False

    async def fake_refresh():
        nonlocal refresh_called
        refresh_called = True
        return TokenData(
            access_token="refreshed_token", expires_at=datetime.utcnow() + timedelta(hours=2)
        )

    result = await store.refresh_if_needed("test_connector", fake_refresh)
    assert result.access_token == "valid_token"
    assert not refresh_called


@pytest.mark.asyncio
async def test_refresh_if_needed_with_expired_token(store):
    """Test refresh_if_needed calls refresh when token is expired."""
    now = datetime.utcnow()
    expired_token = TokenData(access_token="expired", expires_at=now - timedelta(hours=1))
    await store.store_token("test_connector", expired_token)

    refresh_called = False

    async def fake_refresh():
        nonlocal refresh_called
        refresh_called = True
        return TokenData(
            access_token="refreshed_token", expires_at=datetime.utcnow() + timedelta(hours=2)
        )

    result = await store.refresh_if_needed("test_connector", fake_refresh)
    assert result.access_token == "refreshed_token"
    assert refresh_called


@pytest.mark.asyncio
async def test_refresh_if_needed_with_no_token(store):
    """Test refresh_if_needed calls refresh when no token exists."""
    refresh_called = False

    async def fake_refresh():
        nonlocal refresh_called
        refresh_called = True
        return TokenData(
            access_token="refreshed_token", expires_at=datetime.utcnow() + timedelta(hours=2)
        )

    result = await store.refresh_if_needed("test_connector", fake_refresh)
    assert result.access_token == "refreshed_token"
    assert refresh_called


@pytest.mark.asyncio
async def test_concurrent_refresh(store):
    """Test that concurrent refresh calls only execute one refresh."""
    refresh_count = 0

    async def slow_refresh():
        nonlocal refresh_count
        refresh_count += 1
        await asyncio.sleep(0.1)  # Simulate slow refresh
        return TokenData(
            access_token=f"token_{refresh_count}", expires_at=datetime.utcnow() + timedelta(hours=1)
        )

    # Launch multiple concurrent refreshes
    tasks = [
        store.refresh_if_needed("test_connector", slow_refresh) for _ in range(5)
    ]
    results = await asyncio.gather(*tasks)

    # All should get the same token
    assert all(r.access_token == "token_1" for r in results)
    # Refresh should only be called once
    assert refresh_count == 1


@pytest.mark.asyncio
async def test_delete_token(store):
    """Test deleting a token."""
    token = TokenData(
        access_token="test_token", expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    await store.store_token("test_connector", token)

    assert await store.is_valid("test_connector")
    await store.delete_token("test_connector")
    assert not await store.is_valid("test_connector")


@pytest.mark.asyncio
async def test_list_connectors(store):
    """Test listing connectors with tokens."""
    now = datetime.utcnow() + timedelta(hours=1)

    await store.store_token("ebay", TokenData(access_token="ebay_token", expires_at=now))
    await store.store_token("amazon", TokenData(access_token="amazon_token", expires_at=now))
    await store.store_token("etsy", TokenData(access_token="etsy_token", expires_at=now))

    connectors = await store.list_connectors()
    assert set(connectors) == {"ebay", "amazon", "etsy"}


@pytest.mark.asyncio
async def test_replace_token(store):
    """Test that replace=True overwrites existing tokens."""
    token1 = TokenData(
        access_token="token1", expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    await store.store_token("test_connector", token1)

    token2 = TokenData(
        access_token="token2", expires_at=datetime.utcnow() + timedelta(hours=2)
    )
    await store.store_token("test_connector", token2, replace=True)

    retrieved = await store.get_token("test_connector")
    assert retrieved.access_token == "token2"


@pytest.mark.asyncio
async def test_no_replace_token(store):
    """Test that replace=False skips if token exists."""
    token1 = TokenData(
        access_token="token1", expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    await store.store_token("test_connector", token1)

    token2 = TokenData(
        access_token="token2", expires_at=datetime.utcnow() + timedelta(hours=2)
    )
    await store.store_token("test_connector", token2, replace=False)

    retrieved = await store.get_token("test_connector")
    assert retrieved.access_token == "token1"


@pytest.mark.asyncio
async def test_old_schema_migration():
    """Test migration from old connector_configs schema."""
    with TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        # Create old schema
        import sqlite3

        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE connector_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                connector_id TEXT NOT NULL UNIQUE,
                config_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # Insert old-style config with oauth_token
        old_config = {
            "oauth_token": {
                "access_token": "old_token",
                "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
                "scope": "read",
                "token_type": "Bearer",
            }
        }
        conn.execute(
            "INSERT INTO connector_configs (connector_id, config_json) VALUES (?, ?)",
            ("ebay", json.dumps(old_config)),
        )
        conn.commit()
        conn.close()

        # Create store - should auto-migrate
        store = OAuthTokenStore(db_path)
        token = await store.get_token("ebay")

        assert token is not None
        assert token.access_token == "old_token"
        assert token.scope == "read"


@pytest.mark.asyncio
async def test_multiple_keys_per_connector(store):
    """Test that multiple keys can be stored for same connector."""
    token1 = TokenData(
        access_token="oauth_token", expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    await store.store_token("ebay", token1)

    # Store a different key
    async with aiosqlite.connect(store.db_path) as conn:
        await conn.execute(
            """
            INSERT INTO connector_configs (connector_id, key, value, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            ("ebay", "api_key", "some_api_key", None),
        )
        await conn.commit()

    # OAuth token should still be retrievable
    token = await store.get_token("ebay")
    assert token.access_token == "oauth_token"