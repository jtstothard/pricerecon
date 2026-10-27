"""Shared evidence accounting, never a tax/entitlement or freshness engine."""

from datetime import datetime
from decimal import Decimal, localcontext

from pricerecon.core.qualification import identity_key
from pricerecon.models.costs import (
    CostAmount,
    CostEvidence,
    CostScenario,
    CostScenarioInput,
    PublicCostSummary,
)
from pricerecon.models.qualification import (
    MerchantEvidenceReport,
    MerchantOffer,
    SelectionBinding,
    safe_pointer,
)

REQUIRED = (
    "item",
    "shipping",
    "merchant_tax",
    "merchant_fee",
    "import_tax",
    "duty",
    "carrier_fee",
    "payment_fee",
)
MERCHANT = {"basket_other_items", "item", "shipping", "merchant_tax", "merchant_fee"}


def evidence_issue(evidence: CostEvidence, scenario: CostScenarioInput, at: datetime) -> str | None:
    if safe_pointer(evidence.pointer) is None:
        return "invalid_evidence_pointer"
    if evidence.context != scenario.context:
        return "cost_context_mismatch"
    if evidence.observed_at is None:
        return "observation_time_unknown"
    if evidence.observed_at > evidence.retrieved_at or evidence.retrieved_at > at:
        return "invalid_evidence_time"
    if evidence.effective_at is not None and evidence.effective_at > at:
        return "evidence_not_effective"
    if evidence.expires_at is not None and evidence.expires_at < at:
        return "evidence_expired_at_observation"
    if (
        evidence.extractor_kind in {"ai", "human"}
        or evidence.issuer_kind in {"ai_inference", "human_correction", "search_lead"}
        or evidence.input_claim_ids
    ):
        return "derived_claim_not_independent_support"
    return None


