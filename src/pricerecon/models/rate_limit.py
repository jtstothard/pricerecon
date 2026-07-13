"""Pydantic models for rate limiting."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class RateLimitWindow(str, Enum):
    """Rate limit time window options."""

    MINUTE = "1m"
    HOUR = "1h"
    DAY = "1d"


class RateLimitConfig(BaseModel):
    """Rate limit configuration for a connector."""

    max_requests: int = Field(..., gt=0, description="Maximum requests per window")
    window: RateLimitWindow = Field(default=RateLimitWindow.HOUR, description="Time window")
    tokens_per_request: int = Field(default=1, gt=0, description="Tokens consumed per request")


class RateLimitStatus(BaseModel):
    """Current rate limit status for a connector."""

    connector_id: str = Field(..., description="Connector identifier")
    max_requests: int = Field(..., description="Maximum requests per window")
    remaining: int = Field(..., description="Remaining requests in current window")
    window: str = Field(..., description="Time window (e.g., '1h', '1d')")
    reset_at: datetime = Field(..., description="When the window resets")
    is_rate_limited: bool = Field(default=False, description="Whether currently rate limited")

    class Config:
        from_attributes = True


class ConnectorRateLimits(BaseModel):
    """Rate limits for multiple connectors."""

    connectors: dict[str, RateLimitStatus] = Field(
        default_factory=dict, description="Rate limit status per connector"
    )
