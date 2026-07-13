"""Generic OAuth token storage utility for connectors.

Provides persistent storage, expiry checking, and auto-refresh for OAuth tokens.
Thread-safe for concurrent use across multiple connector instances.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional, Awaitable

import aiosqlite

logger = logging.getLogger(__name__)


class TokenData:
    """OAuth token data model."""

    def __init__(
        self,
        access_token: str,
        expires_at: datetime,
        scope: Optional[str] = None,
        token_type: str = "Bearer",
        refresh_token: Optional[str] = None,
        raw_data: Optional[dict[str, Any]] = None,
    ):
        self.access_token = access_token
        self.expires_at = expires_at
        self.scope = scope
        self.token_type = token_type
        self.refresh_token = refresh_token
        self.raw_data = raw_data or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "access_token": self.access_token,
            "expires_at": self.expires_at.isoformat(),
            "scope": self.scope,
            "token_type": self.token_type,
            "refresh_token": self.refresh_token,
            "raw_data": self.raw_data,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TokenData":
        """Create from dictionary."""
        return cls(
            access_token=data["access_token"],
            expires_at=datetime.fromisoformat(data["expires_at"]),
            scope=data.get("scope"),
            token_type=data.get("token_type", "Bearer"),
            refresh_token=data.get("refresh_token"),
            raw_data=data.get("raw_data", {}),
        )

    def is_expired(self, buffer_seconds: int = 300) -> bool:
        """Check if token is expired (with buffer)."""
        return datetime.utcnow() >= self.expires_at - timedelta(seconds=buffer_seconds)


class OAuthTokenStore:
    """Persistent OAuth token storage with auto-refresh support.

    Stores tokens in the connector_configs table with the schema:
    - connector_id (string, PK)
    - key (string, PK) - typically 'oauth_token'
    - value (text, JSON) - TokenData serialized as JSON
    - expires_at (datetime, nullable)
    """

    def __init__(self, db_path: str | Path):
        """Initialize token store.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self._lock = asyncio.Lock()
        self._refresh_in_progress: dict[str, asyncio.Event] = {}

    async def _ensure_schema(self) -> None:
        """Ensure connector_configs table exists with required schema."""
        async with aiosqlite.connect(self.db_path) as conn:
            # Check if table has the new schema
            cursor = await conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='connector_configs'"
            )
            row = await cursor.fetchone()

            if row is None:
                # Table doesn't exist, create with new schema
                await conn.execute("""
                    CREATE TABLE connector_configs (
                        connector_id TEXT NOT NULL,
                        key TEXT NOT NULL,
                        value TEXT NOT NULL,
                        expires_at TEXT,
                        PRIMARY KEY (connector_id, key)
                    );
                    """)
                await conn.execute(
                    "CREATE INDEX idx_connector_configs_expires ON connector_configs(expires_at);"
                )
                await conn.commit()
                logger.info(f"Created connector_configs table at {self.db_path}")
            else:
                schema_sql = row[0]
                # Check if we need to migrate from old schema
                if "connector_id" in schema_sql and "key" not in schema_sql:
                    # Old schema: (id, connector_id, config_json, updated_at)
                    await self._migrate_old_schema(conn)
                elif "expires_at" not in schema_sql:
                    # Intermediate schema missing expires_at
                    await conn.execute("ALTER TABLE connector_configs ADD COLUMN expires_at TEXT")
                    await conn.execute(
                        "CREATE INDEX IF NOT EXISTS idx_connector_configs_expires "
                        "ON connector_configs(expires_at)"
                    )
                    await conn.commit()
                    logger.info("Added expires_at column to connector_configs")

    async def _migrate_old_schema(self, conn: aiosqlite.Connection) -> None:
        """Migrate from old (id, connector_id, config_json) schema.

        This converts the old format to the new (connector_id, key, value, expires_at) format.
        """
        logger.info("Migrating connector_configs to new schema")

        # Fetch all old data
        cursor = await conn.execute("SELECT connector_id, config_json FROM connector_configs")
        rows = await cursor.fetchall()

        # Create new table
        await conn.execute("""
            CREATE TABLE connector_configs_new (
                connector_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                expires_at TEXT,
                PRIMARY KEY (connector_id, key)
            );
            """)
        await conn.execute(
            "CREATE INDEX idx_connector_configs_new_expires ON connector_configs_new(expires_at);"
        )

        # Migrate data
        for connector_id, config_json in rows:
            try:
                config = json.loads(config_json)
                if "oauth_token" in config:
                    token_data = config["oauth_token"]
                    token_obj = TokenData(
                        access_token=token_data["access_token"],
                        expires_at=datetime.fromisoformat(token_data["expires_at"]),
                        scope=token_data.get("scope"),
                        token_type=token_data.get("token_type", "Bearer"),
                        refresh_token=token_data.get("refresh_token"),
                        raw_data=token_data.get("raw_data", {}),
                    )
                    await conn.execute(
                        """
                        INSERT INTO connector_configs_new (connector_id, key, value, expires_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            connector_id,
                            "oauth_token",
                            json.dumps(token_obj.to_dict()),
                            token_obj.expires_at.isoformat(),
                        ),
                    )
            except Exception as e:
                logger.warning(f"Failed to migrate token for {connector_id}: {e}")

        # Drop old table and rename new one
        await conn.execute("DROP TABLE connector_configs")
        await conn.execute("ALTER TABLE connector_configs_new RENAME TO connector_configs")
        await conn.commit()
        logger.info("Schema migration complete")

    async def get_token(self, connector_id: str) -> Optional[TokenData]:
        """Get stored token if not expired.

        Args:
            connector_id: Connector identifier (e.g., 'ebay')

        Returns:
            TokenData if valid token exists, None otherwise
        """
        async with self._lock:
            await self._ensure_schema()

            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(
                    """
                    SELECT value, expires_at
                    FROM connector_configs
                    WHERE connector_id = ? AND key = 'oauth_token'
                    """,
                    (connector_id,),
                )
                row = await cursor.fetchone()

                if not row:
                    return None

                try:
                    token_dict = json.loads(row["value"])
                    token = TokenData.from_dict(token_dict)

                    if not token.is_expired():
                        return token
                except Exception as e:
                    logger.warning(f"Failed to parse token for {connector_id}: {e}")

                return None

    async def store_token(
        self, connector_id: str, token_data: TokenData, *, replace: bool = True
    ) -> None:
        """Store token in database.

        Args:
            connector_id: Connector identifier
            token_data: Token to store
            replace: If False, skip if token already exists (for idempotency)
        """
        async with self._lock:
            await self._ensure_schema()

            token_json = json.dumps(token_data.to_dict())
            expires_at_str = token_data.expires_at.isoformat()

            async with aiosqlite.connect(self.db_path) as conn:
                if replace:
                    await conn.execute(
                        """
                        INSERT OR REPLACE INTO connector_configs
                        (connector_id, key, value, expires_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (connector_id, "oauth_token", token_json, expires_at_str),
                    )
                else:
                    # Only insert if not exists
                    await conn.execute(
                        """
                        INSERT INTO connector_configs (connector_id, key, value, expires_at)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT (connector_id, key) DO NOTHING
                        """,
                        (connector_id, "oauth_token", token_json, expires_at_str),
                    )
                await conn.commit()

            logger.debug(f"Stored token for {connector_id} (expires at {expires_at_str})")

    async def is_valid(self, connector_id: str, buffer_seconds: int = 300) -> bool:
        """Check if a valid non-expired token exists.

        Args:
            connector_id: Connector identifier
            buffer_seconds: Expiry buffer in seconds (default 5 min)

        Returns:
            True if valid token exists, False otherwise
        """
        token = await self.get_token(connector_id)
        return token is not None and not token.is_expired(buffer_seconds)

    async def refresh_if_needed(
        self, connector_id: str, refresh_func: Callable[[], Awaitable[TokenData]]
    ) -> TokenData:
        """Get token, refreshing if expired or missing.

        Thread-safe: concurrent calls will wait for a single refresh operation.

        Args:
            connector_id: Connector identifier
            refresh_func: Async function that returns a fresh TokenData

        Returns:
            Valid TokenData

        Raises:
            Exception: If refresh fails
        """
        while True:
            token = await self.get_token(connector_id)
            if token is not None:
                return token

            async with self._lock:
                refresh_event = self._refresh_in_progress.get(connector_id)
                should_refresh = refresh_event is None
                if should_refresh:
                    refresh_event = asyncio.Event()
                    self._refresh_in_progress[connector_id] = refresh_event

            if not should_refresh:
                logger.debug(f"Token refresh in progress for {connector_id}, waiting...")
                await refresh_event.wait()
                continue

            try:
                logger.info(f"Refreshing token for {connector_id}")
                # Call the connector-specific refresh function
                new_token = await refresh_func()
                # Store the new token
                await self.store_token(connector_id, new_token)
                logger.info(f"Token refreshed for {connector_id}")
                return new_token
            finally:
                # Signal that refresh is complete
                async with self._lock:
                    refresh_event.set()
                    self._refresh_in_progress.pop(connector_id, None)

    async def delete_token(self, connector_id: str) -> None:
        """Delete stored token.

        Args:
            connector_id: Connector identifier
        """
        async with self._lock:
            await self._ensure_schema()

            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    "DELETE FROM connector_configs WHERE connector_id = ? AND key = 'oauth_token'",
                    (connector_id,),
                )
                await conn.commit()

            logger.debug(f"Deleted token for {connector_id}")

    async def list_connectors(self) -> list[str]:
        """List all connector IDs with stored tokens.

        Returns:
            List of connector IDs
        """
        async with self._lock:
            await self._ensure_schema()

            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute(
                    "SELECT DISTINCT connector_id FROM connector_configs WHERE key = 'oauth_token'"
                )
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
