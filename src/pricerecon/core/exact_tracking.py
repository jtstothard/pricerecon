"""Qualified delivered-target decisions at the normal acquisition execution seam.

No scheduler or collection activation. Price state is offer/buyer-scenario based,
not capture/route based. Withheld observations never reset a crossing or a low.
"""

import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from pricerecon.categories.watches import configuration_matches_values, configuration_preference_fit
from pricerecon.core import notifications
from pricerecon.core.qualification import identity_key
from pricerecon.db.discovery import get_preferences, load_capture_candidates
from pricerecon.db.schema import DB_PATH
from pricerecon.db.tracking import evidence_revision_withdrawn, store, target_delivery_valid
from pricerecon.models import EventType
from pricerecon.models.discovery import DiscoveryCandidate, DiscoveryCapture, PreferenceProfile
from pricerecon.models.qualification import MerchantOffer, SelectionBinding
from pricerecon.models.tracking import (
    ExactTracking,
    OfferTargetState,
    TargetEvent,
    TrackingAssessment,
    TrackingPolicy,
)


def assess_offer(
    intent: ExactTracking,
    candidate: DiscoveryCandidate,
    offer: MerchantOffer,
    binding: SelectionBinding,
    preferences: PreferenceProfile,
    policy: TrackingPolicy | None,
    now: datetime,
) -> TrackingAssessment:
    result = TrackingAssessment(
        assessed_at=now,
        capture_id=candidate.capture_id,
        intent_revision=intent.revision,
        preference_revision=preferences.revision,
        offer_id=offer.id,
        offer_revision=offer.revision,
        binding_revision=binding.revision,
        configuration_id=binding.configuration_id,
        configuration_revision=binding.configuration_revision,
        policy_version=policy.version if policy else None,
        policy_fingerprint=identity_key(policy.model_dump_json()) if policy else None,
    )
    reasons = []
    configuration = next(
        (c for c in candidate.configurations if c.id == binding.configuration_id), None
    )
    if policy is None:
        reasons.append("policy_required")
    if intent.invalidation_reason:
        reasons.append("evidence_invalidated")
    if (
        configuration is None
        or configuration.state != "supported"
        or (
            not configuration_matches_values(configuration.values, intent.intended_values)
            if intent.intended_values is not None
            else binding.configuration_id != intent.configuration_id
        )
    ):
        reasons.append("exact_configuration_unresolved_or_changed")
    if binding.resolution.state != "supported" or offer.qualification.state != "supported":
        reasons.append("selected_offer_unqualified")
    if offer.purchase_mode != "buy_now" or offer.availability != "in_stock":
        reasons.append("offer_unavailable_or_not_buy_now")
    costs = [
        c
        for c in offer.cost_scenarios
        if c.kind == "public_no_coupon" and c.context.purchase_scope == "standalone"
    ]
    if len(costs) != 1:
        reasons.append("public_delivered_scenario_unresolved")
        result.reasons = reasons
        return result
    cost = costs[0]
    result.scenario_id, result.scenario_revision = cost.id, cost.revision
    if (
        cost.state != "verified_at_observation"
        or cost.total is None
        or cost.total.currency != "GBP"
    ):
        reasons.append("public_delivered_total_unverified")
    if (
        cost.offer_id,
        cost.offer_revision,
        cost.binding_id,
        cost.binding_revision,
        cost.configuration_id,
        cost.configuration_revision,
    ) != (
        offer.id,
        offer.revision,
        binding.id,
        binding.revision,
        binding.configuration_id,
        binding.configuration_revision,
    ):
        reasons.append("evidence_revision_mismatch")
    if offer.destination != "GB" or cost.context.destination_country != "GB":
        reasons.append("uk_destination_unproven")
    if policy is not None:
        result.policy_version = policy.version
        if (
            offer.condition not in policy.allowed_conditions
            or offer.quantity != policy.quantity
            or cost.context.quantity != policy.quantity
            or cost.context.destination_nation != policy.destination_nation
            or cost.context.destination_region != policy.destination_region
            or cost.context.payment_method != policy.payment_method
        ):
            reasons.append("buyer_eligibility_mismatch")
        if offer.condition in {"used", "refurbished"} and not offer.condition_description:
            reasons.append("condition_details_missing")
        # Every supporting input needs observation time. Retrieval/health alone
        # cannot renew semantic freshness. Rejected claims cannot repair it.
        cost_evidence = cost.context_evidence + [e for c in cost.components for e in c.evidence]
        cost_evidence += [e for fx in cost.fx_quotes for e in fx.evidence]
        required_ids = set(
            (configuration.evidence_ids if configuration else [])
            + binding.resolution.evidence_ids
            + offer.qualification.evidence_ids
        )
        field_evidence = [e for e in offer.evidence if e.id in required_ids]
        evidence = field_evidence + cost_evidence
        if not evidence or not required_ids.issubset({e.id for e in field_evidence}):
            reasons.append("supporting_evidence_missing")
        expiry = [candidate.captured_at + timedelta(seconds=policy.max_evidence_age_seconds)]
        for claim in evidence:
            stamp = claim.observed_at
            if stamp is None or stamp > now or claim.retrieved_at > now:
                reasons.append("evidence_time_unknown_or_future")
                continue
            expiry.append(stamp + timedelta(seconds=policy.max_evidence_age_seconds))
            if claim.effective_at is not None and claim.effective_at > now:
                reasons.append("evidence_not_effective")
        for claim in cost_evidence:
            if claim.expires_at is not None:
                expiry.append(claim.expires_at)
        result.valid_until = min(expiry)
        if result.valid_until <= now:
            reasons.append("evidence_stale_or_expired")
    fits = configuration_preference_fit(
        preferences.values, [configuration] if configuration else []
    )
    if any(f.strength != "unset" and f.field != "budget" and f.state != "fits" for f in fits):
        reasons.append("preference_mismatch_or_unknown")
    if (
        cost.total is not None
        and preferences.values.budget_gbp is not None
        and (cost.total.currency != "GBP" or cost.total.amount > preferences.values.budget_gbp)
    ):
        reasons.append("preference_mismatch_or_unknown")
    if reasons:
        result.reasons = list(dict.fromkeys(reasons))
        return result
    if cost.total is None:
        return result
    result.delivered_gbp = cost.total.amount
    result.state = "eligible" if cost.total.amount <= intent.target_gbp else "above_target"
    result.reasons = ["qualifying_observation" if result.state == "eligible" else "above_target"]
    return result


