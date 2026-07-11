"""Tests for the token bucket rate limiter."""

import asyncio
from datetime import datetime, timedelta

import pytest

from pricerecon.core.rate_limiter import (
    ConnectorRateLimiter,
    TokenBucket,
    get_rate_limiter,
    init_rate_limiter,
)
from pricerecon.models.rate_limit import (
    RateLimitConfig,
    RateLimitStatus,
    RateLimitWindow,
)


class TestTokenBucket:
    """Test TokenBucket class."""

    def test_initial_capacity(self):
        """Test bucket starts with full capacity."""
        bucket = TokenBucket(capacity=10, window_seconds=60)
        assert bucket.get_remaining() == 10

    def test_single_acquire(self):
        """Test acquiring a single token."""
        bucket = TokenBucket(capacity=10, window_seconds=60)
        assert bucket.try_acquire(1) is True
        assert bucket.get_remaining() == 9

    def test_multiple_acquires(self):
        """Test acquiring multiple tokens."""
        bucket = TokenBucket(capacity=10, window_seconds=60)
        assert bucket.try_acquire(3) is True
        assert bucket.get_remaining() == 7

    def test_exhaust_bucket(self):
        """Test exhausting the bucket."""
        bucket = TokenBucket(capacity=5, window_seconds=60)
        assert bucket.try_acquire(5) is True
        assert bucket.get_remaining() == 0
        assert bucket.try_acquire(1) is False

    def test_partial_exhaust(self):
        """Test exhausting when not enough tokens remain."""
        bucket = TokenBucket(capacity=5, window_seconds=60)
        assert bucket.try_acquire(3) is True
        assert bucket.try_acquire(3) is False  # Only 2 left
        assert bucket.get_remaining() == 2

    def test_reset(self):
        """Test resetting the bucket."""
        bucket = TokenBucket(capacity=10, window_seconds=60)
        bucket.try_acquire(5)
        assert bucket.get_remaining() == 5
        bucket.reset()
        assert bucket.get_remaining() == 10

    def test_reset_time(self):
        """Test reset time calculation."""
        bucket = TokenBucket(capacity=10, window_seconds=60)
        reset_time = bucket.get_reset_time()
        now = datetime.utcnow()

        # Reset time should be approximately 1 minute in the future
        assert reset_time >= now + timedelta(seconds=59)
        assert reset_time <= now + timedelta(seconds=61)

    def test_reset_time_after_exhaust(self):
        """Test reset time after exhausting bucket."""
        bucket = TokenBucket(capacity=10, window_seconds=60)
        bucket.try_acquire(10)
        reset_time = bucket.get_reset_time()
        now = datetime.utcnow()

        # Reset time should be approximately 1 minute in the future
        assert reset_time >= now + timedelta(seconds=59)
        assert reset_time <= now + timedelta(seconds=61)

    def test_concurrent_acquires(self):
        """Test thread-safe concurrent acquires."""
        import threading

        bucket = TokenBucket(capacity=100, window_seconds=60)
        results = []

        def acquire_tokens():
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

    def test_configure_connector(self):
        """Test configuring a connector."""
        limiter = ConnectorRateLimiter()
        config = RateLimitConfig(
            max_requests=100,
            window=RateLimitWindow.HOUR,
        )
        limiter.configure_connector("test_connector", config)

        assert "test_connector" in limiter.list_connectors()

    def test_auto_configure_default(self):
        """Test auto-configuring with default limits."""
        limiter = ConnectorRateLimiter()

        # eBay has default config
        limiter.configure_connector("ebay")
        assert "ebay" in limiter.list_connectors()

        # Unknown connector gets generous defaults
        limiter.configure_connector("unknown")
        assert "unknown" in limiter.list_connectors()

    def test_acquire_allowed(self):
        """Test acquiring when under limit."""
        limiter = ConnectorRateLimiter()
        config = RateLimitConfig(
            max_requests=10,
            window=RateLimitWindow.HOUR,
        )
        limiter.configure_connector("test", config)

        assert limiter.acquire("test", 1) is True

    def test_acquire_rate_limited(self):
        """Test acquiring when over limit."""
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

    def test_acquire_multiple_tokens(self):
        """Test acquiring multiple tokens at once."""
        limiter = ConnectorRateLimiter()
        config = RateLimitConfig(
            max_requests=10,
            window=RateLimitWindow.HOUR,
        )
        limiter.configure_connector("test", config)

        assert limiter.acquire("test", 5) is True
        assert limiter.acquire("test", 6) is False  # Only 5 left

    def test_get_status(self):
        """Test getting rate limit status."""
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

    def test_get_status_unknown_connector(self):
        """Test getting status for unknown connector."""
        limiter = ConnectorRateLimiter()
        status = asyncio.run(limiter.get_status("unknown"))
        assert status is None

    def test_reset(self):
        """Test resetting a connector's bucket."""
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

    def test_async_acquire(self):
        """Test async acquire method."""
        limiter = ConnectorRateLimiter()
        config = RateLimitConfig(
            max_requests=10,
            window=RateLimitWindow.HOUR,
        )
        limiter.configure_connector("test", config)

        async def test_async():
            result = await limiter.acquire_async("test", 1)
            return result

        assert asyncio.run(test_async()) is True

    def test_multiple_connectors(self):
        """Test rate limiting multiple connectors independently."""
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

    def test_get_rate_limiter(self):
        """Test getting global limiter instance."""
        limiter = get_rate_limiter()
        assert isinstance(limiter, ConnectorRateLimiter)

        # Should return same instance
        limiter2 = get_rate_limiter()
        assert limiter is limiter2

    def test_init_rate_limiter(self):
        """Test initializing global limiter."""
        limiter = init_rate_limiter()
        assert isinstance(limiter, ConnectorRateLimiter)

        # Should return same instance
        limiter2 = init_rate_limiter()
        assert limiter is limiter2