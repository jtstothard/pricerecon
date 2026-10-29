"""Explicit finite operating envelopes. No numerical production defaults."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Resource = Literal[
    "requests",
    "pages",
    "details",
    "retries",
    "fallbacks",
    "browser_contexts",
    "browser_seconds",
    "ai_calls",
    "ai_tokens",
    "storage_bytes",
    "elapsed_seconds",
]
Priority = Literal["discovery", "tracking", "verification"]


class CollectionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ResourceCap(CollectionModel):
    limit: int = Field(ge=0, strict=True)
    tracking_reserve: int = Field(ge=0, strict=True)

    @model_validator(mode="after")
    def reserve_fits(self) -> "ResourceCap":
        if self.tracking_reserve > self.limit:
            raise ValueError("Tracking reserve must fit within the shared cap")
        return self


class OperatingPolicy(CollectionModel):
    """One non-refilling envelope shared across purposes and processes.

    A new scope is a new explicit grant, never an automatic reset/retry. Unused
    reservations are not refunded after crashes. Unsupported lanes fail closed.
    """

    scope_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    owner_reference: str = Field(min_length=1)
    permission_reference: str = Field(min_length=1)
    retention_reference: str = Field(min_length=1)
    starts_at: datetime
    stops_at: datetime
    recovery_spacing_seconds: int = Field(ge=0, strict=True)
    run_timeout_seconds: int = Field(gt=0, strict=True)
    caps: dict[Resource, ResourceCap]
    provider_request_caps: dict[str, ResourceCap] = Field(min_length=1)

    @model_validator(mode="after")
    def complete_envelope(self) -> "OperatingPolicy":
        if self.starts_at.tzinfo is None or self.stops_at.tzinfo is None:
            raise ValueError("Operating times must be timezone aware")
        if self.stops_at <= self.starts_at:
            raise ValueError("Finite operating stop must follow start")
        required = {
            "requests",
            "pages",
            "details",
            "retries",
            "fallbacks",
            "storage_bytes",
            "elapsed_seconds",
        }
        if not required.issubset(self.caps):
            raise ValueError(
                "Explicit request/page/detail/retry/fallback/storage/time caps required"
            )
        for value in (
            self.scope_id,
            self.version,
            self.owner_reference,
            self.permission_reference,
            self.retention_reference,
        ):
            if not value.strip():
                raise ValueError("Operating references cannot be blank")
        return self


class ResourceUsage(CollectionModel):
    resource: Resource
    used: int
    limit: int
    tracking_reserve: int


class CollectionAttempt(CollectionModel):
    id: str
    source: str
    purpose: Priority
    context_id: str
    query: str
    attempted_at: datetime
    state: Literal[
        "running",
        "success",
        "success_empty",
        "partial",
        "cache_reuse",
        "blocked",
        "capped",
        "failed",
        "interrupted",
    ]
    reason: str | None = None
    next_eligible_at: datetime | None = None
    last_good_at: datetime | None = None
    last_good_age_seconds: int | None = None
    evidence_state: Literal["unrefreshed", "observed_at_attempt"] = "unrefreshed"


class ProviderRequestUsage(CollectionModel):
    source: str
    used: int
    limit: int
    tracking_reserve: int


class CollectionStatus(CollectionModel):
    state: Literal["blocked", "supplied", "expired"]
    activation: Literal["staged"] = "staged"
    gates: list[str]
    scope_id: str | None = None
    version: str | None = None
    stops_at: datetime | None = None
    usage: list[ResourceUsage] = Field(default_factory=list)
    provider_usage: list[ProviderRequestUsage] = Field(default_factory=list)
    attempts: list[CollectionAttempt] = Field(default_factory=list)
