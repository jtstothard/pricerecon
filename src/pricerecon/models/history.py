"""Read projections of the retained capture ledger; no price-history copy."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from pricerecon.models.costs import CostScenario
from pricerecon.models.qualification import Configuration, MerchantOffer, SelectionBinding

HistoryChange = Literal["initial", "unchanged", "increased", "decreased", "not_comparable"]
HistoryValidity = Literal[
    "supported_at_capture", "unqualified", "invalidated", "legacy_unqualified"
]


class HistoryModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RevisionReference(HistoryModel):
    kind: Literal["configuration", "binding", "offer", "cost"]
    id: str = Field(min_length=1)
    revision: int = Field(gt=0)


class HistoryInvalidation(HistoryModel):
    """Append-only dependency withdrawal contract for the later correction owner.

    No correction HTTP write path. Exact revision references never reassign old
    observations to a newly corrected configuration.
    """

    id: str = Field(min_length=1)
    target: RevisionReference
    recorded_at: datetime
    reason: str = Field(min_length=1)
    correction_reference: str = Field(min_length=1)


class HistoryObservation(HistoryModel):
    id: str
    capture_id: str
    captured_at: datetime
    observed_at: datetime | None
    candidate_id: str
    source: str
    acquisition_state: Literal["success", "partial", "cache_reuse", "unknown"]
    offer: MerchantOffer
    binding: SelectionBinding
    configuration: Configuration
    costs: list[CostScenario]
    dependencies: list[RevisionReference]
    policy_versions: dict[str, str]
    lineage: list[str]
    duplicate_of: str | None = None
    change: HistoryChange
    validity: HistoryValidity
    invalidations: list[HistoryInvalidation] = Field(default_factory=list)
    reasons: list[str]
    evidence_kind: Literal["synthetic", "retained"]
    market_history_eligible: bool = False
    current_eligible: Literal[False] = False
    freshness: Literal["unvalidated"] = "unvalidated"


class HistoryGap(HistoryModel):
    kind: Literal["unobserved_interval", "open_interval", "source_outcome", "not_returned"]
    start: datetime
    end: datetime
    capture_id: str | None = None
    state: str | None = None
    reason: str


class HistoryAttempt(HistoryModel):
    capture_id: str
    captured_at: datetime
    source: str
    query: str
    state: Literal[
        "success",
        "success_empty",
        "partial",
        "cache_reuse",
        "blocked",
        "capped",
        "failed",
        "not_attempted",
    ]
    listing_count: int
    reason: str | None
    completeness: Literal["unknown", "partial", "declared_scope"]
    reused_capture_id: str | None = None


class LastGood(HistoryModel):
    observation_id: str
    captured_at: datetime
    observed_at: datetime
    age_seconds: float = Field(ge=0)
    freshness: Literal["unvalidated"] = "unvalidated"
    current_eligible: Literal[False] = False


class HistorySummary(HistoryModel):
    observation_count: int = 0
    last_good: LastGood | None = None
    validity: Literal["limited", "unavailable"] = "unavailable"
    reason: str = "Retained captures only; freshness and usual price are uncalibrated."


class UnavailableHistoryPrice(HistoryModel):
    state: Literal["unavailable"] = "unavailable"
    amount: None = None
    reason: str = "No accepted longitudinal sufficiency or baseline calibration."


class ObservationHistory(HistoryModel):
    candidate_id: str
    as_of: datetime
    history_state: Literal["limited", "unavailable"]
    observations: list[HistoryObservation]
    attempts: list[HistoryAttempt]
    gaps: list[HistoryGap]
    last_good: LastGood | None
    usual_price: UnavailableHistoryPrice = Field(default_factory=UnavailableHistoryPrice)
    savings: None = None
    legacy_events_included: Literal[False] = False
    coverage_reason: str = (
        "Only retained captures in the same source/query scope. Intervals between "
        "samples are unobserved, with no cadence, interpolation or continuous stock claim. "
        "Synthetic dates establish no real longitudinal history."
    )
