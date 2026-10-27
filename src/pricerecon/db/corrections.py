"""Append-only corrections and dependent withdrawals share one SQLite transaction."""

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from pricerecon.models.discovery import DiscoveryCandidate, DiscoveryCapture

from pricerecon.db.history import append_history_invalidation
from pricerecon.db.schema import DB_PATH
from pricerecon.db.tracking import invalidate_configuration_tracking, store
from pricerecon.models.corrections import CorrectionEntry, CorrectionHistory, CorrectionWrite
from pricerecon.models.history import HistoryInvalidation, RevisionReference
from pricerecon.models.qualification import Configuration, FieldEvidence
from pricerecon.models.tracking import ExactTracking


class CorrectionConflict(Exception):
    """Correction inputs changed; no partial correction is committed."""


class CorrectionMissing(Exception):
    """No retained configuration on this candidate."""


def init_correction_tables(connection: sqlite3.Connection) -> None:
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS discovery_corrections (
            id TEXT PRIMARY KEY, candidate_id TEXT NOT NULL, configuration_id TEXT NOT NULL,
            revision INTEGER NOT NULL, payload_json TEXT NOT NULL,
            UNIQUE(candidate_id, configuration_id, revision)
        );
        INSERT OR IGNORE INTO schema_migrations(version, description)
            VALUES ('2.0', 'Append human identity corrections and atomically withdraw dependencies');
    """)


def read_corrections(
    connection: sqlite3.Connection,
    candidate_id: str,
    configuration_id: str,
) -> CorrectionHistory:
    row = connection.execute(
        "SELECT c.payload_json FROM discovery_bindings b JOIN discovery_configurations c "
        "ON c.id=b.configuration_id AND c.revision=b.configuration_revision "
        "WHERE b.candidate_id=? AND c.id=? ORDER BY b.rowid LIMIT 1",
        (candidate_id, configuration_id),
    ).fetchone()
    if row is None:
        raise CorrectionMissing()
    original = Configuration.model_validate_json(row[0])
    entries = [
        CorrectionEntry.model_validate_json(r[0])
        for r in connection.execute(
            "SELECT payload_json FROM discovery_corrections WHERE candidate_id=? AND configuration_id=? "
            "ORDER BY revision",
            (candidate_id, configuration_id),
        )
    ]
    # Evidence remains exactly as acquired, including issuer/extractor/lineage.
    from pricerecon.models.qualification import MerchantOffer

    evidence: list[FieldEvidence] = []
    for r in connection.execute(
        "SELECT o.payload_json FROM discovery_offers o JOIN discovery_bindings b "
        "ON b.id=o.binding_id AND b.revision=o.binding_revision "
        "WHERE b.candidate_id=? AND b.configuration_id=? ORDER BY o.rowid LIMIT 1",
        (candidate_id, configuration_id),
    ):
        evidence = MerchantOffer.model_validate_json(r[0]).evidence
    values = dict(original.values)
    fields: dict[str, CorrectionEntry] = {}
    for entry in entries:
        fields[entry.field] = entry
        values[entry.field] = entry.value
    result = CorrectionHistory(
        candidate_id=candidate_id,
        configuration_id=configuration_id,
        revision=entries[-1].revision if entries else 0,
        state=(
            "disputed"
            if any(e.state == "disputed" for e in fields.values())
            else "corrected" if entries else "uncorrected"
        ),
        requalification="required" if entries else "not_required",
        values=values,
        original_configuration=original,
        original_evidence=evidence,
        lineage=entries,
        needs=(
            [
                "Fresh compatible configuration and selected merchant variation evidence",
                "Fresh availability, complete cost and coupon application evidence",
                "New history/comparison qualification and target assessment",
            ]
            if entries
            else []
        ),
    )

    if entries:
        from pricerecon.core.corrections import compatible_fresh_candidate
        from pricerecon.db.discovery import hydrate_candidate
        from pricerecon.models.discovery import DiscoveryCandidate

        latest = connection.execute(
            "SELECT payload_json FROM discovery_leads WHERE candidate_id=? ORDER BY rowid DESC LIMIT 1",
            (candidate_id,),
        ).fetchone()
        candidate = DiscoveryCandidate.model_validate_json(latest[0])
        hydrate_candidate(connection, candidate)
        if compatible_fresh_candidate(candidate, result) and not any(
            is_withdrawn(connection, "offer", offer.id, offer.revision)
            for offer in candidate.offers
        ):
            result.requalification = "supported_by_fresh_evidence"
            result.needs = []
    return result


def get_corrections(candidate_id: str, configuration_id: str) -> CorrectionHistory:
    with closing(sqlite3.connect(DB_PATH)) as connection, connection:
        connection.execute("BEGIN")
        return read_corrections(connection, candidate_id, configuration_id)


def withdraw(
    connection: sqlite3.Connection,
    target: RevisionReference,
    correction_id: str,
    reason: str,
) -> None:
    append_history_invalidation(
        connection,
        HistoryInvalidation(
            id=str(uuid4()),
            target=target,
            recorded_at=datetime.now(UTC),
            reason=reason,
            correction_reference=correction_id,
        ),
    )


def save_correction(
    candidate_id: str,
    configuration_id: str,
    request: CorrectionWrite,
) -> CorrectionHistory:
    with closing(sqlite3.connect(DB_PATH)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        history = read_corrections(connection, candidate_id, configuration_id)
        latest = connection.execute(
            "SELECT capture_id FROM discovery_leads WHERE candidate_id=? ORDER BY rowid DESC LIMIT 1",
            (candidate_id,),
        ).fetchone()
        binding = connection.execute(
            "SELECT configuration_revision FROM discovery_bindings "
            "WHERE candidate_id=? AND capture_id=? AND configuration_id=? ORDER BY rowid DESC LIMIT 1",
            (
                candidate_id,
                request.capture_id,
                request.observed_configuration_id or configuration_id,
            ),
        ).fetchone()
        if (
            history.revision != request.expected_revision
            or latest is None
            or latest[0] != request.capture_id
            or binding is None
            or binding[0] != request.configuration_revision
        ):
            raise CorrectionConflict()
        entry = CorrectionEntry(
            **request.model_dump(),
            id=str(uuid4()),
            revision=history.revision + 1,
            recorded_at=datetime.now(UTC),
            original_value=history.values.get(request.field),
            previous_correction_id=history.lineage[-1].id if history.lineage else None,
        )
        connection.execute(
            "INSERT INTO discovery_corrections VALUES (?, ?, ?, ?, ?)",
            (entry.id, candidate_id, configuration_id, entry.revision, entry.model_dump_json()),
        )
        # This raises TrackingConflict during a claimed send. The context rolls
        # back the correction and every withdrawal, including the inserted entry.
        reason = f"Identity {request.state}: {request.field}; correction {entry.id}"
        # The stable correction subject may now have a freshly qualified,
        # different configuration ID. Withdraw both its old and new descendants.
        configuration_ids = {
            configuration_id,
            request.observed_configuration_id or configuration_id,
            *(
                entry.observed_configuration_id
                for entry in history.lineage
                if entry.observed_configuration_id is not None
            ),
        }
        for identity in sorted(configuration_ids):
            invalidate_configuration_tracking(connection, identity, reason)
        for row in connection.execute("SELECT payload_json FROM exact_tracking"):
            intent = ExactTracking.model_validate_json(row[0])
            if intent.configuration_id in configuration_ids:
                intent.intended_values = {**history.values, request.field: request.value}
                store(connection, intent)
        for identity in sorted(configuration_ids):
            references = [
                RevisionReference(kind="configuration", id=identity, revision=r[0])
                for r in connection.execute(
                    "SELECT revision FROM discovery_configurations WHERE id=?",
                    (identity,),
                )
            ]
            references.extend(
                RevisionReference(kind="binding", id=r[0], revision=r[1])
                for r in connection.execute(
                    "SELECT id,revision FROM discovery_bindings WHERE configuration_id=?",
                    (identity,),
                )
            )
            references.extend(
                RevisionReference(kind="offer", id=r[0], revision=r[1])
                for r in connection.execute(
                    "SELECT o.id,o.revision FROM discovery_offers o JOIN discovery_bindings b "
                    "ON b.id=o.binding_id AND b.revision=o.binding_revision WHERE b.configuration_id=?",
                    (identity,),
                )
            )
            references.extend(
                RevisionReference(kind="cost", id=r[0], revision=r[1])
                for r in connection.execute(
                    "SELECT c.id,c.revision FROM discovery_cost_scenarios c JOIN discovery_offers o "
                    "ON c.offer_id=o.id AND c.offer_revision=o.revision JOIN discovery_bindings b "
                    "ON b.id=o.binding_id AND b.revision=o.binding_revision WHERE b.configuration_id=?",
                    (identity,),
                )
            )
            for ref in references:
                withdraw(connection, ref, entry.id, reason)
        return read_corrections(connection, candidate_id, configuration_id)


def is_withdrawn(connection: sqlite3.Connection, kind: str, identity: str, revision: int) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM discovery_history_invalidations WHERE target_kind=? AND target_id=? "
            "AND target_revision=? LIMIT 1",
            (kind, identity, revision),
        ).fetchone()
        is not None
    )


def correction_revision(connection: sqlite3.Connection) -> int:
    return int(
        connection.execute("SELECT COALESCE(MAX(rowid),0) FROM discovery_corrections").fetchone()[0]
    )


def input_revision() -> int:
    with closing(sqlite3.connect(DB_PATH)) as connection:
        return correction_revision(connection)


def candidate_corrections(
    connection: sqlite3.Connection, candidate_id: str
) -> list[CorrectionHistory]:
    return [
        read_corrections(connection, candidate_id, row[0])
        for row in connection.execute(
            "SELECT DISTINCT configuration_id FROM discovery_corrections WHERE candidate_id=?",
            (candidate_id,),
        )
    ]


def validate_publication(
    connection: sqlite3.Connection,
    capture: "DiscoveryCapture",
    candidates: list["DiscoveryCandidate"],
) -> None:
    """The acquisition's inputs are checked while its publication lock is held."""
    from pricerecon.core.corrections import compatible_fresh_candidate

    current_revision = correction_revision(connection)
    for candidate in candidates:
        corrections = candidate_corrections(connection, candidate.id)
        if not corrections:
            continue
        valid = capture.correction_input_revision == current_revision and all(
            compatible_fresh_candidate(candidate, correction) for correction in corrections
        )
        if valid:
            # Use06's retained capture lineage to reject a new extraction or
            # route that merely points back to pre-correction temporal evidence.
            from pricerecon.db.history import get_history

            retained = get_history(candidate.id, connection=connection)
            boundary = max(c.lineage[-1].recorded_at for c in corrections)
            observations = (
                [o for o in retained.observations if o.capture_id == capture.capture_id]
                if retained
                else []
            )
            valid = (
                bool(observations)
                and all(
                    o.observed_at is not None
                    and o.observed_at > boundary
                    and "capture_lineage_unknown" not in o.reasons
                    and o.acquisition_state == "success"
                    for o in observations
                )
                and all(
                    o.completeness != "partial"
                    for o in capture.outcomes
                    if o.source == candidate.source
                )
            )
        if valid:
            for row in connection.execute("SELECT payload_json FROM exact_tracking"):
                intent = ExactTracking.model_validate_json(row[0])
                if (
                    intent.candidate_id == candidate.id
                    and intent.intended_values is not None
                    and intent.invalidation_reason is not None
                ):
                    # Qualification is evaluated independently by the existing
                    # tracking engine. Correction/recovery alone cannot send.
                    intent.invalidation_reason = None
                    store(connection, intent)
            continue
        capture.publication_state = "withdrawn"
        reason = "Correction inputs changed or fresh compatible evidence is still required"
        correction_id = corrections[-1].lineage[-1].id
        for config in candidate.configurations:
            withdraw(
                connection,
                RevisionReference(kind="configuration", id=config.id, revision=config.revision),
                correction_id,
                reason,
            )
        for binding in candidate.bindings:
            withdraw(
                connection,
                RevisionReference(kind="binding", id=binding.id, revision=binding.revision),
                correction_id,
                reason,
            )
        for offer in candidate.offers:
            withdraw(
                connection,
                RevisionReference(kind="offer", id=offer.id, revision=offer.revision),
                correction_id,
                reason,
            )
            for cost in offer.cost_scenarios:
                withdraw(
                    connection,
                    RevisionReference(kind="cost", id=cost.id, revision=cost.revision),
                    correction_id,
                    reason,
                )
    connection.execute(
        "UPDATE discovery_captures SET payload_json=? WHERE capture_id=?",
        (capture.model_dump_json(), capture.capture_id),
    )
