"""Discovery feed contracts. Legacy normalized output remains lead-only."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from pricerecon.models.corrections import CorrectionHistory
from pricerecon.models.costs import PublicCostSummary
from pricerecon.models.history import HistorySummary
from pricerecon.models.qualification import Configuration, MerchantOffer, SelectionBinding
from pricerecon.models.source_evidence import SourceReceipt
from pricerecon.models.tracking import ExactTracking
from pricerecon.models.watches import SourceConfig


class DiscoveryModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AcquisitionOutcome(DiscoveryModel):
    source_evidence: SourceReceipt | None = None
    source: str
    route: Literal["connector_search_v1"] = "connector_search_v1"
    state: Literal[
        "success", "success_empty", "partial", "cache_reuse", "blocked", "capped", "failed", "not_attempted"
    ]
    listing_count: int = 0
    reason: str | None = None
    completeness: Literal["unknown", "partial", "declared_scope"] = "unknown"
    reused_capture_id: str | None = None


class DiscoveryRequest(DiscoveryModel):
    category: Literal["watches"] = "watches"
    query: str = Field(min_length=1, max_length=500)
    sources: list[SourceConfig] = Field(min_length=1)
    source_queries: dict[str, str] = Field(default_factory=dict)


class SourceCoverage(DiscoveryModel):
    family: Literal[
        "aliexpress",
        "ebay_secondhand",
        "brand_direct",
        "uk_retail",
        "uk_shipping_international",
        "search_aggregator_community",
    ]
    source: str
    route: str
    accepted_status: Literal["reviewed_lead", "blocked", "unqualified", "unsupported"]
    activation: Literal["staged"] = "staged"
    reason: str
    prerequisites: list[str]
    decision_reference: str = "docs/product/category-discovery/source-qualification-decision.md"
    last_outcome: AcquisitionOutcome | None = None


class DiscoveryAdmission(DiscoveryModel):
    """Staged programmatic execution only; never exposed as an activation API."""

    mode: Literal["staged", "offline_verification"] = "staged"
    policy_reference: str | None = Field(default=None, min_length=1)
    permission_reference: str | None = Field(default=None, min_length=1)
    activation_reference: str | None = Field(default=None, min_length=1)

    @property
    def admitted(self) -> bool:
        return self.mode == "offline_verification" and all(
            value and value.strip()
            for value in (
                self.policy_reference,
                self.permission_reference,
                self.activation_reference,
            )
        )


class DiscoveryOrigin(DiscoveryModel):
    """Acquisition context without connector config or credentials."""

    category: Literal["watches"] = "watches"
    query: str
    sources: list[str]
    source_queries: dict[str, str]


class DiscoveryCapture(DiscoveryModel):
    correction_input_revision: int = 0
    publication_state: Literal["accepted", "withdrawn"] = "accepted"
    history_contract_version: Literal["observation-history-v1"] | None = None
    capture_id: str
    captured_at: datetime
    request: DiscoveryOrigin
    admission: DiscoveryAdmission
    outcomes: list[AcquisitionOutcome]


class LeadEvidence(DiscoveryModel):
    id: str
    subject: str
    field: Literal["title", "advertised_item_price"]
    value: str
    issuer: str
    issuer_kind: Literal["connector_report"] = "connector_report"
    extractor: Literal["normalized_lead_v1"] = "normalized_lead_v1"
    captured_at: datetime
    source_observed_at: datetime | None
    capture_id: str
    route: Literal["connector_search_v1"] = "connector_search_v1"
    pointer: str | None
    validity_context: Literal[
        "search lead; exact selection, identity and payable cost unverified"
    ] = "search lead; exact selection, identity and payable cost unverified"
    derived_from: list[str]


class PlaceholderImage(DiscoveryModel):
    kind: Literal["original_placeholder"] = "original_placeholder"
    attribution: str = "PriceRecon original SVG illustration"
    provenance: str = (
        "Original generic artwork; not a product photograph or evidence of dial colour."
    )
    permission: Literal["original_artwork"] = "original_artwork"


class UnavailableUsualPrice(DiscoveryModel):
    state: Literal["unavailable"] = "unavailable"
    amount: None = None
    reason: str = "No qualified history or accepted baseline calibration."


class WatchPreferences(DiscoveryModel):
    compact_max_width_mm: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    compact_strength: Literal["hard", "soft"] = "hard"
    colourful_dials: list[str] = Field(default_factory=list, max_length=20)
    colourful_strength: Literal["hard", "soft"] = "soft"
    budget_gbp: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    budget_strength: Literal["hard", "soft"] = "hard"

    @field_validator("colourful_dials")
    @classmethod
    def clean_colours(cls, colours: list[str]) -> list[str]:
        cleaned = list(dict.fromkeys(colour.strip().casefold() for colour in colours))
        if any(not colour or len(colour) > 60 for colour in cleaned):
            raise ValueError("Enter non-empty dial colours of at most 60 characters.")
        return cleaned


class PreferenceInterpretation(DiscoveryModel):
    field: Literal["compact", "colourful", "budget"]
    strength: Literal["hard", "soft", "unset"]
    meaning: str


class PreferenceProfile(DiscoveryModel):
    category: Literal["watches"] = "watches"
    revision: int = 0
    updated_at: datetime | None = None
    values: WatchPreferences = Field(default_factory=WatchPreferences)
    interpretation: list[PreferenceInterpretation] = Field(default_factory=list)


class PreferenceUpdate(DiscoveryModel):
    expected_revision: int = Field(ge=0)
    values: WatchPreferences


class PreferenceFit(DiscoveryModel):
    field: Literal["compact", "colourful", "budget"]
    strength: Literal["hard", "soft", "unset"]
    state: Literal["unknown", "unset", "fits", "outside"]
    reason: str


class DiscoveryCandidate(DiscoveryModel):
    corrections: list[CorrectionHistory] = Field(default_factory=list)
    history: HistorySummary = Field(default_factory=HistorySummary)
    id: str
    category: Literal["watches"] = "watches"
    origin: Literal["category_discovery"] = "category_discovery"
    source: str
    reported_source: str
    source_listing_id: str
    title: str
    query: str
    url: str | None
    capture_id: str
    captured_at: datetime
    evidence: list[LeadEvidence]
    image: PlaceholderImage = Field(default_factory=PlaceholderImage)
    advertised_item_price: Decimal | None
    reported_currency: str | None
    price_caveat: str = (
        "Connector-reported item price only; may describe another variation or a normalized default."
    )
    identity_state: Literal["unresolved", "supported", "conflicting", "rejected"] = "unresolved"
    configuration: Configuration = Field(default_factory=Configuration)
    configurations: list[Configuration] = Field(default_factory=list)
    bindings: list[SelectionBinding] = Field(default_factory=list)
    offers: list[MerchantOffer] = Field(default_factory=list)
    missing_data: list[str] = Field(
        default_factory=lambda: [
            "exact reference and generation",
            "movement",
            "case width",
            "dial colour",
            "strap",
            "complete watch or accessory",
            "selected merchant variation",
            "condition and purchase mode",
            "availability and quantity",
            "UK shipping, taxes and other payable costs",
        ]
    )
    public_delivered_total: PublicCostSummary = Field(default_factory=PublicCostSummary)
    usual_price: UnavailableUsualPrice = Field(default_factory=UnavailableUsualPrice)
    savings: None = None
    alert_eligible: Literal[False] = False
    preference_fit: list[PreferenceFit] = Field(default_factory=list)


class DiscoveryFeed(DiscoveryModel):
    source_coverage: list[SourceCoverage] = Field(default_factory=list)
    cohort_gaps: list[str] = Field(
        default_factory=lambda: [
            "Militado ML05/ML05B: real manufacturer/store identity, selection and UK offer evidence unresolved.",
            "Merkur Lightning salmon: no reconciled exact reference/offer; missing evidence remains an abstention.",
        ]
    )
    category: Literal["watches"] = "watches"
    collection_state: Literal["staged"] = "staged"
    collection_reason: str = (
        "Live collection awaits explicit source policy, permissions and activation."
    )
    candidates: list[DiscoveryCandidate]
    captures: list[DiscoveryCapture]
    preferences: PreferenceProfile = Field(default_factory=PreferenceProfile)
    tracking: list[ExactTracking] = Field(default_factory=list)
