"""Coupon evidence assessment. Never collect, redeem, or invent discount arithmetic."""

import hashlib

from pricerecon.core.costs import basket_allocation_issues, evaluate_cost, evidence_issue
from pricerecon.core.qualification import identity_key
from pricerecon.models.costs import CostEvidence, CostScenarioInput
from pricerecon.models.coupons import CouponAssessment
from pricerecon.models.qualification import (
    MerchantEvidenceReport,
    MerchantOffer,
    SelectionBinding,
    safe_pointer,
)


def check_evidence(coupon: CouponAssessment, evidence: list[CostEvidence], label: str) -> None:
    scenario = CostScenarioInput(key=coupon.key, kind="public_no_coupon", context=coupon.context)
    if not evidence:
        coupon.issues.append(f"{label}:missing_evidence")
    for claim in evidence:
        reason = evidence_issue(claim, scenario, coupon.captured_at)
        # Coupon expiry is conservative at the instant unless terms explicitly
        # establish inclusivity. General evidence validity uses its own boundary.
        if reason:
            coupon.issues.append(f"{label}:{reason}")
        claim.pointer = safe_pointer(claim.pointer)


def assess_coupon(
    coupon: CouponAssessment, offer: MerchantOffer, binding: SelectionBinding
) -> CouponAssessment:
    coupon.issues = []
    if offer.qualification.state != "supported" or binding.resolution.state != "supported":
        coupon.issues.append("exact_offer_not_supported")
    if not any(cost.context == coupon.context for cost in offer.cost_scenarios):
        coupon.issues.append("exact_cost_context_missing")
    check_evidence(coupon, coupon.opportunity_evidence, "opportunity")
    terms, eligibility = coupon.terms, coupon.eligibility
    if terms is None:
        coupon.issues.append("terms_missing")
        return coupon
    check_evidence(coupon, terms.evidence, "terms")
    check_evidence(coupon, terms.compatibility_evidence, "compatibility")
    if terms.compatibility != "supported" or not terms.combination_rule:
        coupon.issues.append(f"stack_{terms.compatibility}")
    if any(
        v is None
        for v in (
            terms.starts_at,
            terms.ends_at,
            terms.start_inclusive,
            terms.end_inclusive,
            terms.time_zone_literal,
        )
    ):
        coupon.issues.append("validity_unknown")
    else:
        at = coupon.captured_at
        if terms.starts_at is not None and (
            at < terms.starts_at or (at == terms.starts_at and not terms.start_inclusive)
        ):
            coupon.issues.append("not_started")
        if terms.ends_at is not None and (
            at > terms.ends_at or (at == terms.ends_at and not terms.end_inclusive)
        ):
            coupon.issues.append("expired")
    if any(
        v is None
        for v in (
            terms.minimum_spend,
            terms.minimum_currency,
            terms.minimum_inclusive,
            terms.minimum_basis,
            terms.min_quantity,
            terms.max_quantity,
        )
    ):
        coupon.issues.append("spend_or_quantity_terms_unknown")
    quantity = coupon.context.quantity
    if (
        quantity is None
        or (terms.min_quantity is not None and quantity < terms.min_quantity)
        or (terms.max_quantity is not None and quantity > terms.max_quantity)
    ):
        coupon.issues.append("quantity_ineligible")
    if eligibility is None:
        coupon.issues.append("eligibility_unknown")
    else:
        check_evidence(coupon, eligibility.evidence, "eligibility")
        members = eligibility.eligible_members + eligibility.excluded_members
        if len(set(members)) != len(members) or sorted(members) != sorted(
            coupon.context.basket_members
        ):
            coupon.issues.append("basket_eligibility_incomplete")
        if not eligibility.terms_satisfied:
            coupon.issues.append("eligibility_rejected")
        if (
            terms.channel == "unknown"
            or eligibility.channel == "unknown"
            or (terms.channel != "any" and terms.channel != eligibility.channel)
        ):
            coupon.issues.append("channel_ineligible_or_unknown")
        for field in ("new_customer", "membership"):
            requirement = getattr(terms, field)
            if requirement == "unknown" or getattr(eligibility, field) != requirement:
                coupon.issues.append(f"{field}_ineligible_or_unknown")
        if eligibility.currency != terms.minimum_currency:
            coupon.issues.append("minimum_currency_mismatch")
        if terms.minimum_spend is not None and (
            eligibility.eligible_base < terms.minimum_spend
            or (eligibility.eligible_base == terms.minimum_spend and not terms.minimum_inclusive)
        ):
            coupon.issues.append("minimum_spend_not_met")
    if terms.redemption != "public_no_activation":
        coupon.issues.append("redemption_conditional_or_unknown")
    conditional = (
        coupon.category != "public"
        or terms.new_customer == "required"
        or terms.membership == "required"
    )
    rejected = {
        "expired",
        "not_started",
        "quantity_ineligible",
        "eligibility_rejected",
        "minimum_spend_not_met",
        "stack_forbidden",
    }
    if rejected.intersection(coupon.issues):
        coupon.state, coupon.applicability = "rejected", "rejected"
    elif conditional:
        coupon.state, coupon.applicability = "conditional_eligibility", "conditional"
        coupon.issues.append("separate_conditional_benefit")
    elif not coupon.issues:
        coupon.state, coupon.applicability = "applicable_not_reproduced", "supported"
    return coupon


