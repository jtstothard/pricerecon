"""Pydantic models for watch configuration and management."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Any

from pydantic import BaseModel, Field

from .listings import SourceType, Condition


class EventType(str, Enum):
    """Event types emitted by the diff engine."""

    NEW_LISTING = "new_listing"
    PRICE_DROP = "price_drop"
    PRICE_INCREASE = "price_increase"
    STOCK_CHANGE = "stock_change"
    LISTING_GONE = "listing_gone"
    NO_CHANGE = "no_change"


class Severity(str, Enum):
    """Event severity levels."""

    INFO = "info"
    NOTICE = "notice"
    DEBUG = "debug"
    SILENT = "silent"


# ============================================================================
# Source Configuration
# ============================================================================


class SourceConfig(BaseModel):
    """Per-source connector configuration."""

    connector: str = Field(..., description="Connector identifier (e.g., 'ebay', 'cex')")
    enabled: bool = Field(default=True, description="Whether this source is enabled")
    config: dict[str, Any] = Field(
        default_factory=dict, description="Connector-specific configuration"
    )


# ============================================================================
# Watch Filter Configuration
# ============================================================================


class ConditionFilter(BaseModel):
    """Condition filter configuration."""

    conditions: list[Condition] = Field(default_factory=list, description="Allowed conditions")
    dedup_enabled: bool = Field(default=False, description="Enable condition-tier deduplication")


class SpecMatch(BaseModel):
    """Spec matching configuration."""

    gpu_model: Optional[str] = None
    ram_gb: Optional[int] = None
    storage_gb: Optional[int] = None
    cpu_model: Optional[str] = None


class WatchFilters(BaseModel):
    """Watch filtering rules."""

    price_max: Optional[Decimal] = Field(None, ge=0, description="Maximum price")
    currency: str = Field(default="GBP", description="Currency for price_max")
    condition_filter: ConditionFilter = Field(default_factory=ConditionFilter)
    exclude_patterns: list[str] = Field(
        default_factory=list, description="Title exclusion patterns"
    )
    spec_match: SpecMatch = Field(default_factory=SpecMatch)
    min_seller_feedback: Optional[int] = Field(
        None, ge=0, description="Minimum seller feedback score"
    )
    min_seller_feedback_pct: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Minimum feedback %"
    )


# ============================================================================
# Watch Scheduling Configuration
# ============================================================================


class WatchSchedule(BaseModel):
    """Watch scheduling configuration."""

    interval: str = Field(default="4h", description="Interval between checks (e.g., '4h', '30m')")
    timezone: str = Field(default="UTC", description="Timezone for scheduling")
    time_window: Optional[dict[str, Any]] = Field(
        None, description="Optional time window constraints (start, end, days)"
    )


# ============================================================================
# Watch Notification Configuration
# ============================================================================


class WatchNotification(BaseModel):
    """Notification configuration for a watch."""

    events: list[EventType] = Field(
        default_factory=lambda: [
            EventType.NEW_LISTING,
            EventType.PRICE_DROP,
            EventType.STOCK_CHANGE,
        ],
        description="Events to notify on",
    )
    channels: list[str] = Field(
        default_factory=lambda: ["webhook"],
        description="Notification channels (webhook, telegram, discord)",
    )
    webhook_url: Optional[str] = Field(None, description="Webhook URL for webhook notifications")
    telegram_bot_token: Optional[str] = Field(None, description="Telegram bot token override")
    telegram_chat_id: Optional[str] = Field(None, description="Telegram chat ID override")
    discord_webhook_url: Optional[str] = Field(None, description="Discord webhook URL override")


# ============================================================================
# Watch Grouping Configuration
# ============================================================================


class WatchGrouping(BaseModel):
    """Watch grouping configuration."""

    enabled: bool = Field(default=False, description="Enable grouping")
    product_key: Optional[str] = Field(None, description="Key for aggregate display/alerts")


# ============================================================================
# Watch Models
# ============================================================================


class WatchBase(BaseModel):
    """Base watch model."""

    name: str = Field(..., min_length=1, description="Watch name")
    query: str = Field(..., min_length=1, description="Search query")
    category: Optional[str] = Field(None, description="Product category (e.g., 'gpu', 'cpu')")
    sources: list[SourceConfig] = Field(
        default_factory=lambda: [SourceConfig(connector="ebay")],
        description="Source configurations",
    )
    filters: WatchFilters = Field(default_factory=WatchFilters)
    schedule: WatchSchedule = Field(default_factory=WatchSchedule)
    grouping: WatchGrouping = Field(default_factory=WatchGrouping)
    notifications: WatchNotification = Field(default_factory=WatchNotification)
    enabled: bool = Field(default=True, description="Whether this watch is active")


class WatchCreate(WatchBase):
    """Request model for creating a watch."""

    pass


class WatchUpdate(WatchBase):
    """Request model for updating a watch."""

    pass


class Watch(WatchBase):
    """Watch model with database fields."""

    id: int
    created_at: datetime
    updated_at: datetime
    last_check_at: Optional[datetime] = None
    status: str = Field(default="active", description="Watch status")

    class Config:
        from_attributes = True


# ============================================================================
# Event and History Models
# ============================================================================


class Event(BaseModel):
    """Event emitted by the diff engine."""

    id: int
    watch_id: int
    event_type: EventType
    severity: Severity
    listing_id: Optional[str] = None
    data: dict[str, Any] = Field(default_factory=dict, description="Event-specific data")
    timestamp: datetime

    class Config:
        from_attributes = True


class PriceHistory(BaseModel):
    """Price history point for a listing."""

    id: int
    watch_id: int
    listing_id: str
    price: Decimal
    currency: str
    timestamp: datetime
    in_stock: Optional[bool] = None

    class Config:
        from_attributes = True


# ============================================================================
# Source/Connector Models
# ============================================================================


class SourceInfo(BaseModel):
    """Information about a configured source/connector."""

    connector: str
    name: str
    source_type: SourceType
    enabled: bool
    status: str = Field(default="healthy", description="Connector health state")
    last_error: Optional[str] = Field(default=None, description="Last error message")
    config: dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# API Response Models
# ============================================================================


class WatchCheckResponse(BaseModel):
    """Response from triggering an immediate watch check."""

    watch_id: int
    status: str
    message: str
    started_at: datetime
    result: Optional[dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    detail: Optional[str] = None
    status_code: int = 400
