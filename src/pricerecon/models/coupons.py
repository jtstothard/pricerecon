"""Acquisition-only coupon evidence; no account, redemption or activation API."""

from datetime import datetime
from typing import Literal, Self

from pydantic import Field, model_validator

from pricerecon.models.costs import (
    Code,
    CostContext,
    CostEvidence,
    CostModel,
    CostScenario,
    CostScenarioInput,
    Money,
    Token,
)

Requirement = Literal["required", "not_required", "unknown"]


class CouponTerms(CostModel):
    literal: Token
    codes: list[Token] = Field(min_length=1, max_length=20)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    start_inclusive: bool | None = None
    end_inclusive: bool | None = None
    time_zone_literal: Token | None = None
    minimum_spend: Money | None = None
    minimum_currency: Code | None = None
    minimum_inclusive: bool | None = None
    minimum_basis: Token | None = None
    min_quantity: int | None = Field(default=None, gt=0, le=9007199254740991)
    max_quantity: int | None = Field(default=None, gt=0, le=9007199254740991)
    channel: Literal["web", "app", "any", "unknown"] = "unknown"
    new_customer: Requirement = "unknown"
    membership: Requirement = "unknown"
    redemption: Literal["public_no_activation", "conditional", "unknown"] = "unknown"
    compatibility: Literal["supported", "forbidden", "conditional", "unknown"] = "unknown"
    combination_rule: Token | None = None
    evidence: list[CostEvidence] = Field(default_factory=list, max_length=50)
    compatibility_evidence: list[CostEvidence] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def aware_times(self) -> Self:
        if any(t is not None and t.tzinfo is None for t in (self.starts_at, self.ends_at)):
            raise ValueError("Coupon validity needs timezone context")
        if self.starts_at and self.ends_at and self.starts_at > self.ends_at:
            raise ValueError("Coupon validity range reversed")
        if self.min_quantity and self.max_quantity and self.min_quantity > self.max_quantity:
            raise ValueError("Coupon quantity range reversed")
        if len(set(self.codes)) != len(self.codes):
            raise ValueError("Duplicate coupon code is not a stack")
        return self


class CouponEligibility(CostModel):
    channel: Literal["web", "app", "unknown"]
    new_customer: Requirement
    membership: Requirement
    eligible_base: Money
    currency: Code
    terms_satisfied: bool
    reason: Token
    eligible_members: list[Token] = Field(max_length=100)
    excluded_members: list[Token] = Field(max_length=100)
    evidence: list[CostEvidence] = Field(default_factory=list, max_length=50)


class CouponLine(CostModel):
    member: Token
    quantity: int = Field(gt=0, le=9007199254740991)
    before_item_total: Money
    after_item_total: Money
    currency: Code
    eligible: bool
    applied_codes: list[Token] = Field(max_length=20)
    evidence: list[CostEvidence] = Field(default_factory=list, max_length=50)


class CouponApplicationLineage(CostModel):
    terms_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_coupon_revision: int = Field(gt=0)
    expected_offer_revision: int = Field(gt=0)
    expected_binding_revision: int = Field(gt=0)
    expected_configuration_revision: int = Field(gt=0)
    expected_base_revision: int = Field(gt=0)
    expected_identity_policy: Token
    expected_selection_policy: Token
    expected_cost_policy: Token
    expected_coupon_policy: Token
    base_key: Token


class CheckoutObservation(CouponApplicationLineage):
    """Observed source values, separate from the proposed application/accounting.

    A collector must retain a direct before/after quote, not manufacture this
    record by relabelling terms, an eligibility claim, or a computed payable.
    Synthetic collectors must keep retention='synthetic' on the enclosing proof.
    """

    applied_codes: list[Token] = Field(min_length=1, max_length=20)
    other_promotions: list[Token] = Field(max_length=20)
    result: Literal["applied", "rejected", "unknown"]
    eligibility: CouponEligibility
    selected_member: Token
    selected_item_price: Money
    before_total: Money
    quoted_total: Money
    currency: Code
    before: CostScenarioInput
    after: CostScenarioInput
    lines: list[CouponLine] = Field(min_length=1, max_length=100)


class CheckoutReceipt(CostEvidence):
    role: Literal["checkout_application_receipt"]
    observation: CheckoutObservation


class CouponApplication(CouponApplicationLineage):
    before_total: Money
    applied_codes: list[Token] = Field(min_length=1, max_length=20)
    other_promotions: list[Token] = Field(max_length=20)
    selected_item_price: Money
    quoted_total: Money
    currency: Code
    result: Literal["applied", "rejected", "unknown"]
    evidence: list[CostEvidence] = Field(default_factory=list, max_length=50)
    payable: CostScenarioInput
    selected_member: Token
    lines: list[CouponLine] = Field(max_length=100)
    # Old/general evidence remains readable and retained, but cannot confer the
    # receipt role. A missing typed receipt withholds reproduction.
    receipt: CheckoutReceipt | None = None


class CouponInput(CostModel):
    key: Token
    label: Token
    category: Literal["public", "personal", "payment", "cashback"]
    context: CostContext
    opportunity_evidence: list[CostEvidence] = Field(default_factory=list, max_length=50)
    terms: CouponTerms | None = None
    eligibility: CouponEligibility | None = None
    application: CouponApplication | None = None


class CouponAssessment(CouponInput):
    id: str
    revision: int = 1
    offer_id: str
    offer_revision: int = 1
    binding_revision: int = 1
    configuration_revision: int = 1
    identity_policy_version: str = "watch-identity-v1"
    policy_version: str = "exact-coupon-v1"
    captured_at: datetime
    state: Literal[
        "unverified_opportunity",
        "conditional_eligibility",
        "applicable_not_reproduced",
        "reproduced_at_observation",
        "rejected",
        "invalidated",
    ] = "unverified_opportunity"
    issues: list[str] = Field(default_factory=list)
    applicability: Literal["unknown", "supported", "conditional", "rejected"] = "unknown"
    resulting_cost: CostScenario | None = None
    historical_resulting_cost: CostScenario | None = None
    source_conflicts: list[CouponInput] = Field(default_factory=list)
    lineage: Literal["observation_only", "superseded"] = "observation_only"


class CouponHistory(CostModel):
    offer_id: str
    assessments: list[CouponAssessment]
    coverage: Literal["supplied_acquisition_evidence_only"] = "supplied_acquisition_evidence_only"
    freshness: Literal["unvalidated"] = "unvalidated"