def offer_key(binding: SelectionBinding, offer: MerchantOffer) -> str:
    # Merchant selection and buyer context identify the opportunity across
    # acquisition routes. Capture/source IDs and text prices aren't identities.
    cost = next(
        c
        for c in offer.cost_scenarios
        if c.kind == "public_no_coupon" and c.context.purchase_scope == "standalone"
    )
    context = cost.context
    return identity_key(
        binding.merchant_key or "",
        binding.product_id or "",
        binding.variation_id or "",
        offer.seller or "",
        offer.condition or "",
        offer.condition_description or "",
        str(offer.quantity),
        "GB",
        context.destination_nation or "",
        context.destination_region or "",
        context.payment_method or "",
        context.shipping_service or "",
        context.charge_currency or "",
    )


def evidence_time(offer: MerchantOffer) -> datetime:
    stamps = [e.observed_at for e in offer.evidence if e.observed_at is not None]
    for cost in offer.cost_scenarios:
        if cost.kind == "public_no_coupon":
            stamps.extend(e.observed_at for e in cost.context_evidence if e.observed_at is not None)
            stamps.extend(
                e.observed_at
                for c in cost.components
                for e in c.evidence
                if e.observed_at is not None
            )
    return min(stamps)


def decide(
    connection: sqlite3.Connection,
    intent: ExactTracking,
    candidate: DiscoveryCandidate,
    offer: MerchantOffer,
    binding: SelectionBinding,
    assessment: TrackingAssessment,
) -> None:
    price = assessment.delivered_gbp
    if price is None or assessment.policy_version is None or assessment.policy_fingerprint is None:
        return
    key = offer_key(binding, offer)
    row = connection.execute(
        "SELECT payload_json FROM exact_tracking_prices WHERE tracking_id=? AND offer_key=?",
        (intent.id, key),
    ).fetchone()
    previous = OfferTargetState.model_validate_json(row[0]) if row else None
    stamp = evidence_time(offer)
    state = OfferTargetState(
        intent_revision=intent.revision,
        policy_version=assessment.policy_version,
        policy_fingerprint=assessment.policy_fingerprint,
        previous_gbp=price,
        notified_low_gbp=price,
        evidence_at=stamp,
    )
    trigger = None
    if previous is None or (previous.intent_revision, previous.policy_fingerprint) != (
        intent.revision,
        assessment.policy_fingerprint,
    ):
        assessment.reasons = ["above_target" if price > intent.target_gbp else "baseline_recorded"]
        if previous is not None:
            state.crossing_epoch = previous.crossing_epoch
    elif stamp <= previous.evidence_at:
        assessment.reasons = ["duplicate_or_older_evidence"]
        return
    else:
        state = previous.model_copy(update={"previous_gbp": price, "evidence_at": stamp})
        if price > intent.target_gbp:
            state.notified_low_gbp = price
            assessment.reasons = ["above_target"]
        elif previous.previous_gbp > intent.target_gbp:
            state.crossing_epoch += 1
            trigger = "target_crossing"
        elif price < previous.notified_low_gbp:
            trigger = "further_drop"
        else:
            assessment.reasons = ["duplicate_offer_price"]
    if trigger:
        state.notified_low_gbp = price
        assessment.reasons = [trigger]
        listing: dict[str, str | int | None] = {
            "tracking_id": intent.id,
            "title_raw": candidate.title,
            "configuration_id": binding.configuration_id,
            "offer_id": offer.id,
            "offer_key": key,
            "delivered_gbp": str(price),
            "target_gbp": str(intent.target_gbp),
            "reason": trigger,
            "observed_at": stamp.isoformat(),
            "url": candidate.url,
        }
        cursor = connection.execute(
            "INSERT INTO events(watch_id,event_type,listing_key,severity,event_json) "
            "VALUES (NULL,?,?,'notice',?)",
            (EventType.EXACT_TARGET_CROSSING.value, key, json.dumps(listing)),
        )
        if cursor.lastrowid is None:
            raise RuntimeError("Target event insert has no ID")
        event = TargetEvent(
            event_id=cursor.lastrowid,
            tracking_id=intent.id,
            intent_revision=intent.revision,
            invalidation_revision=intent.invalidation_revision,
            offer_key=key,
            delivered_gbp=price,
            reason=trigger,
            status="pending",
            channels={},
            assessment=assessment,
            listing=listing,
            notification_channels=intent.notifications.channels,
        )
        connection.execute(
            "INSERT INTO exact_tracking_events VALUES (?,?,?)",
            (event.event_id, intent.id, event.model_dump_json()),
        )
    connection.execute(
        "INSERT INTO exact_tracking_prices VALUES (?,?,?) ON CONFLICT(tracking_id,offer_key) "
        "DO UPDATE SET payload_json=excluded.payload_json",
        (intent.id, key, state.model_dump_json()),
    )