def evaluate_cost(
    scenario: CostScenarioInput,
    report: MerchantEvidenceReport,
    offer: MerchantOffer,
    binding: SelectionBinding,
    at: datetime,
) -> CostScenario:
    result = CostScenario(
        **scenario.model_dump(),
        id=identity_key(offer.id, scenario.key, scenario.kind, scenario.context.model_dump_json()),
        offer_id=offer.id,
        binding_id=binding.id,
        configuration_id=binding.configuration_id,
        captured_at=at,
    )
    issues = result.issues
    context = scenario.context
    if any(not value for value in context.model_dump().values()):
        issues.append("incomplete_cost_context")
    expected = (
        report.configuration_key,
        report.merchant_key,
        report.product_id,
        report.variation_id,
        offer.seller,
        offer.condition,
        offer.purchase_mode,
        offer.quantity,
        offer.destination,
        offer.currency,
    )
    actual = (
        context.configuration_key,
        context.merchant_key,
        context.product_id,
        context.variation_id,
        context.seller,
        context.condition,
        context.purchase_mode,
        context.quantity,
        context.destination_country,
        context.charge_currency,
    )
    if actual != expected:
        issues.append("offer_cost_context_mismatch")
    if offer.qualification.state != "supported" or binding.resolution.state != "supported":
        issues.append("exact_offer_not_supported")
    if offer.purchase_mode != "buy_now":
        issues.append("obtainable_fixed_price_missing")
    if context.destination_country != "GB" or context.destination_nation not in {
        "England",
        "Scotland",
        "Wales",
        "Northern Ireland",
    }:
        issues.append("uk_destination_unproven")
    if context.purchase_scope == "standalone" and (
        len(context.basket_members) != 1 or len(context.consignment_members) != 1
    ):
        issues.append("standalone_basket_mismatch")
    if context.purchase_scope == "allocated_share" and not scenario.assumptions:
        issues.append("basket_allocation_assumptions_missing")
    if not scenario.context_evidence:
        issues.append("context_evidence_missing")
    for evidence in result.context_evidence:
        reason = evidence_issue(evidence, scenario, at)
        if reason:
            issues.append(f"context:{reason}:{evidence.id}")
        evidence.pointer = safe_pointer(evidence.pointer)
    if scenario.kind != "public_no_coupon" and not scenario.assumptions:
        issues.append("eligibility_assumptions_missing")
    if scenario.kind == "public_no_coupon" and scenario.benefits:
        issues.append("public_scenario_contains_personal_benefit")
    conditional = (
        bool(scenario.assumptions)
        or scenario.kind != "public_no_coupon"
        or context.purchase_scope == "allocated_share"
    )
    with localcontext() as arithmetic:
        # Bounded input exponents/digits, quantity multiplication, FX and sums
        # need under 512 digits, including the smallest retained fractional term.
        arithmetic.prec = 512
        accepted = {}
        kinds = (
            (*REQUIRED, "basket_other_items")
            if context.purchase_scope == "whole_basket"
            or any(c.kind == "basket_other_items" for c in result.components)
            else REQUIRED
        )
        for kind in kinds:
            parts = [c for c in result.components if c.kind == kind]
            signatures = {c.model_dump_json(exclude={"evidence"}) for c in parts}
            if len(signatures) != 1:
                issues.append(
                    f"{kind}:conflicting_components" if parts else f"{kind}:missing_component"
                )
                continue
            component = parts[0]
            component_evidence = [e for c in parts for e in c.evidence]
            bad = [
                f"{kind}:{reason}:{e.id}"
                for e in component_evidence
                if (reason := evidence_issue(e, scenario, at))
            ]
            for e in component_evidence:
                e.pointer = safe_pointer(e.pointer)
            if bad or not component_evidence:
                issues.extend(bad or [f"{kind}:missing_evidence"])
                continue
            if kind == "basket_other_items" and context.purchase_scope != "whole_basket":
                issues.append("basket_other_items:scope_mismatch")
                continue
            if component.payer != "buyer":
                issues.append(f"{kind}:buyer_liability_unproven")
                continue
            if component.state in {"unknown", "conflicting"}:
                issues.append(f"{kind}:{component.state}")
                continue
            if component.state == "not_applicable":
                if (
                    kind == "item"
                    or component.amount is not None
                    or component.included_in is not None
                ):
                    issues.append(f"{kind}:invalid_inapplicability")
                    continue
                accepted[kind] = component
                continue
            if component.amount is None or component.currency is None:
                issues.append(f"{kind}:missing_amount_or_currency")
                continue
            if kind == "item" and component.included_in is not None:
                issues.append("item:invalid_inclusion")
                continue
            expected_item = offer.item_price
            if expected_item is not None and component.basis == "scenario":
                expected_item *= context.quantity or 1
            if kind == "item" and (
                component.currency != offer.currency or component.amount != expected_item
            ):
                issues.append("item:selected_price_mismatch")
                continue
            if component.state in {"derived", "conditional"} and not component.assumptions:
                issues.append(f"{kind}:assumptions_missing")
                continue
            conditional |= bool(component.assumptions) or component.state in {
                "derived",
                "conditional",
            }
            accepted[kind] = component
        for kind, component in accepted.items():
            if component.state == "not_applicable":
                continue
            amount = component.amount
            currency = component.currency
            assert amount is not None and currency is not None
            if component.basis == "per_unit":
                if context.quantity is None:
                    issues.append(f"{kind}:quantity_missing")
                    continue
                amount *= context.quantity
            if component.included_in is not None:
                parent = accepted.get(component.included_in)
                if (
                    parent is None
                    or parent.included_in is not None
                    or parent.amount is None
                    or parent.currency != currency
                    or component.included_in == kind
                ):
                    issues.append(f"{kind}:invalid_inclusion")
                elif amount > parent.amount * (
                    context.quantity or 1 if parent.basis == "per_unit" else 1
                ):
                    issues.append(f"{kind}:included_amount_exceeds_parent")
                continue
            bucket = result.merchant_payable if kind in MERCHANT else result.additional_liabilities
            bucket[currency] = bucket.get(currency, Decimal(0)) + amount
            result.known_subtotal[currency] = (
                result.known_subtotal.get(currency, Decimal(0)) + amount
            )
        converted = Decimal(0)
        funding = context.funding_currency
        for currency, amount in result.known_subtotal.items():
            if currency == funding:
                converted += amount
                continue
            quotes = [
                q
                for q in scenario.fx_quotes
                if q.purpose == "buyer_payment"
                and q.from_currency == currency
                and q.to_currency == funding
            ]
            # Quantum representations may differ while stating the same numeric
            # increment. Keep every quote/evidence record for validation below.
            quote_signatures = {
                (q.model_dump_json(exclude={"evidence", "quantum"}), q.quantum) for q in quotes
            }
            if len(quote_signatures) != 1:
                issues.append(
                    f"payment_fx_conflicting:{currency}:{funding}"
                    if quotes
                    else f"payment_fx_unknown:{currency}:{funding}"
                )
                continue
            quote = quotes[0]
            bad = [
                reason
                for q in quotes
                for e in q.evidence
                if (reason := evidence_issue(e, scenario, at))
            ]
            if (
                bad
                or not quote.evidence
                or quote.spread_included is None
                or quote.state in {"unknown", "conflicting"}
            ):
                issues.append(f"payment_fx_unproven:{currency}:{funding}")
                issues.extend(f"fx:{reason}" for reason in bad)
                continue
            if quote.state == "conditional" and not quote.assumptions:
                issues.append("fx:assumptions_missing")
                continue
            conditional |= quote.state == "conditional" or bool(quote.assumptions)
            # The validated quantum is a numeric power of ten. quantize uses
            # the operand's exponent, so discard coefficient trailing zeroes
            # exactly without normalizing (and rounding) the supplied evidence.
            quantum = Decimal((0, (1,), quote.quantum.adjusted()))
            converted += (amount * quote.rate).quantize(quantum, rounding=quote.rounding)
        if not result.known_subtotal or funding is None:
            issues.append("payable_currency_unresolved")
        if not issues and funding is not None:
            result.total = CostAmount(amount=converted, currency=funding)
            result.state = "conditional" if conditional else "verified_at_observation"
    # Sanitize even rejected/conflicting evidence; unsafe pointers are never
    # persisted or emitted. They are explanatory data, never fetched here.
    for evidence in (
        [e for component in result.components for e in component.evidence]
        + [e for quote in result.fx_quotes for e in quote.evidence]
        + [e for benefit in result.benefits for e in benefit.evidence]
    ):
        evidence.pointer = safe_pointer(evidence.pointer)
    return result


