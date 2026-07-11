"""Connector status and degraded-state helpers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ConnectorStatus(str, Enum):
    ok = "ok"
    bot_blocked = "bot_blocked"
    rate_limited = "rate_limited"
    auth_failed = "auth_failed"
    parse_error = "parse_error"
    timeout = "timeout"
    unknown_error = "unknown_error"
    disabled = "disabled"


@dataclass(slots=True)
class ConnectorDegradedError(Exception):
    """Structured degraded-state exception raised by connectors."""

    status: ConnectorStatus
    message: str
    connector_id: str
    detail: dict[str, Any] | None = None

    def __str__(self) -> str:
        return self.message
