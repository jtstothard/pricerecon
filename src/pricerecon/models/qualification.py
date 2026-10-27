"""Capture-bound evidence and merchant contracts shared by category resolvers.

Only acquisition adapters supply these records; there is no qualification write API.
A typed record preserves a claim, it does not establish its truth or authority.
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Literal, Self
from urllib.parse import parse_qsl, urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pricerecon.models import NormalizedListing
from pricerecon.models.costs import CostScenario, CostScenarioInput
from pricerecon.models.coupons import CouponAssessment, CouponInput

IdentityField = Literal[
    "maker",
    "reference",
    "generation",
    "movement",
    "case_width_mm",
    "dial",
    "strap",
    "date_display",
    "product_kind",
]
OfferField = Literal[
    "seller",
    "condition",
    "condition_description",
    "quantity",
    "availability",
    "purchase_mode",
    "item_price",
    "currency",
    "destination",
    "visible_condition",
]


def safe_pointer(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        parts = urlsplit(value)
        if (
            parts.scheme in {"http", "https"}
            and parts.hostname
            and not (parts.username or parts.password)
        ):
            # Fail closed on credential-bearing links while retaining ordinary
            # selection queries (?variant=..., ?sku=...). Never fetch these URLs.
            sensitive = {
                "key",
                "apikey",
                "token",
                "accesstoken",
                "refreshtoken",
                "auth",
                "authorization",
                "password",
                "secret",
                "signature",
                "credential",
            }
            if any(
                "".join(ch for ch in key.casefold() if ch.isalnum()) in sensitive
                for key, _ in parse_qsl(parts.query)
            ):
                return None
            return parts._replace(fragment="").geturl()
    except ValueError:
        pass
    return None


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceContext(Contract):
    configuration_key: str | None = None
    scope: Literal["configuration", "selected_variation", "generic_listing"]
    merchant_key: str | None = None
    product_id: str | None = None
    variation_id: str | None = None
    destination: str | None = None
    currency: str | None = None
    quantity: int | None = Field(default=None, gt=0, le=9007199254740991)


class FieldEvidence(Contract):
    id: str = Field(min_length=1, max_length=250)
    subject: Literal["configuration", "selection", "offer"]
    field: IdentityField | OfferField
    value: str = Field(min_length=1, max_length=500)
    assertion_state: Literal["asserted", "unknown", "not_applicable"] = "asserted"
    issuer: str = Field(min_length=1, max_length=250)
    issuer_kind: Literal[
        "manufacturer",
        "seller",
        "visible_observation",
        "ai_inference",
        "search_lead",
        "human_correction",
    ]
    extractor: str = Field(min_length=1, max_length=250)
    extractor_kind: Literal["structured_data", "deterministic_dom", "ai", "human"]
    extractor_version: str | None = Field(default=None, max_length=100)
    extractor_model: str | None = Field(default=None, max_length=150)
    extraction_run_id: str | None = Field(default=None, max_length=250)
    uncertainty: str | None = Field(default=None, max_length=500)
    effective_at: datetime | None = None
    observed_at: datetime | None = None
    retrieved_at: datetime
    capture_id: str = Field(min_length=1, max_length=250)
    route: str = Field(min_length=1, max_length=250)
    pointer: str | None = None
    locator: str = Field(min_length=1, max_length=500)
    context: EvidenceContext
    derived_from: list[str] = Field(min_length=1, max_length=50)
    input_claim_ids: list[str] = Field(default_factory=list, max_length=50)
    permission_reference: str = Field(min_length=1, max_length=250)
    retention: Literal["minimal_fields", "synthetic"]

    @model_validator(mode="after")
    def validate_claim(self) -> Self:
        if any(
            stamp is not None and stamp.tzinfo is None
            for stamp in (self.retrieved_at, self.observed_at, self.effective_at)
        ):
            raise ValueError("Evidence times must carry timezone context")
        if not self.value.strip():
            raise ValueError("Empty evidence")
        if self.assertion_state != "asserted":
            return self
        if self.field in {"case_width_mm", "item_price", "quantity"}:
            try:
                number = Decimal(self.value)
            except InvalidOperation as exc:
                raise ValueError("Invalid numeric evidence") from exc
            # Representation bounds prevent adversarial exponents from
            # overflowing Decimal normalization or integer conversion. They
            # are input safety bounds, not a live collection/cost policy.
            if number.is_finite() and (
                abs(number.adjusted()) > 100 or number < Decimal("1e-100") and number != 0
            ):
                raise ValueError("Numeric evidence outside representation bounds")
            if self.field == "quantity" and number.is_finite() and number > 9007199254740991:
                raise ValueError("Quantity exceeds interoperable integer bounds")
            if (
                not number.is_finite()
                or number < 0
                or (self.field != "item_price" and number <= 0)
                or (self.field == "quantity" and number != number.to_integral_value())
            ):
                raise ValueError("Invalid numeric evidence")
        choices = {
            "product_kind": {"complete_watch", "accessory", "component"},
            "condition": {"new", "used", "refurbished"},
            "availability": {"in_stock", "out_of_stock"},
            "purchase_mode": {"buy_now", "auction", "best_offer"},
            "date_display": {"date", "no_date"},
        }
        if self.field in choices and self.value not in choices[self.field]:
            raise ValueError("Unsupported categorical evidence")
        if self.field in {"currency", "destination"} and (
            not self.value.isascii()
            or not self.value.isalpha()
            or not self.value.isupper()
            or len(self.value) != (3 if self.field == "currency" else 2)
        ):
            raise ValueError("Use explicit currency/country codes")
        if not self.value.strip():
            raise ValueError("Empty evidence")
        return self


class MerchantEvidenceReport(Contract):
    source_listing_id: str = Field(min_length=1, max_length=500)
    merchant_key: str | None = Field(default=None, min_length=1, max_length=250)
    product_id: str | None = Field(default=None, min_length=1, max_length=500)
    variation_id: str | None = Field(default=None, min_length=1, max_length=500)
    configuration_key: str | None = None
    destination: str | None = None
    currency: str | None = None
    quantity: int | None = Field(default=None, gt=0, le=9007199254740991)
    claims: list[FieldEvidence] = Field(default_factory=list, max_length=250)
    cost_scenarios: list[CostScenarioInput] = Field(default_factory=list, max_length=50)
    coupons: list[CouponInput] = Field(default_factory=list, max_length=50)


class EvidenceSearchReport(Contract):
    listings: list[NormalizedListing]
    evidence: list[MerchantEvidenceReport] = Field(default_factory=list)


class ResolutionIssue(Contract):
    field: str
    code: str
    evidence_ids: list[str] = Field(default_factory=list)


class Resolution(Contract):
    state: Literal["unresolved", "supported", "conflicting", "rejected"] = "unresolved"
    values: dict[str, str] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)
    issues: list[ResolutionIssue] = Field(default_factory=list)


class Configuration(Resolution):
    id: str = ""
    revision: int = 1
    policy_version: str = "watch-identity-v1"


class SelectionBinding(Contract):
    policy_version: str = "watch-selection-v1"
    id: str
    revision: int = 1
    configuration_id: str
    configuration_revision: int = 1
    merchant_key: str | None = None
    product_id: str | None = None
    variation_id: str | None = None
    resolution: Resolution = Field(default_factory=Resolution)


class MerchantOffer(Contract):
    id: str
    revision: int = 1
    binding_id: str
    binding_revision: int = 1
    source: str
    source_listing_id: str
    seller: str | None = None
    condition: str | None = None
    condition_description: str | None = None
    visible_condition: str | None = None
    quantity: int | None = None
    availability: str | None = None
    purchase_mode: str | None = None
    item_price: Decimal | None = None
    currency: str | None = None
    destination: str | None = None
    authenticity: Literal["unknown"] = "unknown"
    internal_health: Literal["unknown"] = "unknown"
    qualification: Resolution = Field(default_factory=Resolution)
    comparison: Resolution = Field(default_factory=Resolution)
    comparison_cohort: str | None = None
    policy_version: str = "offer-comparison-v1"
    evidence: list[FieldEvidence] = Field(default_factory=list)
    cost_scenarios: list[CostScenario] = Field(default_factory=list)
    coupons: list[CouponAssessment] = Field(default_factory=list)
