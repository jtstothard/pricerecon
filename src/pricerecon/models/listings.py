"""Pydantic models for PriceRecon."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Any

from pydantic import BaseModel, Field, field_validator


class Condition(str, Enum):
    """Listing condition enum."""

    NEW = "new"
    NEW_OPEN_BOX = "new_open_box"
    REFURBISHED = "refurbished"
    USED_LIKE_NEW = "used_like_new"
    USED_GOOD = "used_good"
    USED_FAIR = "used_fair"
    FOR_PARTS = "for_parts"


class StockState(str, Enum):
    """Stock state enum."""

    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    BACK_ORDER = "back_order"
    PRE_ORDER = "pre_order"
    DISCONTINUED = "discontinued"


class SourceType(str, Enum):
    """Source type enum."""

    RETAILER = "retailer"
    MARKETPLACE = "marketplace"
    SIGNAL = "signal"


class VariantMatchConfidence(str, Enum):
    """Variant match confidence enum."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class NormalizedListing(BaseModel):
    """Normalized listing schema (tiered).

    All required fields must be populated by connectors.
    Optional enrichment fields default to None.
    """

    schema_version: str = "1.0"

    # Required fields
    source: str = Field(..., description="Connector identifier (e.g., 'ebay', 'cex')")
    source_type: SourceType = Field(..., description="Source role")
    source_listing_id: str = Field(..., description="Stable ID from source")
    title_raw: str = Field(..., description="Original listing title")
    price: Optional[Decimal] = Field(None, description="Current price in source currency (None if not yet enriched)")
    currency: str = Field(..., description="ISO 4217 currency code")
    url: str = Field(..., description="Direct link to listing")
    timestamp_seen: Optional[datetime] = Field(default_factory=datetime.utcnow)

    # Optional enrichment fields
    product_normalized: Optional[str] = Field(None, description="Normalized product name")
    variant_normalized: Optional[dict[str, Any]] = Field(
        None, description="Parsed specs (GPU, RAM, storage, CPU, etc.)"
    )
    condition: Optional[Condition] = Field(None, description="Normalized condition")
    condition_raw: Optional[str] = Field(None, description="Original condition text")
    shipping_cost: Optional[Decimal] = Field(None, description="Shipping cost")
    total_landed_cost: Optional[Decimal] = Field(None, description="price + shipping")
    seller_or_store: Optional[str] = Field(None, description="Seller name")
    seller_feedback_score: Optional[int] = Field(None, description="Feedback count")
    seller_feedback_pct: Optional[Decimal] = Field(None, ge=0, le=100, description="Feedback %")
    location: Optional[str] = Field(None, description="Geographic location")
    in_stock: Optional[bool] = Field(None, description="Item is buyable")
    stock_state: Optional[StockState] = Field(None, description="Stock state")
    image_url: Optional[str] = Field(None, description="Primary product image")
    exact_variant_confirmed: Optional[bool] = Field(None, description="Spec verified")
    variant_match_confidence: Optional[VariantMatchConfidence] = Field(
        None, description="Match confidence"
    )
    mismatch_flags: Optional[list[str]] = Field(
        None, description="Flags like WRONG_VARIANT, ACCESSORIES_ONLY"
    )
    risk_flags: Optional[list[str]] = Field(
        None, description="Flags like LOW_SELLER_FEEDBACK"
    )
    category: Optional[str] = Field(None, description="Product category")

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, v: str) -> str:
        return v.upper()

    class Config:
        json_encoders = {Decimal: str, datetime: lambda v: v.isoformat()}


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    connector_states: dict[str, Any] = Field(default_factory=dict)