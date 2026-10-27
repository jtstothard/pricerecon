"""Append scoped price assessments against retained evidence in one SQLite snapshot."""

import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from decimal import Decimal

from pricerecon.core.comparisons import assess_observation, claim, cohort_for
from pricerecon.core.qualification import identity_key
from pricerecon.db.history import get_history
from pricerecon.db.schema import DB_PATH
from pricerecon.models.assessments import (
    AssessmentCoverage,
    AssessmentList,
    ComparablePath,
    ComparisonPolicy,
    PathExclusion,
    PriceAssessment,
)
from pricerecon.models.history import HistoryObservation


def init_assessment_tables(connection: sqlite3.Connection) -> None:
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS discovery_price_assessments (
            id TEXT NOT NULL, revision INTEGER NOT NULL, payload_json TEXT NOT NULL,
            PRIMARY KEY(id, revision)
        );
        CREATE TABLE IF NOT EXISTS discovery_comparison_policy (
            singleton INTEGER PRIMARY KEY CHECK(singleton=1), fingerprint TEXT
        );
        INSERT OR IGNORE INTO schema_migrations(version, description)
            VALUES ('2.2', 'Version scoped current-best and dated retained-low assessments');
    """)


def evaluate_comparisons(policy: ComparisonPolicy | None, now: datetime) -> None:
    from pricerecon.core.collection_policy import current_policy
    from pricerecon.db.collection import storage_size

    with closing(sqlite3.connect(DB_PATH)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        operating = current_policy(connection)
        before = storage_size(connection) if operating else 0
        connection.execute(
            "INSERT INTO discovery_comparison_policy VALUES (1,?) "
            "ON CONFLICT(singleton) DO UPDATE SET fingerprint=excluded.fingerprint",
            (identity_key(policy.model_dump_json()) if policy else None,),
        )
        if policy is None:
            if operating:
                from pricerecon.core.rate_limiter import DurableAdmission

                DurableAdmission(
                    operating, "sqlite", "verification", "price-assessment-policy"
                ).debit(
                    {"storage_bytes": max(0, storage_size(connection) - before)},
                    connection=connection,
                )
            return
        ids = [
            r[0] for r in connection.execute("SELECT DISTINCT candidate_id FROM discovery_leads")
        ]
        groups: dict[str, list[HistoryObservation]] = {}
        histories = [h for cid in ids if (h := get_history(cid, as_of=now, connection=connection))]
        attempts_by_candidate = {h.candidate_id: h.attempts for h in histories}
        latest = dict(
            connection.execute(
                "SELECT candidate_id, MAX(rowid) FROM discovery_leads GROUP BY candidate_id"
            )
        )
        latest_captures = {
            cid: connection.execute(
                "SELECT capture_id FROM discovery_leads WHERE rowid=?", (rowid,)
            ).fetchone()[0]
            for cid, rowid in latest.items()
        }
        for history in histories:
            for observation in history.observations:
                if observation.source in policy.sources:
                    key = identity_key(json.dumps(cohort_for(observation), sort_keys=True))
                    groups.setdefault(key, []).append(observation)
        for key, observations in groups.items():
            current: list[ComparablePath] = []
            retained: list[ComparablePath] = []
            exclusions = []
            quotes: dict[tuple[str, datetime], set[Decimal]] = {}
            current_quotes: dict[str, set[Decimal]] = {}
            for observation in observations:
                raw, _ = assess_observation(
                    observation, policy, observation.captured_at, require_history=False
                )
                if raw:
                    quotes.setdefault((raw.offer_key, raw.observed_at), set()).add(raw.amount)
                    if observation.capture_id == latest_captures[observation.candidate_id]:
                        current_quotes.setdefault(raw.offer_key, set()).add(raw.amount)
            for observation in observations:
                if (
                    policy.window_start
                    <= (observation.observed_at or observation.captured_at)
                    <= min(now, policy.window_end)
                ):
                    # Historical receipts remain dated evidence after recapture,
                    # but exact revision withdrawals still govern the observation.
                    from pricerecon.db.coupons import read_coupons
                    from pricerecon.models.coupons import CouponAssessment

                    observation.offer.coupons = [
                        CouponAssessment.model_validate_json(r[0])
                        for r in connection.execute(
                            "SELECT payload_json FROM discovery_coupons WHERE offer_id=? AND offer_revision=?",
                            (observation.offer.id, observation.offer.revision),
                        )
                    ]
                    path, reasons = assess_observation(observation, policy, observation.captured_at)
                    if path and len(quotes.get((path.offer_key, path.observed_at), set())) > 1:
                        path, reasons = None, ["conflicting_route_totals"]
                    if path:
                        retained.append(path)
                    else:
                        exclusions.append(
                            PathExclusion(
                                observation_id=observation.id,
                                candidate_id=observation.candidate_id,
                                reasons=reasons,
                                scope="history",
                            )
                        )
                else:
                    exclusions.append(
                        PathExclusion(
                            observation_id=observation.id,
                            candidate_id=observation.candidate_id,
                            reasons=["outside_disclosed_window"],
                            scope="history",
                        )
                    )
                if observation.capture_id == latest_captures[observation.candidate_id]:
                    from pricerecon.db.coupons import read_coupons

                    observation.offer.coupons = read_coupons(connection, observation.offer)
                    path, reasons = assess_observation(observation, policy, now)
                    if path and len(current_quotes.get(path.offer_key, set())) > 1:
                        path, reasons = None, ["conflicting_route_totals"]
                    from pricerecon.db.collection import refresh_unavailable

                    if refresh_unavailable(
                        connection, observation.candidate_id, observation.captured_at
                    ):
                        path, reasons = None, ["source_refresh_unavailable"]
                    attempts = attempts_by_candidate[observation.candidate_id]
                    if attempts:
                        latest_attempt = max(attempts, key=lambda a: a.captured_at)
                        if (
                            latest_attempt.capture_id != observation.capture_id
                            or latest_attempt.state != "success"
                        ):
                            path, reasons = None, ["source_refresh_unavailable_or_not_returned"]
                    if path:
                        current.append(path)
                    else:
                        exclusions.append(
                            PathExclusion(
                                observation_id=observation.id,
                                candidate_id=observation.candidate_id,
                                reasons=reasons,
                                scope="current",
                            )
                        )
            # Contradictory same-opportunity quotes cannot win through sorting.
            prices: dict[str, set[Decimal]] = {}
            for path in current:
                prices.setdefault(path.offer_key, set()).add(path.amount)
            conflicts = {k for k, values in prices.items() if len(values) > 1}
            for path in current:
                if path.offer_key in conflicts:
                    exclusions.append(
                        PathExclusion(
                            observation_id=path.observation_id,
                            candidate_id=path.candidate_id,
                            reasons=["conflicting_route_totals"],
                            scope="current",
                        )
                    )
            current = list(
                {p.offer_key: p for p in current if p.offer_key not in conflicts}.values()
            )
            revision = connection.execute(
                "SELECT COALESCE(MAX(revision),0)+1 FROM discovery_price_assessments WHERE id=?",
                (key,),
            ).fetchone()[0]
            relevant = [
                h for h in histories if h.candidate_id in {o.candidate_id for o in observations}
            ]
            sources = {a.source for h in relevant for a in h.attempts if a.state == "success"}
            result = PriceAssessment(
                id=key,
                revision=revision,
                candidate_ids=sorted({o.candidate_id for o in observations}),
                assessed_at=now,
                window_start=policy.window_start,
                window_end=min(now, policy.window_end),
                cohort=cohort_for(observations[0]),
                policy=policy,
                policy_fingerprint=identity_key(policy.model_dump_json()),
                current_best=claim(current, "Lowest verified total among the offers checked."),
                observed_low=claim(
                    retained, "Lowest of these retained observations within the disclosed dates."
                ),
                coverage=AssessmentCoverage(
                    sources=policy.sources,
                    unchecked_sources=[s for s in policy.sources if s not in sources],
                    capture_ids=sorted({a.capture_id for h in relevant for a in h.attempts}),
                    gaps=[gap for h in relevant for gap in h.gaps],
                    attempts=[attempt for h in relevant for attempt in h.attempts],
                ),
                exclusions=exclusions,
                dependencies=[ref for o in observations for ref in o.dependencies],
                input_captures={
                    o.candidate_id: latest_captures[o.candidate_id] for o in observations
                },
            )
            connection.execute(
                "INSERT INTO discovery_price_assessments VALUES (?,?,?)",
                (key, revision, result.model_dump_json()),
            )
        if operating:
            from pricerecon.core.rate_limiter import DurableAdmission

            DurableAdmission(operating, "sqlite", "verification", "price-assessments").debit(
                {"storage_bytes": max(0, storage_size(connection) - before)}, connection=connection
            )


def get_assessments(connection: sqlite3.Connection | None = None) -> AssessmentList:
    if connection is None:
        with closing(sqlite3.connect(DB_PATH)) as opened, opened:
            opened.execute("BEGIN")
            return get_assessments(opened)
    items = [
        PriceAssessment.model_validate_json(r[0])
        for r in connection.execute(
            "SELECT payload_json FROM discovery_price_assessments ORDER BY rowid"
        )
    ]
    latest = {item.id: item.revision for item in items}
    active = connection.execute(
        "SELECT fingerprint FROM discovery_comparison_policy WHERE singleton=1"
    ).fetchone()
    from pricerecon.db.collection import refresh_unavailable
    from pricerecon.db.corrections import is_withdrawn
    from pricerecon.db.discovery import datetime as clock

    for item in items:
        reasons = []
        if item.revision != latest[item.id]:
            reasons.append("superseded_assessment")
        if not active or active[0] != item.policy_fingerprint:
            reasons.append("comparison_policy_changed_or_unavailable")
        for cid, capture in item.input_captures.items():
            row = connection.execute(
                "SELECT capture_id FROM discovery_leads WHERE candidate_id=? ORDER BY rowid DESC LIMIT 1",
                (cid,),
            ).fetchone()
            if not row or row[0] != capture:
                reasons.append("recaptured_requires_assessment")
            if refresh_unavailable(connection, cid, item.assessed_at):
                reasons.append("source_refresh_unavailable")
        if any(
            p.valid_until is None or p.valid_until <= clock.now(UTC)
            for p in item.current_best.paths
        ):
            reasons.append("evidence_stale_or_expired")
        withdrawn = any(
            is_withdrawn(connection, ref.kind, ref.id, ref.revision) for ref in item.dependencies
        )
        if withdrawn:
            reasons.append("evidence_revision_withdrawn")
            for output in (item.current_best, item.observed_low):
                if output.state == "supported":
                    output.state = "invalidated"
        if reasons:
            item.historical = True
            item.invalidation_reasons = list(dict.fromkeys(reasons))
            if item.current_best.state == "supported":
                item.current_best.state = "historical"
            if (
                "comparison_policy_changed_or_unavailable" in reasons
                and item.observed_low.state == "supported"
            ):
                item.observed_low.state = "historical"
    return AssessmentList(items=items)
