"""Unit tests for eBay connector OAuth self-healing."""

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, Mock

import httpx
import pytest

# Add src to path
import sys

sys.path.insert(0, "/home/hermes/pricerecon/src")

from pricerecon.connectors.ebay import eBayConnector, eBayOAuthToken, eBayTokenStore


class TestEBayTokenStore:
    """Test eBayTokenStore functionality."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create a temporary test database."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS connector_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                connector_id TEXT NOT NULL UNIQUE,
                config_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        conn.close()
        return db_path

    def test_save_token_preserves_existing_config(self, temp_db):
        """Test that save_token merges with existing config instead of overwriting."""
        store = eBayTokenStore(str(temp_db))

        # First, save some existing config with other keys
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        existing_config = {
            "some_other_key": "some_value",
            "another_key": {"nested": "data"},
        }
        cursor.execute(
            """
            INSERT INTO connector_configs (connector_id, config_json)
            VALUES ('ebay', ?)
            """,
            (json.dumps(existing_config),),
        )
        conn.commit()
        conn.close()

        # Now save a token
        token = eBayOAuthToken(
            access_token="test_token",
            token_type="Bearer",
            expires_in=7200,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        )
        store.save_token(token)

        # Verify that both the token AND existing keys are preserved
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT config_json FROM connector_configs WHERE connector_id = 'ebay'")
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        config = json.loads(row[0])

        # Token should be saved
        assert "oauth_token" in config
        assert config["oauth_token"]["access_token"] == "test_token"

        # Existing keys should be preserved
        assert config["some_other_key"] == "some_value"
        assert config["another_key"]["nested"] == "data"

    def test_get_token_returns_none_if_missing(self, temp_db):
        """Test that get_token returns None when no token exists."""
        store = eBayTokenStore(str(temp_db))
        token = store.get_token()
        assert token is None

    def test_get_token_returns_none_if_expired(self, temp_db):
        """Test that get_token returns None for expired tokens."""
        store = eBayTokenStore(str(temp_db))

        # Save an expired token
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        expired_token = eBayOAuthToken(
            access_token="expired_token",
            token_type="Bearer",
            expires_in=7200,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),  # Expired 1 hour ago
        )
        cursor.execute(
            """
            INSERT INTO connector_configs (connector_id, config_json)
            VALUES ('ebay', ?)
            """,
            (json.dumps({"oauth_token": expired_token.model_dump(mode="json")}),),
        )
        conn.commit()
        conn.close()

        token = store.get_token()
        assert token is None

    def test_get_token_returns_valid_token(self, temp_db):
        """Test that get_token returns a valid token."""
        store = eBayTokenStore(str(temp_db))

        # Save a valid token
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        valid_token = eBayOAuthToken(
            access_token="valid_token",
            token_type="Bearer",
            expires_in=7200,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        )
        cursor.execute(
            """
            INSERT INTO connector_configs (connector_id, config_json)
            VALUES ('ebay', ?)
            """,
            (json.dumps({"oauth_token": valid_token.model_dump(mode="json")}),),
        )
        conn.commit()
        conn.close()

        token = store.get_token()
        assert token is not None
        assert token.access_token == "valid_token"

    def test_naive_expiry_is_normalized_to_utc(self, temp_db):
        """Legacy offset-less expiry timestamps are interpreted as UTC."""
        store = eBayTokenStore(str(temp_db))
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=2)).replace(tzinfo=None)
        token = eBayOAuthToken(
            access_token="legacy_token",
            expires_in=7200,
            expires_at=expires_at,
        )

        assert token.expires_at.tzinfo is not None
        assert token.expires_at.utcoffset() == timedelta(0)
        store.save_token(token)

        restored = store.get_token()
        assert restored is not None
        assert restored.expires_at.tzinfo is not None
        assert restored.expires_at.utcoffset() == timedelta(0)


class TestEBayConnectorSearch401Retry:
    """Test eBay connector 401 retry behavior."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create a temporary test database."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create connector_configs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS connector_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                connector_id TEXT NOT NULL UNIQUE,
                config_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Create connector_health table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS connector_health (
                connector_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                last_error TEXT,
                details_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.commit()
        conn.close()
        return db_path

    @pytest.fixture
    def connector(self, temp_db):
        """Create an eBay connector instance with health DB calls isolated."""
        patcher = patch("pricerecon.core.connector_health.get_db")
        mock_get_db = patcher.start()

        def open_temp_db(*_args, **_kwargs):
            conn = sqlite3.connect(temp_db)
            conn.row_factory = sqlite3.Row
            return conn

        mock_get_db.side_effect = open_temp_db
        try:
            yield eBayConnector(
                app_id="test_app_id",
                cert_id="test_cert_id",
                db_path=str(temp_db),
            )
        finally:
            patcher.stop()

    @pytest.mark.asyncio
    async def test_search_401_triggers_refresh_and_retry(self, connector, temp_db):
        """Test that a 401 on first search triggers token refresh and retry succeeds."""
        # Save a valid token
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        initial_token = eBayOAuthToken(
            access_token="initial_token",
            token_type="Bearer",
            expires_in=7200,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        )
        cursor.execute(
            """
            INSERT INTO connector_configs (connector_id, config_json)
            VALUES ('ebay', ?)
            """,
            (json.dumps({"oauth_token": initial_token.model_dump(mode="json")}),),
        )
        conn.commit()
        conn.close()

        # Mock HTTP client responses
        mock_client = AsyncMock()

        # First call returns 401 (token expired)
        response_401 = MagicMock()
        response_401.status_code = 401
        response_401.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized", request=MagicMock(), response=response_401
        )

        # Token fetch succeeds
        response_token = MagicMock()
        response_token.status_code = 200
        response_token.json.return_value = {
            "access_token": "new_token",
            "token_type": "Bearer",
            "expires_in": 7200,
        }

        # Second search call succeeds
        response_success = MagicMock()
        response_success.status_code = 200
        response_success.json.return_value = {
            "itemSummaries": [
                {
                    "itemId": "123",
                    "title": "Test Item",
                    "price": {"value": "10.00", "currency": "GBP"},
                    "itemWebUrl": "https://example.com/item/123",
                    "seller": {
                        "username": "test_seller",
                        "feedbackScore": 100,
                        "feedbackPercentage": 99.5,
                    },
                    "availability": {"shipToLocationAvailability": {"quantity": 1}},
                }
            ]
        }

        mock_client.post.return_value = response_token
        mock_client.get.side_effect = [response_401, response_success]

        with patch.object(connector, "_client", mock_client):
            listings = await connector.search("test query")

        # Verify that we got listings (retry succeeded)
        assert len(listings) == 1
        assert listings[0].title_raw == "Test Item"

        # Verify that we called get twice (first 401, second retry)
        assert mock_client.get.call_count == 2

        # Verify that we fetched a new token
        assert mock_client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_expired_cached_token_is_replaced_before_search(self, connector, temp_db):
        """An expired cached token is not sent to Browse API."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        expired_token = eBayOAuthToken(
            access_token="expired_token",
            token_type="Bearer",
            expires_in=7200,
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        cursor.execute(
            "INSERT INTO connector_configs (connector_id, config_json) VALUES ('ebay', ?)",
            (json.dumps({"oauth_token": expired_token.model_dump(mode="json")}),),
        )
        conn.commit()
        conn.close()

        mock_client = AsyncMock()
        response_token = MagicMock(status_code=200)
        response_token.json.return_value = {
            "access_token": "fresh_token",
            "token_type": "Bearer",
            "expires_in": 7200,
        }
        response_success = MagicMock(status_code=200)
        response_success.json.return_value = {"itemSummaries": []}
        mock_client.post.return_value = response_token
        mock_client.get.return_value = response_success

        with patch.object(connector, "_client", mock_client):
            assert await connector.search("expired token query") == []

        assert mock_client.post.call_count == 1
        assert mock_client.get.call_count == 1
        assert "fresh_token" in mock_client.get.call_args.kwargs["headers"]["Authorization"]

    @pytest.mark.asyncio
    async def test_repeated_401_does_not_retry_indefinitely(self, connector, temp_db):
        """A refreshed token gets exactly one Browse API retry."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        token = eBayOAuthToken(
            access_token="revoked_token",
            token_type="Bearer",
            expires_in=7200,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        )
        cursor.execute(
            "INSERT INTO connector_configs (connector_id, config_json) VALUES ('ebay', ?)",
            (json.dumps({"oauth_token": token.model_dump(mode="json")}),),
        )
        conn.commit()
        conn.close()

        mock_client = AsyncMock()
        response_401 = MagicMock(status_code=401)
        response_401.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized", request=MagicMock(), response=response_401
        )
        response_token = MagicMock(status_code=200)
        response_token.json.return_value = {
            "access_token": "replacement_token",
            "token_type": "Bearer",
            "expires_in": 7200,
        }
        mock_client.post.return_value = response_token
        mock_client.get.side_effect = [response_401, response_401]

        with patch.object(connector, "_client", mock_client):
            with pytest.raises(httpx.HTTPStatusError):
                await connector.search("still unauthorized")

        assert mock_client.get.call_count == 2
        assert mock_client.post.call_count == 1


