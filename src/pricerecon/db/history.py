"""History is a projection of existing immutable captures and exact revisions."""

import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from itertools import pairwise

from pricerecon.db.schema import DB_PATH
from pricerecon.models.discovery import DiscoveryCandidate, DiscoveryCapture
from pricerecon.models.history import (
    HistoryAttempt,
    HistoryChange,
    HistoryGap,
    HistoryInvalidation,
    HistoryObservation,
    HistoryValidity,
    LastGood,
    ObservationHistory,
    RevisionReference,
)
from pricerecon.models.qualification import MerchantOffer


def init_history_tables(connection: sqlite3.Connection) -> None:
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS discovery_history_invalidations (
            id TEXT PRIMARY KEY,
            target_kind TEXT NOT NULL CHECK(target_kind IN ('configuration','binding','offer','cost')),
            target_id TEXT NOT NULL, target_revision INTEGER NOT NULL CHECK(target_revision > 0),
            payload_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_history_invalidation_target
            ON discovery_history_invalidations(target_kind, target_id, target_revision);
        INSERT OR IGNORE INTO schema_migrations(version, description)
            VALUES ('1.7', 'Project retained observation history with exact revision invalidation references');
    """)


def append_history_invalidation(
    connection: sqlite3.Connection, invalidation: HistoryInvalidation
) -> None:
    """Caller owns the correction transaction; an ID cannot overwrite a withdrawal."""
    connection.execute(
        "INSERT INTO discovery_history_invalidations VALUES (?, ?, ?, ?, ?)",
        (
            invalidation.id,
            invalidation.target.kind,
            invalidation.target.id,
            invalidation.target.revision,
            invalidation.model_dump_json(),
        ),
    )


def get_history(
    candidate_id: str,
    *,
    as_of: datetime | None = None,
    connection: sqlite3.Connection | None = None,
) -> ObservationHistory | None:
    if connection is None:
        with closing(sqlite3.connect(DB_PATH)) as opened, opened:
            opened.execute("BEGIN")
            return get_history(candidate_id, as_of=as_of, connection=opened)
    from pricerecon.db.discovery import hydrate_candidate

    now = as_of or datetime.now(UTC)
    candidates = [
        DiscoveryCandidate.model_validate_json(row[0])
        for row in connection.execute(
            "SELECT payload_json FROM discovery_leads WHERE candidate_id = ? ORDER BY rowid",
            (candidate_id,),
        )
    ]
    if not candidates:
        return None
    captures = [
        DiscoveryCapture.model_validate_json(row[0])
        for row in connection.execute(
            "SELECT payload_json FROM discovery_captures WHERE category = 'watches' ORDER BY rowid"
        )
    ]
    by_capture = {c.capture_id: c for c in captures}
    observations: list[HistoryObservation] = []
    # Cross-route copies of the same selected merchant capture retain one
    # owner even when they arrive as different discovery candidates.
    lineage_owners: dict[tuple[str, str | None, str | None, str | None], str] = {}
    for row in connection.execute(
        "SELECT capture_id, payload_json FROM discovery_offers ORDER BY rowid"
    ):
        retained = MerchantOffer.model_validate_json(row[1])
        for claim in retained.evidence:
            if claim.subject != "offer" or claim.field not in {"item_price", "availability"}:
                continue
            key = (
                claim.capture_id,
                claim.context.merchant_key,
                claim.context.product_id,
                claim.context.variation_id,
            )
            lineage_owners.setdefault(key, f"{row[0]}:{retained.id}:{retained.revision}")
    previous: dict[str, HistoryObservation] = {}
    for candidate in candidates:
        hydrate_candidate(connection, candidate)
        capture = by_capture[candidate.capture_id]
        outcomes = [o for o in capture.outcomes if o.source == candidate.source]
        state = outcomes[0].state if len(outcomes) == 1 else "unknown"
        for offer in candidate.offers:
            binding = next(
                (
                    b
                    for b in candidate.bindings
                    if (b.id, b.revision) == (offer.binding_id, offer.binding_revision)
                ),
                None,
            )
            if binding is None:
                continue
            configuration = next(
                (
                    c
                    for c in candidate.configurations
                    if (c.id, c.revision)
                    == (binding.configuration_id, binding.configuration_revision)
                ),
                None,
            )
            if configuration is None:
                continue
            dependencies = [
                RevisionReference(kind="offer", id=offer.id, revision=offer.revision),
                RevisionReference(kind="binding", id=binding.id, revision=binding.revision),
                RevisionReference(
                    kind="configuration", id=configuration.id, revision=configuration.revision
                ),
            ]
            dependencies.extend(
                RevisionReference(kind="cost", id=c.id, revision=c.revision)
                for c in offer.cost_scenarios
            )
            invalidations: list[HistoryInvalidation] = []
            for ref in dependencies:
                invalidations.extend(
                    HistoryInvalidation.model_validate_json(row[0])
                    for row in connection.execute(
                        "SELECT payload_json FROM discovery_history_invalidations WHERE target_kind = ? AND target_id = ? AND target_revision = ? ORDER BY rowid",
                        (ref.kind, ref.id, ref.revision),
                    )
                )
            claims = [c for c in offer.evidence if c.subject != "configuration"]
            cost_claims = [
                e
                for c in offer.cost_scenarios
                for e in c.context_evidence + [e for part in c.components for e in part.evidence]
            ]
            lineage = sorted(
                {value for c in claims + cost_claims for value in [c.capture_id, *c.derived_from]}
            )
            observation_id = f"{capture.capture_id}:{offer.id}:{offer.revision}"
            owners = [
                lineage_owners[
                    (
                        c.capture_id,
                        c.context.merchant_key,
                        c.context.product_id,
                        c.context.variation_id,
                    )
                ]
                for c in claims
                if c.subject == "offer" and c.field in {"item_price", "availability"}
            ]
            duplicate = next((owner for owner in owners if owner != observation_id), None)
            times = [
                c.observed_at
                for c in [c for c in claims if c.subject == "offer"] + cost_claims
                if c.observed_at is not None
            ]
            observed_at = min(times) if times else None
            public = [c for c in offer.cost_scenarios if c.kind == "public_no_coupon"]
            reasons = []
            if (
                offer.qualification.state != "supported"
                or binding.resolution.state != "supported"
                or configuration.state != "supported"
            ):
                reasons.append("identity_selection_or_offer_unqualified")
            if (
                len(public) != 1
                or public[0].state != "verified_at_observation"
                or public[0].context.purchase_scope != "standalone"
            ):
                reasons.append("public_standalone_cost_unqualified")
            if state not in {"success", "partial"}:
                reasons.append("acquisition_not_a_new_observation")
            if duplicate:
                reasons.append("duplicate_acquisition_lineage")
            if observed_at is None or observed_at > capture.captured_at:
                reasons.append("observation_time_unavailable")
            if invalidations:
                reasons.append("revision_invalidated")
            if capture.history_contract_version is None:
                reasons.append("legacy_capture_not_qualified")
            validity: HistoryValidity = (
                "invalidated"
                if invalidations
                else "legacy_unqualified"
                if capture.history_contract_version is None
                else "unqualified"
                if reasons
                else "supported_at_capture"
            )
            synthetic = any(c.retention == "synthetic" for c in offer.evidence + cost_claims)
            # Value changes compare the same offer, configuration, purchase and
            # policy basis only. Revisions remain dependencies, not new cohorts.
            basis = json.dumps(
                [
                    offer.id,
                    configuration.id,
                    configuration.values,
                    offer.condition,
                    offer.quantity,
                    offer.destination,
                    offer.currency,
                    offer.purchase_mode,
                    configuration.policy_version,
                    binding.policy_version,
                    offer.policy_version,
                    [
                        (
                            c.kind,
                            c.key,
                            c.policy_version,
                            c.context.model_dump(mode="json"),
                            c.assumptions,
                        )
                        for c in public
                    ],
                ],
                sort_keys=True,
            )
            prior = previous.get(basis)
            change: HistoryChange = "not_comparable"
            if validity == "supported_at_capture":
                if prior is None:
                    change = "initial"
                else:
                    before = next(c for c in prior.costs if c.kind == "public_no_coupon").total
                    after = public[0].total
                    if (
                        before is not None
                        and after is not None
                        and before.currency == after.currency
                    ):
                        change = (
                            "unchanged"
                            if after.amount == before.amount
                            else "increased"
                            if after.amount > before.amount
                            else "decreased"
                        )
            observation = HistoryObservation(
                id=observation_id,
                capture_id=capture.capture_id,
                captured_at=capture.captured_at,
                observed_at=observed_at,
                candidate_id=candidate.id,
                source=candidate.source,
                acquisition_state=state
                if state in {"success", "partial", "cache_reuse"}
                else "unknown",
                offer=offer,
                binding=binding,
                configuration=configuration,
                costs=offer.cost_scenarios,
                dependencies=dependencies,
                policy_versions={
                    "history": "observation-history-v1",
                    "identity": configuration.policy_version,
                    "selection": binding.policy_version,
                    "offer": offer.policy_version,
                    **{f"cost:{c.id}": c.policy_version for c in offer.cost_scenarios},
                },
                lineage=lineage,
                duplicate_of=duplicate,
                change=change,
                validity=validity,
                invalidations=invalidations,
                reasons=reasons,
                evidence_kind="synthetic" if synthetic else "retained",
                market_history_eligible=validity == "supported_at_capture" and not synthetic,
            )
            observations.append(observation)
            if validity == "supported_at_capture":
                previous[basis] = observation
    attempts, gaps = [], []
    source, query = candidates[0].source, candidates[0].query
    candidate_captures = {c.capture_id for c in candidates}
    for capture in captures:
        effective_query = capture.request.source_queries.get(source, capture.request.query)
        if effective_query != query and capture.capture_id not in candidate_captures:
            continue
        for outcome in capture.outcomes:
            if outcome.source != source:
                continue
            attempts.append(
                HistoryAttempt(
                    capture_id=capture.capture_id,
                    captured_at=capture.captured_at,
                    source=source,
                    query=effective_query,
                    **outcome.model_dump(exclude={"source", "route"}),
                )
            )
            if outcome.state != "success":
                gaps.append(
                    HistoryGap(
                        kind="source_outcome",
                        start=capture.captured_at,
                        end=capture.captured_at,
                        capture_id=capture.capture_id,
                        state=outcome.state,
                        reason=outcome.reason or outcome.state,
                    )
                )
            elif capture.capture_id not in candidate_captures:
                gaps.append(
                    HistoryGap(
                        kind="not_returned",
                        start=capture.captured_at,
                        end=capture.captured_at,
                        capture_id=capture.capture_id,
                        state=outcome.state,
                        reason="Not returned in this scope; disappearance and availability are unknown.",
                    )
                )
    stamps = sorted({o.captured_at for o in observations})
    for start, end in pairwise(stamps):
        gaps.append(
            HistoryGap(
                kind="unobserved_interval",
                start=start,
                end=end,
                reason="No continuous observation between retained samples; cadence unspecified.",
            )
        )
    if stamps and now > stamps[-1]:
        gaps.append(
            HistoryGap(
                kind="open_interval",
                start=stamps[-1],
                end=now,
                reason="No newer retained observation; current price and availability unknown.",
            )
        )
    good = [
        o
        for o in observations
        if o.validity == "supported_at_capture" and o.observed_at is not None
    ]
    last = max(good, key=lambda o: o.observed_at or o.captured_at) if good else None
    last_good = (
        LastGood(
            observation_id=last.id,
            captured_at=last.captured_at,
            observed_at=last.observed_at,
            age_seconds=max(0, (now - last.observed_at).total_seconds()),
        )
        if last and last.observed_at
        else None
    )
    return ObservationHistory(
        candidate_id=candidate_id,
        as_of=now,
        history_state="limited" if good else "unavailable",
        observations=observations,
        attempts=attempts,
        gaps=gaps,
        last_good=last_good,
    )