async def evaluate_tracking_capture(capture_id: str, *, policy: TrackingPolicy | None) -> None:
    now = datetime.now(UTC)
    with closing(sqlite3.connect(DB_PATH)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        from pricerecon.core.collection_policy import current_policy
        from pricerecon.db.collection import storage_size

        operating = current_policy()
        before_bytes = storage_size(connection) if operating else 0
        candidates = load_capture_candidates(connection, capture_id)
        capture = DiscoveryCapture.model_validate_json(
            connection.execute(
                "SELECT payload_json FROM discovery_captures WHERE capture_id=?",
                (capture_id,),
            ).fetchone()[0]
        )
        preferences = get_preferences()
        intents = [
            ExactTracking.model_validate_json(r[0])
            for r in connection.execute("SELECT payload_json FROM exact_tracking ORDER BY id")
        ]
        for intent in intents:
            assessments = []
            evaluated = []
            for candidate in candidates:
                for offer in candidate.offers:
                    binding = next(b for b in candidate.bindings if b.id == offer.binding_id)
                    if (
                        binding.configuration_id != intent.configuration_id
                        and candidate.id != intent.candidate_id
                    ):
                        continue
                    assessment = assess_offer(
                        intent, candidate, offer, binding, preferences, policy, now
                    )
                    outcomes = [o for o in capture.outcomes if o.source == candidate.source]
                    if not outcomes or not all(
                        o.state == "success"
                        and o.completeness != "partial"
                        and o.reused_capture_id is None
                        for o in outcomes
                    ):
                        assessment.state = "withheld"
                        assessment.reasons = ["acquisition_partial_or_reused"]
                    if evidence_revision_withdrawn(connection, intent, assessment):
                        assessment.state = "withheld"
                        assessment.reasons = ["evidence_revision_withdrawn"]
                    evaluated.append((candidate, offer, binding, assessment))
                    assessments.append(assessment)
            totals: dict[str, set[Decimal | None]] = {}
            for _, offer, binding, assessment in evaluated:
                if assessment.state != "withheld":
                    totals.setdefault(offer_key(binding, offer), set()).add(
                        assessment.delivered_gbp
                    )
            for candidate, offer, binding, assessment in evaluated:
                if assessment.state != "withheld":
                    if len(totals[offer_key(binding, offer)]) > 1:
                        assessment.state = "withheld"
                        assessment.reasons = ["conflicting_route_totals"]
                    else:
                        decide(connection, intent, candidate, offer, binding, assessment)
            intent.assessment = (
                min(
                    assessments,
                    key=lambda a: (
                        {"eligible": 0, "above_target": 1, "withheld": 2}[a.state],
                        a.delivered_gbp if a.delivered_gbp is not None else 0,
                    ),
                )
                if assessments
                else TrackingAssessment(
                    assessed_at=now,
                    intent_revision=intent.revision,
                    reasons=["source_evidence_unavailable"],
                )
            )
            store(connection, intent)
        if operating:
            from pricerecon.core.rate_limiter import DurableAdmission

            DurableAdmission(operating, "sqlite", "verification", capture_id).debit(
                {"storage_bytes": max(0, storage_size(connection) - before_bytes)},
                connection=connection,
            )
    await deliver_pending_targets(policy=policy)


async def deliver_pending_targets(*, policy: TrackingPolicy | None) -> None:
    """Recover pre-send reservations after restart, revalidating every input.

    Claimed channels are never automatically retried, including failed sends:
    false/exception may mean the external recipient accepted but its ACK was lost.
    """
    from pricerecon.core.collection_policy import current_policy

    operating = current_policy()
    if (policy is None or operating is None
        or not operating.starts_at <= datetime.now(UTC) < operating.stops_at):
        return
    with closing(sqlite3.connect(DB_PATH)) as connection:
        events = [
            TargetEvent.model_validate_json(r[0])
            for r in connection.execute(
                "SELECT payload_json FROM exact_tracking_events ORDER BY event_id"
            )
        ]
    for event in events:
        if event.status != "pending":
            continue
        with closing(sqlite3.connect(DB_PATH)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            intent = ExactTracking.model_validate_json(
                connection.execute(
                    "SELECT payload_json FROM exact_tracking WHERE id=?",
                    (event.tracking_id,),
                ).fetchone()[0]
            )
            preferences = get_preferences()
            valid = (
                intent.revision == event.intent_revision
                and intent.invalidation_revision == event.invalidation_revision
                and intent.invalidation_reason is None
                and event.assessment.policy_version == policy.version
                and event.assessment.policy_fingerprint == identity_key(policy.model_dump_json())
                and event.assessment.preference_revision == preferences.revision
                and event.assessment.valid_until is not None
                and event.assessment.valid_until > datetime.now(UTC)
            )
            # A later offer capture invalidates a pending assessment. Recovery
            # does not silently transfer its price to new evidence.
            revision = connection.execute(
                "SELECT MAX(revision) FROM discovery_offers WHERE id=?",
                (event.assessment.offer_id,),
            ).fetchone()[0]
            valid = valid and revision == event.assessment.offer_revision
            from pricerecon.db.collection import refresh_unavailable

            valid = valid and not refresh_unavailable(connection, intent.candidate_id,
                                                     event.assessment.assessed_at)
            valid = valid and target_delivery_valid(connection, event.event_id)
            if not valid:
                event.status = "withheld"
                connection.execute(
                    "UPDATE exact_tracking_events SET payload_json=? WHERE event_id=?",
                    (event.model_dump_json(), event.event_id),
                )
                continue
        if event.notification_channels:
            await notifications.dispatch_notifications(
                watch_id=None,
                event_id=event.event_id,
                event_type=EventType.EXACT_TARGET_CROSSING,
                watch_name=str(event.listing["title_raw"]),
                watch_notifications={
                    "events": [EventType.EXACT_TARGET_CROSSING.value],
                    "channels": event.notification_channels,
                },
                listing=dict(event.listing),
                global_config=notifications.get_global_notification_config(),
                durable_key=f"exact-target:{event.event_id}",
            )
        # This acknowledgement describes local attempts, not exactly-once delivery.
        with closing(sqlite3.connect(DB_PATH)) as connection, connection:
            event.status = "attempted" if event.notification_channels else "channels_unset"
            connection.execute(
                "UPDATE exact_tracking_events SET payload_json=? WHERE event_id=?",
                (event.model_dump_json(), event.event_id),
            )