class TestEBayConnectorHealthRecovery:
    """Test eBay connector health recovery."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create a temporary test database."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create connector_configs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS connector_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                connector_id TEXT NOT NULL UNIQUE,
                config_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Create connector_health table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS connector_health (
                connector_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                last_error TEXT,
                details_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.commit()
        conn.close()
        return db_path

    @pytest.fixture
    def connector(self, temp_db):
        """Create an eBay connector instance with health DB calls isolated."""
        patcher = patch("pricerecon.core.connector_health.get_db")
        mock_get_db = patcher.start()

        def open_temp_db(*_args, **_kwargs):
            conn = sqlite3.connect(temp_db)
            conn.row_factory = sqlite3.Row
            return conn

        mock_get_db.side_effect = open_temp_db
        try:
            yield eBayConnector(
                app_id="test_app_id",
                cert_id="test_cert_id",
                db_path=str(temp_db),
            )
        finally:
            patcher.stop()

    @pytest.mark.asyncio
    async def test_connector_with_auth_failed_health_state_is_retried(self, connector, temp_db):
        """Test that a connector with auth_failed health state is retried after it becomes stale."""
        # Set up auth_failed health state
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Set auth_failed status with an old timestamp (more than 1 hour ago)
        old_timestamp = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        cursor.execute(
            """
            INSERT INTO connector_health (connector_id, status, last_error, details_json, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "ebay",
                "auth_failed",
                "Test auth error",
                json.dumps({"error_type": "TokenRefreshError"}),
                old_timestamp,
            ),
        )
        conn.commit()
        conn.close()

        # Mock successful token fetch
        mock_client = AsyncMock()
        response_token = MagicMock()
        response_token.status_code = 200
        response_token.json.return_value = {
            "access_token": "new_token",
            "token_type": "Bearer",
            "expires_in": 7200,
        }

        # Mock successful search
        response_search = MagicMock()
        response_search.status_code = 200
        response_search.json.return_value = {
            "itemSummaries": [
                {
                    "itemId": "123",
                    "title": "Test Item",
                    "price": {"value": "10.00", "currency": "GBP"},
                    "itemWebUrl": "https://example.com/item/123",
                    "seller": {
                        "username": "test_seller",
                        "feedbackScore": 100,
                        "feedbackPercentage": 99.5,
                    },
                    "availability": {"shipToLocationAvailability": {"quantity": 1}},
                }
            ]
        }

        mock_client.post.return_value = response_token
        mock_client.get.return_value = response_search

        def mock_get_db(path=None):
            db_conn = sqlite3.connect(temp_db)
            db_conn.row_factory = sqlite3.Row
            return db_conn

        with patch("pricerecon.core.connector_health.get_db", side_effect=mock_get_db):
            with patch.object(connector, "_client", mock_client):
                listings = await connector.search("test query")

        # Verify that we got listings (connector was not skipped)
        assert len(listings) == 1
        assert listings[0].title_raw == "Test Item"

        # Verify health state was cleared
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM connector_health WHERE connector_id = 'ebay'")
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row[0] == "ok"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
