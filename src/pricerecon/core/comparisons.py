"""Shared comparison cohorts and qualified payable claims; no estimator or acquisition."""

import json
from datetime import datetime

from pricerecon.core.exact_tracking import assess_offer, offer_key
from pricerecon.models.assessments import ComparablePath, ComparisonPolicy, PriceClaim
from pricerecon.models.discovery import DiscoveryCandidate, PreferenceProfile
from pricerecon.models.history import HistoryObservation


def cohort_for(observation: HistoryObservation) -> dict[str, str]:
    cost = next((c for c in observation.costs if c.kind == "public_no_coupon"), None)
    context = cost.context.model_dump(mode="json") if cost else {}
    # Selection and receipt identities remain exact dependencies. Different
    # merchants may compete for the same standalone configuration/commitment.
    for name in (
        "configuration_key",
        "merchant_key",
        "product_id",
        "variation_id",
        "seller",
        "basket_id",
        "consignment_id",
        "basket_members",
        "consignment_members",
    ):
        context.pop(name, None)
    return {
        "configuration": json.dumps(observation.configuration.values, sort_keys=True),
        "condition": observation.offer.condition or "unknown",
        "condition_description": observation.offer.condition_description or "",
        "quantity": str(observation.offer.quantity),
        "purchase_mode": observation.offer.purchase_mode or "unknown",
        "buyer_context": json.dumps(context, sort_keys=True),
        "eligibility": "ordinary_public_purchase",
    }


def assess_observation(
    observation: HistoryObservation,
    policy: ComparisonPolicy,
    at: datetime,
    *,
    require_history: bool = True,
) -> tuple[ComparablePath | None, list[str]]:
    offer, binding, config = observation.offer, observation.binding, observation.configuration
    candidate = DiscoveryCandidate(
        id=observation.candidate_id,
        source=observation.source,
        reported_source=observation.source,
        source_listing_id=offer.source_listing_id,
        title="Comparison input",
        query="",
        url=None,
        capture_id=observation.capture_id,
        captured_at=observation.captured_at,
        evidence=[],
        advertised_item_price=None,
        reported_currency=None,
        configurations=[config],
        bindings=[binding],
        offers=[offer],
    )
    checked = assess_offer(None, candidate, offer, binding, PreferenceProfile(), policy, at)
    reasons = []
    if observation.invalidations or (
        require_history
        and (observation.validity != "supported_at_capture" or observation.duplicate_of)
    ):
        reasons.extend(observation.reasons or ["retained_observation_unqualified"])
    if observation.acquisition_state != "success":
        reasons.append("acquisition_partial_or_reused")
    actual = {
        "identity": config.policy_version,
        "selection": binding.policy_version,
        "offer": offer.policy_version,
    }
    if (
        config.policy_version != policy.evidence_policies["identity"]
        or binding.policy_version != policy.evidence_policies["selection"]
        or offer.policy_version != policy.evidence_policies["offer"]
    ):
        reasons.append("evidence_policy_changed")
    cost = next((c for c in offer.cost_scenarios if c.id == checked.scenario_id), None)
    coupon = next((c for c in offer.coupons if c.id == checked.coupon_id), None)
    if coupon is not None:
        cost = coupon.resulting_cost
        actual["coupon"] = coupon.policy_version
        if coupon.policy_version != policy.evidence_policies["coupon"]:
            reasons.append("coupon_policy_changed")
    if cost is None or cost.policy_version != policy.evidence_policies["cost"]:
        reasons.append("cost_policy_changed_or_missing")
    if checked.state == "withheld":
        reasons.extend(checked.reasons)
    if reasons or cost is None or observation.observed_at is None or checked.delivered_gbp is None:
        return None, list(dict.fromkeys(reasons or ["observation_time_unavailable"]))
    return (
        ComparablePath(
            candidate_id=candidate.id,
            capture_id=candidate.capture_id,
            observation_id=observation.id,
            observed_at=observation.observed_at,
            amount=checked.delivered_gbp,
            scenario_kind=cost.kind,
            offer_key=offer_key(binding, offer),
            dependencies=observation.dependencies,
            policies={**actual, "cost": cost.policy_version},
            valid_until=checked.valid_until,
            evidence_ids=sorted(
                {e.id for e in offer.evidence}
                | {e.id for e in cost.context_evidence}
                | {e.id for part in cost.components for e in part.evidence}
                | (
                    {
                        e.id
                        for e in coupon.opportunity_evidence
                        + (
                            coupon.terms.evidence + coupon.terms.compatibility_evidence
                            if coupon.terms
                            else []
                        )
                        + (coupon.eligibility.evidence if coupon.eligibility else [])
                        + (coupon.application.evidence if coupon.application else [])
                    }
                    if coupon
                    else set()
                )
            ),
            synthetic=observation.evidence_kind == "synthetic",
            context=cost.context,
            coupon_id=checked.coupon_id,
            coupon_revision=checked.coupon_revision,
            coupon_fingerprint=checked.coupon_fingerprint,
        ),
        [],
    )


def claim(paths: list[ComparablePath], reason: str, *, require_live: bool = False) -> PriceClaim:
    """Claim the lowest payable among qualifying paths with visible provenance.

    `require_live=True` is the live-fact call-site contract: synthetic
    (fixture/offline-proof) paths are excluded before any amount is computed,
    and a fixture-only candidate set yields an explicit refusal instead of a
    number. The default keeps offline-verification claims available but marks
    them `synthetic` on the envelope so a caller can refuse them there too.

    Capability note: no production call site passes `require_live=True` yet.
    The production publishers (`db/assessments.evaluate_comparisons`, which
    serves `current_best`/`observed_low`) deliberately mark rather than
    filter, and market-history eligibility is enforced by its own exclusion
    in `db/history.get_history`. The flag exists for a future call site that
    must publish a live market fact; until one exists it is exercised only
    by tests.
    """
    if not paths:
        return PriceClaim(reason="No qualifying comparable observations in the disclosed scope.")
    if require_live:
        live = [p for p in paths if not p.synthetic]
        if not live:
            return PriceClaim(
                reason="Only synthetic fixture paths qualify; no live market fact is claimed."
            )
        paths = live
    amount = min(p.amount for p in paths)
    winners = [p for p in paths if p.amount == amount]
    return PriceClaim(
        state="supported",
        amount=amount,
        reason=reason,
        observation_count=len({p.observation_id for p in paths}),
        paths=winners,
        synthetic=any(p.synthetic for p in winners),
    )
