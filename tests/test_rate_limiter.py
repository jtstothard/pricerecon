"""Tests for the token bucket rate limiter."""

import asyncio
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone

from pricerecon.core.rate_limiter import (
    ConnectorRateLimiter,
    DurableAdmission,
    TokenBucket,
    get_rate_limiter,
    init_rate_limiter,
)
from pricerecon.models.collection import OperatingPolicy
from pricerecon.models.rate_limit import (
    RateLimitConfig,
    RateLimitWindow,
)


class TestTokenBucket:
    """Test TokenBucket class."""

    def test_initial_capacity(self) -> None:
        bucket = TokenBucket(capacity=10, window_seconds=60)
        assert bucket.get_remaining() == 10

    def test_single_acquire(self) -> None:
        bucket = TokenBucket(capacity=10, window_seconds=60)
        assert bucket.try_acquire(1) is True
        assert bucket.get_remaining() == 9

    def test_multiple_acquires(self) -> None:
        bucket = TokenBucket(capacity=10, window_seconds=60)
        assert bucket.try_acquire(3) is True
        assert bucket.get_remaining() == 7

    def test_exhaust_bucket(self) -> None:
        bucket = TokenBucket(capacity=5, window_seconds=60)
        assert bucket.try_acquire(5) is True
        assert bucket.get_remaining() == 0
        assert bucket.try_acquire(1) is False

    def test_partial_exhaust(self) -> None:
        bucket = TokenBucket(capacity=5, window_seconds=60)
        assert bucket.try_acquire(3) is True
        assert bucket.try_acquire(3) is False  # Only 2 left
        assert bucket.get_remaining() == 2

    def test_reset(self) -> None:
        bucket = TokenBucket(capacity=10, window_seconds=60)
        bucket.try_acquire(5)
        assert bucket.get_remaining() == 5
        bucket.reset()
        assert bucket.get_remaining() == 10

    def test_reset_time(self) -> None:
        bucket = TokenBucket(capacity=10, window_seconds=60)
        reset_time = bucket.get_reset_time()
        now = datetime.now(timezone.utc)

        # Reset time should be approximately 1 minute in the future
        assert reset_time >= now + timedelta(seconds=59)
        assert reset_time <= now + timedelta(seconds=61)

    def test_reset_time_after_exhaust(self) -> None:
        bucket = TokenBucket(capacity=10, window_seconds=60)
        bucket.try_acquire(10)
        reset_time = bucket.get_reset_time()
        now = datetime.now(timezone.utc)

        # Reset time should be approximately 1 minute in the future
        assert reset_time >= now + timedelta(seconds=59)
        assert reset_time <= now + timedelta(seconds=61)

    def test_concurrent_acquires(self) -> None:
        import threading

        bucket = TokenBucket(capacity=100, window_seconds=60)
        results = []

        def acquire_tokens() -> None:
            for _ in range(10):
                results.append(bucket.try_acquire(1))

        threads = [threading.Thread(target=acquire_tokens) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have exactly 100 successful acquires
        assert sum(results) == 100
        assert bucket.get_remaining() == 0


class TestConnectorRateLimiter:
    """Test ConnectorRateLimiter class."""

    def test_configure_connector(self) -> None:
        limiter = ConnectorRateLimiter()
        config = RateLimitConfig(
            max_requests=100,
            window=RateLimitWindow.HOUR,
        )
        limiter.configure_connector("test_connector", config)

        assert "test_connector" in limiter.list_connectors()

    def test_auto_configure_default(self) -> None:
        limiter = ConnectorRateLimiter()

        # eBay has default config
        limiter.configure_connector("ebay")
        assert "ebay" in limiter.list_connectors()

        # Unknown connector gets generous defaults
        limiter.configure_connector("unknown")
        assert "unknown" in limiter.list_connectors()

    def test_acquire_allowed(self) -> None:
        limiter = ConnectorRateLimiter()
        config = RateLimitConfig(
            max_requests=10,
            window=RateLimitWindow.HOUR,
        )
        limiter.configure_connector("test", config)

        assert limiter.acquire("test", 1) is True

    def test_acquire_rate_limited(self) -> None:
        limiter = ConnectorRateLimiter()
        config = RateLimitConfig(
            max_requests=5,
            window=RateLimitWindow.HOUR,
        )
        limiter.configure_connector("test", config)

        # Exhaust bucket
        for _ in range(5):
            assert limiter.acquire("test", 1) is True

        # Next acquire should fail
        assert limiter.acquire("test", 1) is False

    def test_acquire_multiple_tokens(self) -> None:
        limiter = ConnectorRateLimiter()
        config = RateLimitConfig(
            max_requests=10,
            window=RateLimitWindow.HOUR,
        )
        limiter.configure_connector("test", config)

        assert limiter.acquire("test", 5) is True
        assert limiter.acquire("test", 6) is False  # Only 5 left

    def test_get_status(self) -> None:
        limiter = ConnectorRateLimiter()
        config = RateLimitConfig(
            max_requests=10,
            window=RateLimitWindow.HOUR,
        )
        limiter.configure_connector("test", config)

        # Use some tokens
        limiter.acquire("test", 3)

        # Check status
        status = asyncio.run(limiter.get_status("test"))
        assert status is not None
        assert status.connector_id == "test"
        assert status.max_requests == 10
        assert status.remaining == 7
        assert status.window == "1h"

    def test_get_status_unknown_connector(self) -> None:
        limiter = ConnectorRateLimiter()
        status = asyncio.run(limiter.get_status("unknown"))
        assert status is None

    def test_reset(self) -> None:
        limiter = ConnectorRateLimiter()
        config = RateLimitConfig(
            max_requests=10,
            window=RateLimitWindow.HOUR,
        )
        limiter.configure_connector("test", config)

        # Exhaust bucket
        for _ in range(10):
            limiter.acquire("test", 1)

        assert limiter.acquire("test", 1) is False

        # Reset
        asyncio.run(limiter.reset("test"))

        # Should be able to acquire again
        assert limiter.acquire("test", 1) is True

    def test_async_acquire(self) -> None:
        limiter = ConnectorRateLimiter()
        config = RateLimitConfig(
            max_requests=10,
            window=RateLimitWindow.HOUR,
        )
        limiter.configure_connector("test", config)

        async def test_async() -> bool:
            result = await limiter.acquire_async("test", 1)
            return result

        assert asyncio.run(test_async()) is True

    def test_multiple_connectors(self) -> None:
        limiter = ConnectorRateLimiter()

        config1 = RateLimitConfig(max_requests=5, window=RateLimitWindow.HOUR)
        config2 = RateLimitConfig(max_requests=10, window=RateLimitWindow.HOUR)

        limiter.configure_connector("connector1", config1)
        limiter.configure_connector("connector2", config2)

        # Exhaust connector1
        for _ in range(5):
            assert limiter.acquire("connector1", 1) is True
        assert limiter.acquire("connector1", 1) is False

        # connector2 should still work
        for _ in range(10):
            assert limiter.acquire("connector2", 1) is True
        assert limiter.acquire("connector2", 1) is False


class TestGlobalLimiter:
    """Test global limiter singleton."""

    def test_get_rate_limiter(self) -> None:
        limiter = get_rate_limiter()
        assert isinstance(limiter, ConnectorRateLimiter)

        # Should return same instance
        limiter2 = get_rate_limiter()
        assert limiter is limiter2

    def test_init_rate_limiter(self) -> None:
        limiter = init_rate_limiter()
        assert isinstance(limiter, ConnectorRateLimiter)

        # Should return same instance
        limiter2 = init_rate_limiter()
        assert limiter is limiter2


def _fresh_install_policy(source: str) -> OperatingPolicy:
    """Explicit synthetic envelope; confers no production limits or rights."""
    now = datetime.now(timezone.utc)
    return OperatingPolicy(
        scope_id="fresh-install-admission",
        version="synthetic-v1",
        owner_reference="rate-limiter-test",
        permission_reference="original-fixtures",
        retention_reference="temporary-directory-only",
        starts_at=now,
        stops_at=now + timedelta(hours=1),
        recovery_spacing_seconds=0,
        run_timeout_seconds=60,
        provider_request_caps={source: {"limit": 100, "tracking_reserve": 0}},
        caps={
            name: {"limit": amount, "tracking_reserve": 0}
            for name, amount in (
                ("requests", 100),
                ("pages", 100),
                ("details", 100),
                ("retries", 100),
                ("fallbacks", 100),
                ("storage_bytes", 10_000_000),
                ("elapsed_seconds", 10_000),
            )
        },
    )


class TestDurableAdmissionFreshDatabase:
    """m1 (adversarial review, 2026-10-29): owned admission paths self-initialize.

    A connector's first admission action can be the first database touch of a
    fresh install; debit/begin/finish on owned connections (and a
    caller-supplied idle connection) must not depend on init_db having run
    earlier in the process.
    """

    def test_begin_debit_finish_initialize_a_truly_fresh_database(
        self, tmp_path, monkeypatch
    ) -> None:
        from pricerecon.core.collection_policy import current_policy, operating_policy
        from pricerecon.db import schema

        database = tmp_path / "fresh.db"
        monkeypatch.setattr(schema, "DB_PATH", database)
        policy = _fresh_install_policy("ebay")
        admission = DurableAdmission(policy, "ebay", "discovery", "fresh-install")

        # Production ordering: bind the grant, then reserve and account.
        with operating_policy(policy):
            assert current_policy() == policy
            admission.begin()
            admission.debit({"requests": 1})
            admission.finish("success_empty")

        with closing(sqlite3.connect(database)) as connection:
            states = connection.execute("SELECT state FROM collection_attempts").fetchall()
        assert states == [("success_empty",)]

    def test_select_policy_with_supplied_fresh_connection_initializes(self, tmp_path, monkeypatch) -> None:
        from pricerecon.core.collection_policy import operating_policy
        from pricerecon.db import schema
        from pricerecon.db.connection import connect

        database = tmp_path / "fresh-supplied.db"
        monkeypatch.setattr(schema, "DB_PATH", database)
        policy = _fresh_install_policy("ebay")

        with operating_policy(policy), closing(connect(database)) as supplied:
            selection = DurableAdmission.select_policy(supplied)

        assert selection.reason is None
        assert selection.policy == policy
