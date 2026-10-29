"""Append-only corrections and dependent withdrawals share one SQLite transaction."""

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from pricerecon.models.discovery import DiscoveryCandidate, DiscoveryCapture

from pricerecon.db.connection import connect
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
        from pricerecon.db.discovery import hydrate_candidate
        from pricerecon.models.discovery import DiscoveryCandidate

        latest = connection.execute(
            "SELECT payload_json FROM discovery_leads WHERE candidate_id=? ORDER BY rowid DESC LIMIT 1",
            (candidate_id,),
        ).fetchone()
        candidate = DiscoveryCandidate.model_validate_json(latest[0])
        hydrate_candidate(connection, candidate)
        if qualified_correction_paths(connection, candidate, result):
            result.requalification = "supported_by_fresh_evidence"
            result.needs = []
    return result


def get_corrections(candidate_id: str, configuration_id: str) -> CorrectionHistory:
    with closing(connect(DB_PATH)) as connection, connection:
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
    with closing(connect(DB_PATH)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        history = read_corrections(connection, candidate_id, configuration_id)
        latest = connection.execute(
            "SELECT capture_id FROM discovery_leads WHERE candidate_id=? ORDER BY rowid DESC LIMIT 1",
            (candidate_id,),
        ).fetchone()
        bindings = connection.execute(
            "SELECT configuration_revision,id FROM discovery_bindings "
            "WHERE candidate_id=? AND capture_id=? AND configuration_id=? ORDER BY rowid DESC",
            (
                candidate_id,
                request.capture_id,
                request.observed_configuration_id or configuration_id,
            ),
        ).fetchall()
        if (
            history.revision != request.expected_revision
            or latest is None
            or latest[0] != request.capture_id
            or not any(
                b[0] == request.configuration_revision
                and b[1] in correction_binding_ids(connection, history)
                for b in bindings
            )
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
        # Retained selection IDs connect old and new definitions. Restrict
        # every exact revision to this candidate; definition IDs are global.
        binding_ids = correction_binding_ids(connection, history)
        bindings = retained_subject_bindings(
            connection,
            candidate_id,
            configuration_id,
            history.lineage[0].capture_id if history.lineage else None,
        )
        # A descendant definition can equal another journal's original
        # definition. Targets belong to their original captured selection revisions,
        # not every definition ID that this journal has passed through.
        tracking_configurations: set[str] = set()
        subject_revisions = {(binding[0], binding[1]) for binding in bindings}
        for row in connection.execute("SELECT payload_json FROM exact_tracking"):
            intent = ExactTracking.model_validate_json(row[0])
            if intent.candidate_id != candidate_id:
                continue
            anchored_selections = {
                (binding[0], binding[1])
                for binding in connection.execute(
                    "SELECT id,revision FROM discovery_bindings WHERE candidate_id=? "
                    "AND capture_id=? AND configuration_id=?",
                    (intent.candidate_id, intent.capture_id, intent.configuration_id),
                )
            }
            if anchored_selections & subject_revisions:
                tracking_configurations.add(intent.configuration_id)
        for identity in sorted(tracking_configurations):
            invalidate_configuration_tracking(
                connection, identity, reason, candidate_id=candidate_id
            )
        for row in connection.execute("SELECT payload_json FROM exact_tracking"):
            intent = ExactTracking.model_validate_json(row[0])
            if (
                intent.candidate_id == candidate_id
                and intent.configuration_id in tracking_configurations
            ):
                intent.intended_values = {**history.values, request.field: request.value}
                store(connection, intent)
        for binding_id, revision, identity, configuration_revision in bindings:
            references = [
                RevisionReference(kind="binding", id=binding_id, revision=revision),
            ]
            if not any(
                row[0] not in binding_ids
                for row in connection.execute(
                    "SELECT id FROM discovery_bindings WHERE configuration_id=? "
                    "AND configuration_revision=?",
                    (identity, configuration_revision),
                )
            ):
                references.append(
                    RevisionReference(
                        kind="configuration", id=identity, revision=configuration_revision
                    )
                )
            for offer_id, offer_revision in connection.execute(
                "SELECT id,revision FROM discovery_offers WHERE candidate_id=? "
                "AND binding_id=? AND binding_revision=?",
                (candidate_id, binding_id, revision),
            ):
                references.append(
                    RevisionReference(kind="offer", id=offer_id, revision=offer_revision)
                )
                references.extend(
                    RevisionReference(kind="cost", id=r[0], revision=r[1])
                    for r in connection.execute(
                        "SELECT id,revision FROM discovery_cost_scenarios "
                        "WHERE offer_id=? AND offer_revision=?",
                        (offer_id, offer_revision),
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
    with closing(connect(DB_PATH)) as connection:
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


def correction_binding_ids(
    connection: sqlite3.Connection, correction: CorrectionHistory
) -> set[str]:
    """Follow retained selections, never an unrelated matching definition."""
    return retained_selection_ids(
        connection,
        correction.candidate_id,
        correction.configuration_id,
        correction.lineage[0].capture_id if correction.lineage else None,
    )


def retained_selection_ids(
    connection: sqlite3.Connection,
    candidate_id: str,
    configuration_id: str,
    first_capture_id: str | None,
) -> set[str]:
    return {
        row[0]
        for row in retained_subject_bindings(
            connection, candidate_id, configuration_id, first_capture_id
        )
    }


def retained_subject_bindings(
    connection: sqlite3.Connection,
    candidate_id: str,
    configuration_id: str,
    first_capture_id: str | None,
) -> list[tuple[str, int, str, int]]:
    # Freeze membership at the first correction's observed capture. A later
    # unrelated selection can converge on a descendant's definition without
    # becoming part of this journal, including after a second correction.
    if first_capture_id is None:
        latest = connection.execute(
            "SELECT capture_id FROM discovery_leads WHERE candidate_id=? ORDER BY rowid DESC LIMIT 1",
            (candidate_id,),
        ).fetchone()
        first_capture_id = latest[0] if latest else None
    roots = {
        row[0]: row[1]
        for row in connection.execute(
            "SELECT id,revision FROM discovery_bindings WHERE candidate_id=? AND configuration_id=? "
            "AND capture_id=?",
            (candidate_id, configuration_id, first_capture_id),
        )
    }
    # Older revisions of the original identity are affected too. A different
    # identity preceding the subject capture is not a corrected descendant.
    return [
        row
        for row in connection.execute(
            "SELECT id,revision,configuration_id,configuration_revision FROM discovery_bindings "
            "WHERE candidate_id=?",
            (candidate_id,),
        )
        if row[0] in roots and (row[1] >= roots[row[0]] or row[2] == configuration_id)
    ]


def correction_paths(
    connection: sqlite3.Connection,
    candidate: "DiscoveryCandidate",
    correction: CorrectionHistory,
) -> list["DiscoveryCandidate"]:
    """One exact configuration -> binding -> offer -> cost dependency path."""
    bindings = correction_binding_ids(connection, correction)
    paths = []
    for binding in candidate.bindings:
        if binding.id not in bindings:
            continue
        for configuration in candidate.configurations:
            if (configuration.id, configuration.revision) != (
                binding.configuration_id,
                binding.configuration_revision,
            ):
                continue
            for offer in candidate.offers:
                if (offer.binding_id, offer.binding_revision) == (binding.id, binding.revision):
                    paths.append(
                        candidate.model_copy(
                            update={
                                "configuration": configuration,
                                "configurations": [configuration],
                                "bindings": [binding],
                                "offers": [offer],
                            }
                        )
                    )
    return paths


def qualified_correction_paths(
    connection: sqlite3.Connection,
    candidate: "DiscoveryCandidate",
    correction: CorrectionHistory,
) -> list["DiscoveryCandidate"]:
    """Publication and readback share the same exact retained-lineage gates."""
    from pricerecon.core.corrections import compatible_fresh_candidate
    from pricerecon.db.history import get_history
    from pricerecon.models.discovery import DiscoveryCapture

    capture = DiscoveryCapture.model_validate_json(
        connection.execute(
            "SELECT payload_json FROM discovery_captures WHERE capture_id=?",
            (candidate.capture_id,),
        ).fetchone()[0]
    )
    changed = connection.execute(
        "SELECT 1 FROM discovery_corrections WHERE candidate_id=? AND configuration_id=? "
        "AND rowid>? LIMIT 1",
        (candidate.id, correction.configuration_id, capture.correction_input_revision),
    ).fetchone()
    if (
        changed
        or not correction.lineage
        or any(
            o.completeness == "partial" for o in capture.outcomes if o.source == candidate.source
        )
    ):
        return []
    retained = get_history(candidate.id, connection=connection)
    observations = {o.id: o for o in retained.observations} if retained else {}
    boundary = correction.lineage[-1].recorded_at
    qualified = []
    for path in correction_paths(connection, candidate, correction):
        offer = path.offers[0]
        observation = observations.get(f"{candidate.capture_id}:{offer.id}:{offer.revision}")
        if (
            compatible_fresh_candidate(path, correction)
            and observation is not None
            and observation.observed_at is not None
            and observation.observed_at > boundary
            and "capture_lineage_unknown" not in observation.reasons
            and observation.acquisition_state == "success"
            and not any(
                is_withdrawn(connection, ref.kind, ref.id, ref.revision)
                for ref in observation.dependencies
            )
        ):
            qualified.append(path)
    return qualified


def validate_publication(
    connection: sqlite3.Connection,
    capture: "DiscoveryCapture",
    candidates: list["DiscoveryCandidate"],
) -> None:
    """The acquisition's inputs are checked while its publication lock is held."""
    from pricerecon.categories.watches import configuration_matches_values

    for candidate in candidates:
        corrections = candidate_corrections(connection, candidate.id)
        if not corrections:
            continue
        failed = {}
        for correction in corrections:
            qualified = {
                (p.offers[0].id, p.offers[0].revision)
                for p in qualified_correction_paths(connection, candidate, correction)
            }
            for path in correction_paths(connection, candidate, correction):
                offer = path.offers[0]
                if (offer.id, offer.revision) not in qualified:
                    failed[(offer.id, offer.revision)] = (path, correction)
        for path, correction in failed.values():
            capture.publication_state = "withdrawn"
            reason = "Correction inputs changed or fresh compatible evidence is still required"
            offer, binding, config = path.offers[0], path.bindings[0], path.configurations[0]
            references = [
                RevisionReference(kind="binding", id=binding.id, revision=binding.revision),
                RevisionReference(kind="offer", id=offer.id, revision=offer.revision),
                *(
                    RevisionReference(kind="cost", id=c.id, revision=c.revision)
                    for c in offer.cost_scenarios
                ),
            ]
            # A definition may be shared by several offers. A failed selected
            # offer cannot withdraw another independently supported selection.
            if not any(
                b.configuration_id == config.id
                and b.configuration_revision == config.revision
                and (o.id, o.revision) not in failed
                for b in candidate.bindings
                for o in candidate.offers
                if (o.binding_id, o.binding_revision) == (b.id, b.revision)
            ):
                references.append(
                    RevisionReference(kind="configuration", id=config.id, revision=config.revision)
                )
            for ref in references:
                withdraw(
                    connection,
                    ref,
                    correction.lineage[-1].id,
                    reason,
                )
        for correction in corrections:
            if not qualified_correction_paths(connection, candidate, correction):
                continue
            configuration_ids = {
                row[2]
                for row in retained_subject_bindings(
                    connection,
                    candidate.id,
                    correction.configuration_id,
                    correction.lineage[0].capture_id,
                )
            }
            for row in connection.execute("SELECT payload_json FROM exact_tracking"):
                intent = ExactTracking.model_validate_json(row[0])
                if (
                    intent.candidate_id == candidate.id
                    and intent.configuration_id in configuration_ids
                    and intent.intended_values is not None
                    and configuration_matches_values(correction.values, intent.intended_values)
                    and intent.invalidation_reason is not None
                ):
                    intent.invalidation_reason = None
                    store(connection, intent)
    connection.execute(
        "UPDATE discovery_captures SET payload_json=? WHERE capture_id=?",
        (capture.model_dump_json(), capture.capture_id),
    )
