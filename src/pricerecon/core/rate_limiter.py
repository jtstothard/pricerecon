"""Token bucket rate limiter per connector."""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from threading import Lock
from typing import Optional

from pricerecon.models.rate_limit import (
    RateLimitStatus,
    RateLimitConfig,
    RateLimitWindow,
)

logger = logging.getLogger(__name__)


# Default rate limits per connector (from PRD section 8.1)
DEFAULT_RATE_LIMITS = {
    "ebay": RateLimitConfig(
        max_requests=5000,
        window=RateLimitWindow.DAY,
        tokens_per_request=1,
    ),
    "cex": RateLimitConfig(
        max_requests=10000,  # Generous limit
        window=RateLimitWindow.DAY,
        tokens_per_request=1,
    ),
    "amazon_uk": RateLimitConfig(
        max_requests=1000,  # Reasonable default for unknown limit
        window=RateLimitWindow.DAY,
        tokens_per_request=1,
    ),
    "facebook_marketplace": RateLimitConfig(
        max_requests=150,  # ~100-150/hr
        window=RateLimitWindow.HOUR,
        tokens_per_request=1,
    ),
}


class TokenBucket:
    """Thread-safe token bucket for rate limiting."""

    def __init__(self, capacity: int, window_seconds: int):
        """Initialize token bucket.

        Args:
            capacity: Maximum number of tokens (max_requests)
            window_seconds: Time window in seconds for token refill
        """
        self.capacity = capacity
        self.window_seconds = window_seconds
        self.tokens = capacity
        self.last_refill_time = time.time()
        self._lock = Lock()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill_time

        if elapsed >= self.window_seconds:
            # Full reset if window has passed
            self.tokens = self.capacity
            self.last_refill_time = now
        else:
            # Proportional refill for partial windows
            # Refill rate: capacity tokens / window_seconds
            tokens_to_add = (elapsed / self.window_seconds) * self.capacity
            self.tokens = min(self.capacity, self.tokens + tokens_to_add)
            self.last_refill_time = now

    def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired, False if rate limited
        """
        with self._lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def get_remaining(self) -> int:
        """Get remaining tokens.

        Returns:
            Number of tokens remaining
        """
        with self._lock:
            self._refill()
            return int(self.tokens)

    def get_reset_time(self) -> datetime:
        """Get when the bucket will be fully reset.

        Returns:
            datetime when tokens will be at capacity
        """
        with self._lock:
            now = time.time()
            elapsed = now - self.last_refill_time

            if elapsed >= self.window_seconds:
                # Already reset
                return datetime.utcnow()

            # Time until next full reset
            time_until_reset = self.window_seconds - elapsed
            return datetime.utcnow() + timedelta(seconds=time_until_reset)

    def reset(self) -> None:
        """Reset the bucket to full capacity."""
        with self._lock:
            self.tokens = self.capacity
            self.last_refill_time = time.time()


class ConnectorRateLimiter:
    """Per-connector rate limiter using token bucket algorithm."""

    def __init__(self):
        """Initialize the rate limiter."""
        self._buckets: dict[str, TokenBucket] = {}
        self._configs: dict[str, RateLimitConfig] = {}
        self._lock = Lock()

    def configure_connector(
        self,
        connector_id: str,
        config: Optional[RateLimitConfig] = None,
    ) -> None:
        """Configure rate limits for a connector.

        Args:
            connector_id: Connector identifier (e.g., 'ebay', 'cex')
            config: Rate limit configuration (uses default if None)
        """
        if config is None:
            # Use default config for known connectors
            config = DEFAULT_RATE_LIMITS.get(connector_id)
            if config is None:
                logger.warning(f"No default rate limit for connector {connector_id}, using generous defaults")
                config = RateLimitConfig(
                    max_requests=1000,
                    window=RateLimitWindow.HOUR,
                    tokens_per_request=1,
                )

        window_seconds = self._window_to_seconds(config.window)

        with self._lock:
            self._configs[connector_id] = config
            # Create new bucket if doesn't exist or config changed
            if connector_id not in self._buckets:
                self._buckets[connector_id] = TokenBucket(
                    capacity=config.max_requests,
                    window_seconds=window_seconds,
                )
                logger.info(
                    f"Configured rate limiter for {connector_id}: "
                    f"{config.max_requests} requests per {config.window.value}"
                )

    def acquire(self, connector_id: str, tokens: int = 1) -> bool:
        """Try to acquire tokens for a connector request.

        Args:
            connector_id: Connector identifier
            tokens: Number of tokens to acquire (default 1)

        Returns:
            True if allowed, False if rate limited
        """
        # Auto-configure if not already configured
        if connector_id not in self._buckets:
            self.configure_connector(connector_id)

        bucket = self._buckets[connector_id]
        allowed = bucket.try_acquire(tokens)

        if not allowed:
            logger.debug(
                f"Rate limited for {connector_id}: "
                f"requested {tokens} tokens, remaining {bucket.get_remaining()}"
            )

        return allowed

    async def acquire_async(self, connector_id: str, tokens: int = 1) -> bool:
        """Async wrapper for acquire (for API compatibility).

        Args:
            connector_id: Connector identifier
            tokens: Number of tokens to acquire

        Returns:
            True if allowed, False if rate limited
        """
        # Token bucket operations are fast, so we can just call sync version
        return self.acquire(connector_id, tokens)

    async def get_status(self, connector_id: str) -> Optional[RateLimitStatus]:
        """Get rate limit status for a connector.

        Args:
            connector_id: Connector identifier

        Returns:
            RateLimitStatus or None if connector not configured
        """
        if connector_id not in self._buckets:
            return None

        bucket = self._buckets[connector_id]
        config = self._configs[connector_id]

        return RateLimitStatus(
            connector_id=connector_id,
            max_requests=config.max_requests,
            remaining=bucket.get_remaining(),
            window=config.window.value,
            reset_at=bucket.get_reset_time(),
        )

    async def reset(self, connector_id: str) -> None:
        """Reset rate limit bucket for a connector.

        Args:
            connector_id: Connector identifier
        """
        if connector_id in self._buckets:
            self._buckets[connector_id].reset()
            logger.info(f"Reset rate limit bucket for {connector_id}")

    def _window_to_seconds(self, window: RateLimitWindow) -> int:
        """Convert window enum to seconds.

        Args:
            window: Rate limit window

        Returns:
            Number of seconds
        """
        mapping = {
            RateLimitWindow.MINUTE: 60,
            RateLimitWindow.HOUR: 3600,
            RateLimitWindow.DAY: 86400,
        }
        return mapping.get(window, 3600)  # Default to 1 hour

    def list_connectors(self) -> list[str]:
        """List all configured connectors.

        Returns:
            List of connector IDs
        """
        return list(self._buckets.keys())


# Global rate limiter instance (singleton pattern)
_global_limiter: Optional[ConnectorRateLimiter] = None


def get_rate_limiter() -> ConnectorRateLimiter:
    """Get the global rate limiter instance.

    Returns:
        ConnectorRateLimiter instance (creates if doesn't exist)
    """
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = ConnectorRateLimiter()
    return _global_limiter


def init_rate_limiter() -> ConnectorRateLimiter:
    """Initialize the global rate limiter instance.

    Returns:
        ConnectorRateLimiter instance
    """
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = ConnectorRateLimiter()
    return _global_limiter