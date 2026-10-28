"""Staged category acquisition through the shared executor connector lifecycle."""

import hashlib
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import ValidationError

from pricerecon.categories.watches import resolve_watch
from pricerecon.core.acquisition import acquire_sources
from pricerecon.core.costs import evaluate_costs
from pricerecon.core.qualification import identity_key, qualify_offer
from pricerecon.db.discovery import save_capture
from pricerecon.models.assessments import ComparisonPolicy
from pricerecon.models.coupons import CouponAssessment
from pricerecon.models.discovery import (
    AcquisitionOutcome,
    DiscoveryAdmission,
    DiscoveryCandidate,
    DiscoveryCapture,
    DiscoveryOrigin,
    DiscoveryRequest,
    LeadEvidence,
)
from pricerecon.models.discovery_images import PermittedImage, RemoteReferenceImage
from pricerecon.models.qualification import MerchantEvidenceReport, safe_pointer
from pricerecon.models.tracking import TrackingPolicy


async def execute_discovery(
    request: DiscoveryRequest,
    *,
    admission: DiscoveryAdmission | None = None,
    tracking_policy: TrackingPolicy | None = None,
    comparison_policy: ComparisonPolicy | None = None,
) -> DiscoveryCapture:
    """Normal one-shot entry point, without scheduler or live activation paths.

    Offline verification must explicitly name its policy, permission and activation
    receipts. The default records a denied attempt without constructing connectors.
    An explicitly supplied tracking policy also evaluates exact delivered targets
    through the existing notification owner; HTTP intent writes cannot supply it.
    """
    admission = admission or DiscoveryAdmission()
    from pricerecon.core.collection_policy import current_policy
    from pricerecon.core.rate_limiter import AdmissionDenied

    policy_gate = None
    try:
        operating = current_policy()
    except AdmissionDenied as exc:
        operating, policy_gate = None, exc.reason

    if admission.admitted and operating is not None and tracking_policy is not None:
        from pricerecon.core.exact_tracking import deliver_pending_targets

        await deliver_pending_targets(policy=tracking_policy)
    from pricerecon.db.corrections import input_revision

    correction_input_revision = input_revision()
    capture_id = str(uuid4())
    captured_at = datetime.now(UTC)
    candidates: list[DiscoveryCandidate] = []
    by_id: dict[str, DiscoveryCandidate] = {}
    if admission.admitted and operating is not None:
        from pricerecon.db.collection import verification_sources

        result = await acquire_sources(
            request.sources,
            query=request.query,
            source_queries=request.source_queries,
            filters={},
            context_id=capture_id,
            purpose="discovery",
            verification_sources=verification_sources(request),
        )
        outcomes = result.outcomes
        for lead in result.leads:
            listing = lead.listing
            key = hashlib.sha256(
                f"{request.category}\0{lead.source}\0{listing.source_listing_id}".encode()
            ).hexdigest()
            # No normalized confidence, title, stock or total flag certifies any
            # watch dimension, offer binding, landed cost or image permission.
            url = safe_pointer(listing.url)
            price = listing.price
            if price is not None and (not price.is_finite() or price < 0):
                price = None
            fields: list[tuple[Literal["title", "advertised_item_price"], str]] = [
                ("title", listing.title_raw)
            ]
            if price is not None:
                fields.append(("advertised_item_price", str(price)))
            evidence = [
                LeadEvidence(
                    id=f"{capture_id}:{key}:{field}:{hashlib.sha256(value.encode()).hexdigest()}",
                    subject=key,
                    field=field,
                    value=value,
                    issuer=lead.source,
                    captured_at=captured_at,
                    source_observed_at=listing.timestamp_seen,
                    capture_id=capture_id,
                    pointer=url,
                    derived_from=[f"{capture_id}:{lead.source}:{listing.source_listing_id}"],
                )
                for field, value in fields
            ]
            candidate = DiscoveryCandidate(
                id=key,
                source=lead.source,
                reported_source=listing.source,
                source_listing_id=listing.source_listing_id,
                title=listing.title_raw,
                query=lead.query,
                url=url,
                capture_id=capture_id,
                captured_at=captured_at,
                evidence=evidence,
                advertised_item_price=price,
                reported_currency=listing.currency or None,
            )
            if listing.discovery_image is not None:
                try:
                    image = (
                        RemoteReferenceImage.model_validate(listing.discovery_image)
                        if listing.discovery_image.get("kind") == "remote_reference"
                        else PermittedImage.model_validate(listing.discovery_image)
                    )
                    if image.source_listing_id == listing.source_listing_id:
                        candidate.image = image
                except (ValidationError, ValueError):
                    pass  # Invalid depiction evidence never discards the buying lead.
            report = lead.evidence_report or MerchantEvidenceReport(
                source_listing_id=listing.source_listing_id
            )
            candidate.configuration, binding = resolve_watch(report, captured_at, key, lead.source)
            candidate.configurations = [candidate.configuration]
            candidate.identity_state = candidate.configuration.state
            candidate.bindings = [binding]
            candidate.offers = [qualify_offer(lead.source, report, binding, captured_at)]
            candidate.offers[0].cost_scenarios = evaluate_costs(
                report, candidate.offers[0], binding, captured_at
            )
            candidate.offers[0].coupons = [
                CouponAssessment(
                    **coupon.model_dump(),
                    id=identity_key(candidate.offers[0].id, coupon.key),
                    offer_id=candidate.offers[0].id,
                    captured_at=captured_at,
                    identity_policy_version=candidate.configuration.policy_version,
                )
                for coupon in report.coupons
            ]
            grouped_coupons: dict[str, CouponAssessment] = {}
            for coupon in candidate.offers[0].coupons:
                previous_coupon = grouped_coupons.get(coupon.id)
                if previous_coupon is None:
                    grouped_coupons[coupon.id] = coupon
                elif coupon.model_dump_json() != previous_coupon.model_dump_json():
                    from pricerecon.models.coupons import CouponInput

                    previous_coupon.source_conflicts.append(
                        CouponInput.model_validate(
                            coupon.model_dump(include=set(CouponInput.model_fields))
                        )
                    )
            candidate.offers[0].coupons = list(grouped_coupons.values())
            public_costs = [
                c for c in candidate.offers[0].cost_scenarios if c.kind == "public_no_coupon"
            ]
            if (
                len(public_costs) == 1
                and public_costs[0].state == "verified_at_observation"
                and public_costs[0].context.purchase_scope == "standalone"
            ):
                candidate.offers[0].comparison.issues = [
                    issue
                    for issue in candidate.offers[0].comparison.issues
                    if issue.code != "uk_cost_unknown"
                ]
            if (
                len(public_costs) == 1
                and public_costs[0].state == "conditional"
                and public_costs[0].context.purchase_scope == "standalone"
            ):
                for issue in candidate.offers[0].comparison.issues:
                    if issue.code == "uk_cost_unknown":
                        issue.code = "uk_cost_conditional"
            candidate.missing_data = list(
                dict.fromkeys(
                    f"{issue.field}: {issue.code}"
                    for resolution in (
                        candidate.configuration,
                        binding.resolution,
                        candidate.offers[0].qualification,
                        candidate.offers[0].comparison,
                    )
                    for issue in resolution.issues
                )
            )
            previous = by_id.get(key)
            if previous is None:
                by_id[key] = candidate
                candidates.append(candidate)
            else:
                for configuration in candidate.configurations:
                    if configuration.id not in {c.id for c in previous.configurations}:
                        previous.configurations.append(configuration)
                for binding in candidate.bindings:
                    if binding.id not in {b.id for b in previous.bindings}:
                        previous.bindings.append(binding)
                for offer in candidate.offers:
                    if offer.id not in {o.id for o in previous.offers}:
                        previous.offers.append(offer)
                previous.missing_data = list(
                    dict.fromkeys(previous.missing_data + candidate.missing_data)
                )
                # Duplicated extraction within one capture is not independent
                # confirmation. Retain differing claims without resolving them.
                known_claims = {(claim.field, claim.value) for claim in previous.evidence}
                extra_claims = [
                    claim for claim in evidence if (claim.field, claim.value) not in known_claims
                ]
                if extra_claims:
                    previous.evidence.extend(extra_claims)
                    if (
                        "conflicting connector reports for the same listing"
                        not in previous.missing_data
                    ):
                        previous.missing_data.append(
                            "conflicting connector reports for the same listing"
                        )
    else:
        outcomes = [
            AcquisitionOutcome(
                source=source.connector,
                state="blocked" if admission.admitted and source.enabled else "not_attempted",
                reason=("source_disabled" if not source.enabled else
                        (policy_gate or "operating_policy_required") if admission.admitted else "collection_staged"),
            )
            for source in request.sources
        ]
    for candidate in candidates:
        states = {config.state for config in candidate.configurations}
        candidate.identity_state = (
            "conflicting"
            if "conflicting" in states
            else "supported"
            if states == {"supported"}
            else "rejected"
            if states == {"rejected"}
            else "unresolved"
        )
    capture = DiscoveryCapture(
        correction_input_revision=correction_input_revision,
        history_contract_version="observation-history-v1",
        capture_id=capture_id,
        captured_at=captured_at,
        request=DiscoveryOrigin(
            category=request.category,
            query=request.query,
            source_queries=request.source_queries,
            sources=[source.connector for source in request.sources],
        ),
        admission=admission,
        outcomes=outcomes,
    )
    from pricerecon.core.rate_limiter import AdmissionDenied

    try:
        save_capture(capture, candidates)
    except AdmissionDenied as exc:
        from pricerecon.db.collection import reject_capture

        for outcome in capture.outcomes:
            if outcome.state in {"success", "success_empty", "partial", "cache_reuse"}:
                outcome.state = exc.state
                outcome.reason = exc.reason
        reject_capture(capture.capture_id, exc.reason, exc.state)
        # No unaccounted fallback write. The existing attempt receipt supplies
        # capped coverage; the rolled-back evidence never reaches the feed.
        return capture
    from pricerecon.core.exact_tracking import evaluate_tracking_capture

    try:
        from pricerecon.db.assessments import evaluate_comparisons

        evaluate_comparisons(
            comparison_policy if admission.admitted and operating is not None else None,
            datetime.now(UTC),
        )
        await evaluate_tracking_capture(capture.capture_id,
            policy=tracking_policy if admission.admitted and operating is not None else None)
    except AdmissionDenied as exc:
        from pricerecon.db.collection import reject_capture

        reject_capture(capture.capture_id, exc.reason, exc.state)
        for outcome in capture.outcomes:
            if outcome.state in {"success", "success_empty"}:
                outcome.state, outcome.reason = exc.state, exc.reason
    return capture
