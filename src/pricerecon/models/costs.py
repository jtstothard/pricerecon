"""Category-independent, exact-scenario cost evidence. No legal rates or defaults.

Input bounds protect decimal representation and payload size, not operating policy.
Destination is a region token, never an address; payment is a method token, never
an account/card identifier. Source authority/retention remain separate live gates.
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)
from pydantic_core import PydanticCustomError


def precise_number(value: object) -> Decimal:
    if not isinstance(value, (str, Decimal, int)) or isinstance(value, bool):
        raise PydanticCustomError("exact_decimal", "Use an exact decimal string, not a float")
    if isinstance(value, str) and len(value) > 220:
        raise ValueError("Cost string outside representation bounds")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("Invalid decimal cost") from exc
    if not number.is_finite() or number < 0 or (number and abs(number.adjusted()) > 100):
        raise ValueError("Invalid nonnegative finite cost")
    exponent = number.as_tuple().exponent
    if not isinstance(exponent, int) or len(number.as_tuple().digits) > 100 or abs(exponent) > 100:
        raise ValueError("Cost outside representation bounds")
    return number.copy_abs() if number.is_zero() else number


Money = Annotated[Decimal, BeforeValidator(precise_number)]
Code = Annotated[str, Field(pattern=r"^[A-Z]{3}$", max_length=3)]
Token = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
Kind = Literal[
    "basket_other_items",
    "item",
    "shipping",
    "merchant_tax",
    "merchant_fee",
    "import_tax",
    "duty",
    "carrier_fee",
    "payment_fee",
]


class CostModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CostContext(CostModel):
    configuration_key: Token | None = None
    merchant_key: Token | None = None
    product_id: Token | None = None
    variation_id: Token | None = None
    seller: Token | None = None
    condition: Token | None = None
    purchase_mode: Token | None = None
    quantity: int | None = Field(default=None, gt=0, le=9007199254740991)
    destination_country: Annotated[str, Field(pattern=r"^[A-Z]{2}$")] | None = None
    destination_nation: Token | None = None
    destination_region: Token | None = None
    shipping_service: Token | None = None
    seller_establishment: Token | None = None
    goods_location: Token | None = None
    dispatch_country: Token | None = None
    customs_origin: Token | None = None
    dispatch_route: Token | None = None
    purchase_scope: Literal["standalone", "allocated_share", "whole_basket"] | None = None
    basket_id: Token | None = None
    basket_members: list[Token] = Field(default_factory=list, max_length=100)
    consignment_id: Token | None = None
    consignment_members: list[Token] = Field(default_factory=list, max_length=100)
    grouping_basis: Token | None = None
    payment_method: Token | None = None
    display_currency: Code | None = None
    charge_currency: Code | None = None
    funding_currency: Code | None = None


class CostEvidence(CostModel):
    id: Token
    issuer: Token
    issuer_kind: Literal[
        "seller",
        "carrier",
        "payment_provider",
        "customs",
        "ai_inference",
        "human_correction",
        "search_lead",
    ]
    extractor: Token
    extractor_kind: Literal["structured_data", "deterministic_dom", "ai", "human"]
    observed_at: datetime | None = None
    retrieved_at: datetime
    effective_at: datetime | None = None
    expires_at: datetime | None = None
    capture_id: Token
    acquisition_capture_id: Token | None = None
    route: Token
    pointer: str | None = Field(default=None, max_length=2000)
    locator: Token
    derived_from: list[Token] = Field(min_length=1, max_length=50)
    input_claim_ids: list[Token] = Field(default_factory=list, max_length=50)
    permission_reference: Token
    retention: Literal["minimal_fields", "synthetic"]
    context: CostContext

    @model_validator(mode="after")
    def aware_times(self) -> Self:
        if any(
            t is not None and t.tzinfo is None
            for t in (self.observed_at, self.retrieved_at, self.effective_at, self.expires_at)
        ):
            raise ValueError("Cost evidence times need timezone context")
        return self


class CostComponent(CostModel):
    kind: Kind
    state: Literal["observed", "derived", "conditional", "unknown", "conflicting", "not_applicable"]
    amount: Money | None = None
    currency: Code | None = None
    basis: Literal["per_unit", "scenario"]
    included_in: Kind | None
    payer: Token
    collector: Token
    reason: Token
    assumptions: list[Token] = Field(default_factory=list, max_length=50)
    evidence: list[CostEvidence] = Field(default_factory=list, max_length=50)


class FxQuote(CostModel):
    purpose: Literal["buyer_payment", "customs_valuation"]
    from_currency: Code
    to_currency: Code
    rate: Annotated[Money, Field(gt=0)]
    direction: Literal["target_per_source"]
    converter: Token
    spread_included: bool | None = None
    quantum: Annotated[Money, Field(gt=0)]
    rounding: Literal["ROUND_HALF_UP", "ROUND_HALF_EVEN", "ROUND_DOWN", "ROUND_UP"]
    state: Literal["observed", "conditional", "unknown", "conflicting"]
    assumptions: list[Token] = Field(default_factory=list, max_length=50)
    evidence: list[CostEvidence] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def decimal_quantum(self) -> Self:
        digits = self.quantum.as_tuple().digits
        # Decimal.normalize uses ambient precision and can round a near-power
        # into a power. Inspect the exact coefficient instead.
        if digits[0] != 1 or any(digit != 0 for digit in digits[1:]):
            raise ValueError("Rounding quantum must be an explicit decimal power")
        return self


class ConditionalBenefit(CostModel):
    kind: Literal["personal", "payment", "cashback"]
    amount: Money | None = None
    currency: Code | None = None
    state: Literal["conditional", "unknown", "conflicting"]
    reason: Token
    evidence: list[CostEvidence] = Field(default_factory=list, max_length=50)
    accounting: Literal["excluded_from_payable"] = "excluded_from_payable"


class CostScenarioInput(CostModel):
    key: Token
    kind: Literal["public_no_coupon", "personal", "payment", "cashback"]
    context: CostContext
    context_evidence: list[CostEvidence] = Field(default_factory=list, max_length=50)
    fx_quotes: list[FxQuote] = Field(default_factory=list, max_length=50)
    components: list[CostComponent] = Field(default_factory=list, max_length=100)
    benefits: list[ConditionalBenefit] = Field(default_factory=list, max_length=50)
    assumptions: list[Token] = Field(default_factory=list, max_length=50)


class CostAmount(CostModel):
    # Computed output may have more digits than any individual bounded input.
    amount: Decimal = Field(ge=0, allow_inf_nan=False)
    currency: Code


class CostScenario(CostScenarioInput):
    # Output is the union of separately bounded source records. Do not discard
    # contradictions or apply a per-record input cap to aggregated evidence.
    components: list[CostComponent] = Field(default_factory=list)
    context_evidence: list[CostEvidence] = Field(default_factory=list)
    fx_quotes: list[FxQuote] = Field(default_factory=list)
    benefits: list[ConditionalBenefit] = Field(default_factory=list)
    assumptions: list[Token] = Field(default_factory=list)
    id: str
    revision: int = 1
    policy_version: str = "exact-scenario-cost-v1"
    offer_id: str
    offer_revision: int = 1
    binding_id: str
    binding_revision: int = 1
    configuration_id: str
    configuration_revision: int = 1
    captured_at: datetime
    state: Literal["verified_at_observation", "conditional", "unknown"] = "unknown"
    total: CostAmount | None = None
    known_subtotal: dict[str, Decimal] = Field(default_factory=dict)
    merchant_payable: dict[str, Decimal] = Field(default_factory=dict)
    additional_liabilities: dict[str, Decimal] = Field(default_factory=dict)
    issues: list[str] = Field(default_factory=list)
    freshness: Literal["unvalidated"] = "unvalidated"


class PublicCostSummary(CostModel):
    state: Literal["verified_at_observation", "conditional", "unknown"] = "unknown"
    amount: Decimal | None = None
    currency: str | None = None
    scenario_id: str | None = None
    scenario_revision: int | None = None
    reason: str = "Exact configuration, merchant selection and UK payable components need checking."


class CostHistory(CostModel):
    offer_id: str
    scenarios: list[CostScenario]
    freshness: Literal["unvalidated"] = "unvalidated"