def public_summary(offers: list[MerchantOffer]) -> PublicCostSummary:
    scenarios = [
        c for offer in offers for c in offer.cost_scenarios if c.kind == "public_no_coupon"
    ]
    if len(scenarios) != 1:
        return PublicCostSummary(
            reason="Expand exact-offer scenarios; no single public scenario is selected."
        )
    cost = scenarios[0]
    if cost.context.purchase_scope != "standalone":
        return PublicCostSummary(
            scenario_id=cost.id,
            scenario_revision=cost.revision,
            reason="Expand basket cost scenarios; an allocated share or whole-basket total is not a standalone obtainable offer price.",
        )
    return PublicCostSummary(
        state=cost.state,
        amount=cost.total.amount if cost.total else None,
        currency=cost.total.currency if cost.total else None,
        scenario_id=cost.id,
        scenario_revision=cost.revision,
        reason="Cost at observation only; freshness and comparison acceptance remain unvalidated.",
    )


def evaluate_costs(
    report: MerchantEvidenceReport, offer: MerchantOffer, binding: SelectionBinding, at: datetime
) -> list[CostScenario]:
    # Same selected scenario: retain contradictory components, never first-report
    # wins or majority voting. Distinct contexts remain distinct buying scenarios.
    merged: dict[tuple[str, str, str], CostScenarioInput] = {}
    for scenario in report.cost_scenarios:
        key = (scenario.key, scenario.kind, scenario.context.model_dump_json())
        if key not in merged:
            merged[key] = scenario.model_copy(deep=True)
        else:
            retained = merged[key]
            for field in ("components", "context_evidence", "fx_quotes", "benefits"):
                values = getattr(retained, field)
                known = {value.model_dump_json() for value in values}
                values.extend(
                    value
                    for value in getattr(scenario, field)
                    if value.model_dump_json() not in known
                )
            retained.assumptions = list(dict.fromkeys(retained.assumptions + scenario.assumptions))
    return [evaluate_cost(scenario, report, offer, binding, at) for scenario in merged.values()]
