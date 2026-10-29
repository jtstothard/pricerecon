"""Bounded source observations, distinct from qualified selection or use rights."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EvidenceUse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    permission_reference: str = Field(min_length=1, max_length=250)
    retention: Literal["minimal_fields", "synthetic"]

    @field_validator("permission_reference")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Evidence use requires an explicit reference")
        return value


class SourceReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    route: str
    source_host: str | None = None
    capture_id: str
    retrieved_at: datetime
    use: EvidenceUse | None = None
    history_rights: Literal["unqualified"] = "unqualified"
    prerequisites: list[str] = Field(default_factory=list)
    pages_captured: int = Field(default=0, ge=0)
    page_limit: int | None = Field(default=None, ge=1)
    item_limit: int | None = Field(default=None, ge=1)
    detail_limit: int | None = Field(default=None, ge=1)
    discovered_count: int | None = Field(default=None, ge=0)
    inspected_count: int | None = Field(default=None, ge=0)
    next_page: bool | None = None
    content_truncated: bool | None = None
    completeness: Literal["unknown", "partial", "declared_scope"] = "unknown"
    issues: list[str] = Field(default_factory=list)


class SourceOfferEvidence(BaseModel):
    """Literal source details only. Qualification never consumes this summary."""

    model_config = ConfigDict(extra="forbid")
    merchant_role: Literal["marketplace", "independent_retailer", "retailer", "unknown"] = "unknown"
    selected_options: dict[str, str] = Field(default_factory=dict)
    selected_sku: str | None = None
    price_scope: Literal[
        "selected_variation", "parent_listing", "display_unbound", "auction_bid", "unknown"
    ] = "unknown"
    condition_literal: str | None = None
    seller_literal: str | None = None
    destination: str | None = None
    destination_literal: str | None = None
    quantity: int | None = Field(default=None, ge=1)
    availability_literal: str | None = None
    stock_quantity: int | None = Field(default=None, ge=0)
    purchase_modes: list[str] = Field(default_factory=list)
    shipping_claim: str | None = None
    vat_included_claim: bool | None = None
    other_price_claims: dict[str, str] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
