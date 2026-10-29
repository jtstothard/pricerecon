"""Versioned, scoped claims; calibration is deliberately unavailable."""

from datetime import datetime
from decimal import Decimal
from typing import Literal, Self

from pydantic import Field, model_validator

from pricerecon.models.costs import CostContext
from pricerecon.models.history import HistoryAttempt, HistoryGap, RevisionReference
from pricerecon.models.tracking import TrackingModel, TrackingPolicy


class ComparisonPolicy(TrackingPolicy):
    window_start: datetime
    window_end: datetime
    sources: list[str] = Field(min_length=1)
    evidence_policies: dict[Literal["identity", "selection", "offer", "cost", "coupon"], str]

    @model_validator(mode="after")
    def explicit_window(self) -> Self:
        if (
            self.window_start.tzinfo is None
            or self.window_end.tzinfo is None
            or self.window_start > self.window_end
        ):
            raise ValueError("Supply an ordered, timezone-aware retained-observation window")
        if set(self.evidence_policies) != {"identity", "selection", "offer", "cost", "coupon"}:
            raise ValueError("Supply every evidence policy version")
        return self


class ComparablePath(TrackingModel):
    candidate_id: str
    capture_id: str
    observation_id: str
    observed_at: datetime
    amount: Decimal
    scenario_kind: str
    offer_key: str
    dependencies: list[RevisionReference]
    policies: dict[str, str]
    valid_until: datetime | None
    evidence_ids: list[str]
    synthetic: bool
    context: CostContext
    coupon_id: str | None = None
    coupon_revision: int | None = None
    coupon_fingerprint: str | None = None


class PriceClaim(TrackingModel):
    state: Literal["supported", "unavailable", "historical", "invalidated"] = "unavailable"
    amount: Decimal | None = None
    currency: Literal["GBP"] = "GBP"
    reason: str
    observation_count: int = 0
    paths: list[ComparablePath] = Field(default_factory=list)
    # Envelope-level provenance: true when the claimed amount is decided by at
    # least one synthetic (fixture/offline-proof) path. Offline proof must never
    # be presented as a live market fact, and this marker is the API contract
    # that lets a consumer refuse it without reading per-path entries.
    synthetic: bool = False


class AssessmentCoverage(TrackingModel):
    sources: list[str]
    unchecked_sources: list[str]
    capture_ids: list[str]
    gaps: list[HistoryGap]
    attempts: list[HistoryAttempt] = Field(default_factory=list)
    reason: str = (
        "Lowest among qualified offers checked in this scope only. Intervals are unobserved; "
        "no continuous availability, complete market or all-time claim."
    )


class PathExclusion(TrackingModel):
    observation_id: str
    candidate_id: str
    reasons: list[str]
    scope: Literal["current", "history"]


class PriceAssessment(TrackingModel):
    id: str
    revision: int
    candidate_ids: list[str]
    assessed_at: datetime
    window_start: datetime
    window_end: datetime
    historical: bool = False
    invalidation_reasons: list[str] = Field(default_factory=list)
    cohort: dict[str, str]
    policy: ComparisonPolicy
    policy_fingerprint: str
    method: Literal["qualified-payable-minimum-v1"] = "qualified-payable-minimum-v1"
    current_best: PriceClaim
    observed_low: PriceClaim
    usual_price: PriceClaim = Field(
        default_factory=lambda: PriceClaim(
            reason="Usual obtainable price unavailable: no accepted empirical calibration."
        )
    )
    personal_price: PriceClaim = Field(
        default_factory=lambda: PriceClaim(
            reason="Personal eligibility and comparable personal history unsupported."
        )
    )
    savings: None = None
    coverage: AssessmentCoverage
    exclusions: list[PathExclusion]
    dependencies: list[RevisionReference] = Field(default_factory=list)
    input_captures: dict[str, str] = Field(default_factory=dict)


class AssessmentList(TrackingModel):
    items: list[PriceAssessment]
    reason: str = "Explicit comparison policy required; no production calibration is assumed."