def assess_application(
    coupon: CouponAssessment, offer: MerchantOffer, binding: SelectionBinding
) -> None:
    """Called after acquisition assigns revisions, inside the same transaction."""
    application = coupon.application
    if coupon.source_conflicts:
        coupon.state = "invalidated"
        coupon.issues.append("conflicting_coupon_inputs")
    if application is None:
        return
    check_evidence(coupon, application.evidence, "application")
    terms = coupon.terms
    if terms is None:
        return
    actual = (coupon.revision, offer.revision, binding.revision, binding.configuration_revision)
    expected = (
        application.expected_coupon_revision,
        application.expected_offer_revision,
        application.expected_binding_revision,
        application.expected_configuration_revision,
    )
    if (
        actual != expected
        or application.terms_fingerprint
        != hashlib.sha256(terms.model_dump_json().encode()).hexdigest()
    ):
        coupon.issues.append("application_lineage_changed")
        coupon.state = "invalidated"
    if application.applied_codes != terms.codes or application.other_promotions:
        coupon.issues.append("whole_stack_not_proven")
    if application.result != "applied":
        coupon.issues.append(f"application_{application.result}")
    payable = application.payable
    if payable.context != coupon.context or payable.kind != "public_no_coupon" or payable.benefits:
        coupon.issues.append("application_context_or_benefit_mismatch")
    bases = [
        c
        for c in offer.cost_scenarios
        if c.key == application.base_key
        and c.kind == "public_no_coupon"
        and c.context == coupon.context
    ]
    if len(bases) != 1:
        coupon.issues.append("exact_no_coupon_base_missing_or_ambiguous")
    else:
        base = bases[0]
        policies = (
            coupon.identity_policy_version,
            binding.policy_version,
            base.policy_version,
            coupon.policy_version,
        )
        expected_policies = (
            application.expected_identity_policy,
            application.expected_selection_policy,
            application.expected_cost_policy,
            application.expected_coupon_policy,
        )
        if policies != expected_policies:
            coupon.issues.append("application_policy_changed")
            coupon.state = "invalidated"
        coupon.issues.extend(basket_allocation_issues(application, base))
        if (
            base.state != "verified_at_observation"
            or base.total is None
            or base.total.amount != application.before_total
            or base.total.currency != application.currency
            or base.revision != application.expected_base_revision
        ):
            coupon.issues.append("no_coupon_base_changed_or_unverified")
    # Receipt support must be distinct from banners/terms, and every resulting
    # component/FX/context must belong to this exact receipt, including explicit
    # inapplicability. A success toast or bare discount cannot pass this gate.
    roots = {root for e in application.evidence for root in e.derived_from}
    term_roots = {
        root for e in terms.evidence + coupon.opportunity_evidence for root in e.derived_from
    }
    if roots.intersection(term_roots):
        coupon.issues.append("advertisement_is_not_application_receipt")
    claims = (
        payable.context_evidence
        + [e for c in payable.components for e in c.evidence]
        + [e for fx in payable.fx_quotes for e in fx.evidence]
        + [e for line in application.lines for e in line.evidence]
    )
    check_evidence(coupon, claims, "payable")
    for line in application.lines:
        check_evidence(coupon, line.evidence, "line")
        eligible = (
            coupon.eligibility is not None and line.member in coupon.eligibility.eligible_members
        )
        if (
            (line.after_item_total != line.before_item_total and not line.applied_codes)
            or line.eligible != eligible
            or (
                line.applied_codes
                and (
                    not line.eligible
                    or any(code not in application.applied_codes for code in line.applied_codes)
                )
            )
        ):
            coupon.issues.append("line_eligibility_or_codes_mismatch")
    if not roots or not claims or any(not set(e.derived_from).issubset(roots) for e in claims):
        coupon.issues.append("payable_not_bound_to_application_receipt")
    if coupon.state != "applicable_not_reproduced" or coupon.issues:
        return
    context = coupon.context
    report = MerchantEvidenceReport(
        source_listing_id=offer.source_listing_id,
        configuration_key=context.configuration_key,
        merchant_key=context.merchant_key,
        product_id=context.product_id,
        variation_id=context.variation_id,
    )
    result = evaluate_cost(
        payable,
        report,
        offer,
        binding,
        coupon.captured_at,
        reproduced_item_price=application.selected_item_price,
    )
    if result.state != "verified_at_observation" or result.total is None:
        coupon.issues.extend(["reproduced_payable_unverified", *result.issues])
        return
    if (
        result.total.amount != application.quoted_total
        or result.total.currency != application.currency
    ):
        coupon.issues.append("quoted_payable_does_not_reconcile")
        return
    result.kind = "public_coupon"
    result.id = identity_key("coupon-payable", coupon.id, result.id)
    result.revision = coupon.revision
    result.offer_revision = offer.revision
    result.binding_revision = binding.revision
    result.configuration_revision = binding.configuration_revision
    coupon.resulting_cost = result
    coupon.state = "reproduced_at_observation"
