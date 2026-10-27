"""Token bucket rate limiter per connector."""

import logging
import sqlite3
import time
from collections.abc import Mapping
from contextlib import closing
from datetime import UTC, datetime, timedelta, timezone
from threading import Lock
from typing import Literal, Optional

from pricerecon.models.collection import OperatingPolicy, Priority, Resource
from pricerecon.models.rate_limit import (
    RateLimitConfig,
    RateLimitStatus,
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
            self.tokens = int(min(self.capacity, self.tokens + tokens_to_add))
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
                return datetime.now(timezone.utc)

            # Time until next full reset
            time_until_reset = self.window_seconds - elapsed
            return datetime.now(timezone.utc) + timedelta(seconds=time_until_reset)

    def reset(self) -> None:
        """Reset the bucket to full capacity."""
        with self._lock:
            self.tokens = self.capacity
            self.last_refill_time = time.time()


class ConnectorRateLimiter:
    """Per-connector rate limiter using token bucket algorithm."""

    def __init__(self) -> None:
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
                logger.warning(
                    f"No default rate limit for connector {connector_id}, using generous defaults"
                )
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


# Finite envelopes deliberately do not inherit/refill the legacy token defaults.
# SQLite BEGIN IMMEDIATE serializes reservations across threads and processes.
class AdmissionDenied(BaseException):
    """Control signal: adapter retry/fallback handlers must not swallow admission."""
    def __init__(self, reason: str, *, state: Literal['blocked', 'capped'] = 'capped') -> None:
        self.reason = reason
        self.state = state
        super().__init__(reason)


class DurableAdmission:
    """Native limiter's explicit, durable collection-accounting boundary."""

    def __init__(self, policy: OperatingPolicy, source: str, purpose: Priority,
                 context_id: int | str, *, query: str = "") -> None:
        self.policy = policy
        self.source = source
        self.purpose = purpose
        self.context_id = str(context_id)
        self.query = query
        self.attempt_id: str | None = None
        self.requests: dict[str, int] = {}

    def debit(self, costs: Mapping[Resource, int], *,
              connection: sqlite3.Connection | None = None) -> None:
        from pricerecon.db.schema import DB_PATH

        now = datetime.now(UTC)
        if not self.policy.starts_at <= now < self.policy.stops_at:
            raise AdmissionDenied('operating_policy_expired', state='blocked')
        if connection is None:
            with closing(sqlite3.connect(DB_PATH)) as owned, owned:
                owned.execute('BEGIN IMMEDIATE')
                self.debit(costs, connection=owned)
            return
        payload = self.policy.model_dump_json()
        saved = connection.execute(
            'SELECT payload_json FROM collection_policies WHERE scope_id=?',
            (self.policy.scope_id,),
        ).fetchone()
        if saved and saved[0] != payload:
            raise AdmissionDenied('operating_policy_changed', state='blocked')
        connection.execute('INSERT OR IGNORE INTO collection_policies VALUES (?, ?)',
                           (self.policy.scope_id, payload))
        for resource, amount in costs.items():
            if not isinstance(amount, int) or amount < 0:
                raise ValueError('Resource debit must be a nonnegative integer')
            cap = self.policy.caps.get(resource)
            if cap is None:
                raise AdmissionDenied(f'resource_policy_required:{resource}', state='blocked')
            row = connection.execute(
                'SELECT used FROM collection_usage WHERE scope_id=? AND resource=?',
                (self.policy.scope_id, resource),
            ).fetchone()
            used = row[0] if row else 0
            ceiling = cap.limit - (cap.tracking_reserve if self.purpose == 'discovery' else 0)
            if used + amount > ceiling:
                reserved = self.purpose == 'discovery' and used + amount <= cap.limit
                raise AdmissionDenied(
                    f'{"tracking_capacity_reserved" if reserved else "resource_exhausted"}:{resource}'
                )
        provider_key = f"provider:{self.source}:requests"
        provider_amount = costs.get("requests", 0)
        if provider_amount:
            cap = self.policy.provider_request_caps.get(self.source)
            if cap is None:
                raise AdmissionDenied(f"provider_policy_required:{self.source}", state="blocked")
            row = connection.execute(
                "SELECT used FROM collection_usage WHERE scope_id=? AND resource=?",
                (self.policy.scope_id, provider_key),
            ).fetchone()
            used = row[0] if row else 0
            ceiling = cap.limit - (cap.tracking_reserve if self.purpose == "discovery" else 0)
            if used + provider_amount > ceiling:
                raise AdmissionDenied(f"provider_requests_exhausted:{self.source}")
        for resource, amount in costs.items():
            connection.execute('''INSERT INTO collection_usage VALUES (?, ?, ?)
                ON CONFLICT(scope_id, resource) DO UPDATE SET used=used+excluded.used''',
                (self.policy.scope_id, resource, amount))
        if provider_amount:
            connection.execute("""INSERT INTO collection_usage VALUES (?, ?, ?)
                ON CONFLICT(scope_id, resource) DO UPDATE SET used=used+excluded.used""",
                (self.policy.scope_id, provider_key, provider_amount))


    def begin(self) -> None:
        import sqlite3
        from contextlib import closing
        from uuid import uuid4

        from pricerecon.db.schema import DB_PATH

        now = datetime.now(UTC)
        attempt_id = str(uuid4())
        reason = None
        with closing(sqlite3.connect(DB_PATH)) as connection, connection:
            connection.execute('BEGIN IMMEDIATE')
            rows = connection.execute('''SELECT id, state, next_eligible_at FROM collection_attempts
                WHERE scope_id=? AND source=? AND next_eligible_at IS NOT NULL
                ORDER BY rowid DESC LIMIT 1''', (self.policy.scope_id, self.source)).fetchone()
            if rows:
                next_at = datetime.fromisoformat(rows[2])
                if next_at > now:
                    reason = 'recovery_spacing'
                elif rows[1] == 'running':
                    connection.execute('''UPDATE collection_attempts SET state='interrupted',
                        reason='lease_expired_unconfirmed' WHERE id=?''', (rows[0],))
            # The durable lease outlives the enforced run timeout. A killed process
            # consumes its reservation; recovery never replays missed periods.
            next_eligible = now + timedelta(seconds=(
                self.policy.run_timeout_seconds + self.policy.recovery_spacing_seconds
            ))
            last_good = connection.execute('''SELECT MAX(attempted_at) FROM collection_attempts
                WHERE source=? AND query=? AND state IN ('success', 'success_empty')''',
                (self.source, self.query)).fetchone()[0]
            connection.execute('''INSERT INTO collection_attempts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (attempt_id, self.policy.scope_id, self.source, self.purpose, self.context_id, self.query,
                 now.isoformat(), 'capped' if reason else 'running', reason,
                 None if reason else next_eligible.isoformat(), last_good))
        self.attempt_id = attempt_id
        if reason:
            raise AdmissionDenied(reason)
        self.debit({'elapsed_seconds': self.policy.run_timeout_seconds})

    def finish(self, state: str, reason: str | None = None) -> None:
        import sqlite3
        from contextlib import closing

        from pricerecon.db.schema import DB_PATH

        if not self.attempt_id:
            return
        now = datetime.now(UTC)
        with closing(sqlite3.connect(DB_PATH)) as connection, connection:
            # A denied overlap cannot extend the existing source lease.
            connection.execute('''UPDATE collection_attempts SET state=?, reason=?,
                last_good_at=CASE WHEN ? IN ('success', 'success_empty') THEN attempted_at
                    ELSE last_good_at END,
                next_eligible_at=CASE WHEN state='running' THEN ? ELSE next_eligible_at END
                WHERE id=?''', (state, reason, state,
                (now + timedelta(seconds=self.policy.recovery_spacing_seconds if state in {"success", "success_empty", "partial", "cache_reuse", "failed"} else 0)).isoformat(),
                self.attempt_id))
