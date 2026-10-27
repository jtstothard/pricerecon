"""SQLite-owned exact intent. All mutations compare revisions under a write lock."""

import sqlite3
from contextlib import closing
from datetime import UTC, datetime

from pricerecon.db.schema import DB_PATH
from pricerecon.models.qualification import Configuration
from pricerecon.models.tracking import (
    DeliveryResolution,
    ExactTracking,
    TargetEvent,
    TrackingAssessment,
    TrackingCreate,
    TrackingDeliveries,
    TrackingDelivery,
    TrackingList,
    TrackingUpdate,
)


class TrackingConflict(Exception):
    """Reload a changed subject or reconcile an interrupted delivery first."""


class TrackingMissing(Exception):
    """The specified retained subject does not exist."""


def init_tracking_tables(connection: sqlite3.Connection) -> None:
    script = """
        BEGIN IMMEDIATE;
        CREATE TABLE IF NOT EXISTS exact_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            configuration_id TEXT NOT NULL UNIQUE,
            revision INTEGER NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS exact_tracking_prices (
            tracking_id INTEGER NOT NULL REFERENCES exact_tracking(id),
            offer_key TEXT NOT NULL, payload_json TEXT NOT NULL,
            PRIMARY KEY(tracking_id, offer_key)
        );
        CREATE TABLE IF NOT EXISTS exact_tracking_events (
            event_id INTEGER PRIMARY KEY REFERENCES events(id),
            tracking_id INTEGER NOT NULL REFERENCES exact_tracking(id),
            payload_json TEXT NOT NULL
        );
    """
    # Existing event/notification ownership is retained. An exact intent isn't a
    # tracked search, so its events have no Watch FK. Preserve every legacy ID.
    if any(
        row[1] == "watch_id" and row[3] for row in connection.execute("PRAGMA table_info(events)")
    ):
        script += """
            CREATE TABLE events_tracking_migration (
                id INTEGER PRIMARY KEY AUTOINCREMENT, watch_id INTEGER,
                event_type TEXT NOT NULL, listing_key TEXT, severity TEXT NOT NULL,
                event_json TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(watch_id) REFERENCES watches(id) ON DELETE CASCADE
            );
            INSERT INTO events_tracking_migration SELECT * FROM events;
            UPDATE sqlite_sequence SET seq = MAX(seq, COALESCE(
                (SELECT seq FROM sqlite_sequence WHERE name='events'), 0
            )) WHERE name='events_tracking_migration';
            DROP TABLE events;
            ALTER TABLE events_tracking_migration RENAME TO events;
            CREATE INDEX idx_events_watch ON events(watch_id);
            CREATE INDEX idx_events_type ON events(event_type);
        """
    if not any(
        row[1] == "delivery_key" for row in connection.execute("PRAGMA table_info(notifications)")
    ):
        script += "ALTER TABLE notifications ADD COLUMN delivery_key TEXT;"
    script += """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_notification_delivery ON notifications(delivery_key);
        INSERT OR IGNORE INTO schema_migrations (version, description)
            VALUES ('1.6', 'Exact configuration intent and durable target delivery state');
        COMMIT;
    """
    try:
        connection.executescript(script)
    except sqlite3.Error:
        connection.rollback()
        raise


def _load(connection: sqlite3.Connection, tracking_id: int) -> ExactTracking:
    row = connection.execute(
        "SELECT payload_json FROM exact_tracking WHERE id = ?", (tracking_id,)
    ).fetchone()
    if row is None:
        raise TrackingMissing()
    return ExactTracking.model_validate_json(row[0])


def store(connection: sqlite3.Connection, intent: ExactTracking) -> None:
    connection.execute(
        "UPDATE exact_tracking SET revision = ?, payload_json = ? WHERE id = ?",
        (intent.revision, intent.model_dump_json(), intent.id),
    )


def create_tracking(request: TrackingCreate) -> ExactTracking:
    with closing(sqlite3.connect(DB_PATH)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT c.payload_json FROM discovery_configurations c "
            "JOIN discovery_bindings b ON b.configuration_id = c.id "
            "AND b.configuration_revision = c.revision "
            "WHERE b.candidate_id = ? AND b.capture_id = ? AND c.id = ? AND c.revision = ?",
            (
                request.candidate_id,
                request.capture_id,
                request.configuration_id,
                request.configuration_revision,
            ),
        ).fetchone()
        if row is None:
            if connection.execute(
                "SELECT 1 FROM discovery_leads WHERE candidate_id = ?", (request.candidate_id,)
            ).fetchone():
                raise TrackingConflict()
            raise TrackingMissing()
        configuration = Configuration.model_validate_json(row[0])
        latest_row = connection.execute(
            "SELECT payload_json FROM discovery_configurations WHERE id = ? ORDER BY revision DESC LIMIT 1",
            (request.configuration_id,),
        ).fetchone()
        latest = Configuration.model_validate_json(latest_row[0])
        if (
            configuration.state != "supported"
            or latest.state != "supported"
            or latest.values != configuration.values
            or latest.policy_version != configuration.policy_version
        ):
            raise TrackingConflict()
        if connection.execute(
            "SELECT 1 FROM exact_tracking WHERE configuration_id = ?", (request.configuration_id,)
        ).fetchone():
            raise TrackingConflict()
        now = datetime.now(UTC)
        cursor = connection.execute(
            "INSERT INTO exact_tracking(configuration_id, revision, payload_json) VALUES (?, 1, '{}')",
            (request.configuration_id,),
        )
        if cursor.lastrowid is None:
            raise RuntimeError("Tracking insert did not return its identity")
        intent = ExactTracking(
            id=cursor.lastrowid, created_at=now, updated_at=now, **request.model_dump()
        )
        store(connection, intent)
        return intent


def get_tracking(tracking_id: int) -> ExactTracking:
    with closing(sqlite3.connect(DB_PATH)) as connection:
        return project_tracking(connection, _load(connection, tracking_id))


def list_tracking() -> TrackingList:
    with closing(sqlite3.connect(DB_PATH)) as connection:
        return TrackingList(
            items=[
                project_tracking(connection, ExactTracking.model_validate_json(row[0]))
                for row in connection.execute("SELECT payload_json FROM exact_tracking ORDER BY id")
            ]
        )


def project_tracking(connection: sqlite3.Connection, intent: ExactTracking) -> ExactTracking:
    """Read-time invalidation never manufactures a new price decision or send."""
    assessment = intent.assessment
    reasons = []
    from pricerecon.db.collection import refresh_unavailable

    if refresh_unavailable(connection, intent.candidate_id, assessment.assessed_at):
        reasons.append("source_refresh_unavailable")
    if intent.invalidation_reason:
        reasons.append("evidence_invalidated")
    if evidence_revision_withdrawn(connection, intent, assessment):
        reasons.append("evidence_revision_withdrawn")
    if assessment.valid_until is not None and assessment.valid_until <= datetime.now(UTC):
        reasons.append("evidence_stale_or_expired")
    if assessment.preference_revision is not None:
        row = connection.execute(
            "SELECT revision FROM discovery_preferences WHERE category='watches'"
        ).fetchone()
        if (row[0] if row else 0) != assessment.preference_revision:
            reasons.append("preferences_changed_requires_observation")
    if assessment.offer_id is not None:
        latest = connection.execute(
            "SELECT MAX(revision) FROM discovery_offers WHERE id=?", (assessment.offer_id,)
        ).fetchone()[0]
        if latest != assessment.offer_revision:
            reasons.append("offer_revision_changed_requires_observation")
    if has_delivery_claim(connection, intent.id):
        reasons.append("delivery_in_flight_or_interrupted")
    if reasons:
        intent.assessment = assessment.model_copy(update={
            "state": "withheld",
            "reasons": list(dict.fromkeys(
                (assessment.reasons if assessment.state == "withheld" else []) + reasons
            )),
        })
    return intent


def update_tracking(tracking_id: int, request: TrackingUpdate) -> ExactTracking:
    with closing(sqlite3.connect(DB_PATH)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        intent = _load(connection, tracking_id)
        if intent.revision != request.expected_revision:
            raise TrackingConflict()
        if has_delivery_claim(connection, tracking_id):
            raise TrackingConflict()
        intent.target_gbp = request.target_gbp
        intent.notifications = request.notifications
        intent.revision += 1
        intent.updated_at = datetime.now(UTC)
        intent.assessment = TrackingAssessment(reasons=["target_changed_requires_observation"])
        store(connection, intent)
        return intent


def has_delivery_claim(connection: sqlite3.Connection, tracking_id: int) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM notifications n JOIN exact_tracking_events e ON n.event_id=e.event_id "
            "WHERE e.tracking_id=? AND n.status='dispatching' LIMIT 1",
            (tracking_id,),
        ).fetchone()
        is not None
    )


def list_deliveries(tracking_id: int) -> TrackingDeliveries:
    with closing(sqlite3.connect(DB_PATH)) as connection:
        _load(connection, tracking_id)
        deliveries = []
        for row in connection.execute(
            "SELECT payload_json FROM exact_tracking_events WHERE tracking_id=? ORDER BY event_id",
            (tracking_id,),
        ):
            event = TargetEvent.model_validate_json(row[0])
            delivery = TrackingDelivery.model_validate(
                event.model_dump(
                    exclude={
                        "assessment",
                        "listing",
                        "notification_channels",
                        "invalidation_revision",
                    }
                )
            )
            delivery.channels = {
                channel: "not_attempted" for channel in event.notification_channels
            }
            delivery.channels.update(
                dict(
                    connection.execute(
                        "SELECT channel, status FROM notifications WHERE event_id=?",
                        (delivery.event_id,),
                    )
                )
            )
            if delivery.channels:
                delivery.status = (
                    "pending"
                    if event.status == "pending"
                    and all(s == "not_attempted" for s in delivery.channels.values())
                    else (
                        "sent"
                        if all(s in {"sent", "reconciled_sent"} for s in delivery.channels.values())
                        else (
                            "ambiguous"
                            if any(
                                s in {"dispatching", "failed"} for s in delivery.channels.values()
                            )
                            else "withheld"
                        )
                    )
                )
            deliveries.append(delivery)
    return TrackingDeliveries(items=deliveries)


def resolve_delivery(tracking_id: int, event_id: int, request: DeliveryResolution) -> ExactTracking:
    with closing(sqlite3.connect(DB_PATH)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        intent = _load(connection, tracking_id)
        if intent.revision != request.expected_revision:
            raise TrackingConflict()
        if (
            connection.execute(
                "SELECT 1 FROM exact_tracking_events WHERE event_id=? AND tracking_id=?",
                (event_id, tracking_id),
            ).fetchone()
            is None
        ):
            raise TrackingMissing()
        cursor = connection.execute(
            "UPDATE notifications SET status=?, error_message=? WHERE event_id=? AND channel=? "
            "AND status IN ('dispatching','failed')",
            (
                "reconciled_sent" if request.resolution == "record_sent" else "abandoned_ambiguous",
                "Operator asserted no send in flight; resolution=" + request.resolution,
                event_id,
                request.channel,
            ),
        )
        if not cursor.rowcount:
            raise TrackingConflict()
        intent.revision += 1
        intent.updated_at = datetime.now(UTC)
        intent.assessment = TrackingAssessment(reasons=["delivery_resolved_requires_observation"])
        store(connection, intent)
        return intent


def invalidate_configuration_tracking(
    connection: sqlite3.Connection,
    configuration_id: str,
    reason: str,
) -> None:
    """Ticket07 seam: caller holds BEGIN IMMEDIATE with its correction writes.

    Invalidation retains the original subject/target and all prior events. It
    cannot relabel old prices or restore qualification. A caller must roll back
    its correction when delivery is in flight and this raises TrackingConflict.
    """
    for row in connection.execute(
        "SELECT payload_json FROM exact_tracking WHERE configuration_id=?",
        (configuration_id,),
    ):
        intent = ExactTracking.model_validate_json(row[0])
        if has_delivery_claim(connection, intent.id):
            raise TrackingConflict()
        intent.invalidation_revision += 1
        intent.invalidation_reason = reason
        intent.revision += 1
        intent.assessment = TrackingAssessment(reasons=["evidence_invalidated"])
        store(connection, intent)


def target_delivery_valid(connection: sqlite3.Connection, event_id: int) -> bool:
    """Check the reserved target/revision in the same transaction as a channel claim."""
    row = connection.execute(
        "SELECT e.payload_json, t.payload_json FROM exact_tracking_events e "
        "JOIN exact_tracking t ON e.tracking_id=t.id WHERE e.event_id=?",
        (event_id,),
    ).fetchone()
    if row is None:
        return False
    event, intent = TargetEvent.model_validate_json(row[0]), ExactTracking.model_validate_json(
        row[1]
    )
    preference = connection.execute(
        "SELECT revision FROM discovery_preferences WHERE category='watches'"
    ).fetchone()
    latest_offer = connection.execute(
        "SELECT MAX(revision) FROM discovery_offers WHERE id=?",
        (event.assessment.offer_id,),
    ).fetchone()[0]
    latest_cost = connection.execute(
        "SELECT MAX(revision) FROM discovery_cost_scenarios WHERE id=?",
        (event.assessment.scenario_id,),
    ).fetchone()[0]
    return (
        event.intent_revision == intent.revision
        and event.invalidation_revision == intent.invalidation_revision
        and intent.invalidation_reason is None
        and not evidence_revision_withdrawn(connection, intent, event.assessment)
        and event.assessment.preference_revision == (preference[0] if preference else 0)
        and event.assessment.valid_until is not None
        and event.assessment.valid_until > datetime.now(UTC)
        and event.assessment.offer_revision == latest_offer
        and event.assessment.scenario_revision == latest_cost
    )


def evidence_revision_withdrawn(
    connection: sqlite3.Connection,
    intent: ExactTracking,
    assessment: TrackingAssessment,
) -> bool:
    """Consume06's committed exact-revision withdrawal contract, without projecting history."""
    row = connection.execute(
        "SELECT binding_id FROM discovery_offers WHERE id=? AND revision=?",
        (assessment.offer_id, assessment.offer_revision),
    ).fetchone()
    references = [
        ("configuration", assessment.configuration_id or intent.configuration_id, assessment.configuration_revision),
        ("binding", row[0] if row else None, assessment.binding_revision),
        ("offer", assessment.offer_id, assessment.offer_revision),
        ("cost", assessment.scenario_id, assessment.scenario_revision),
    ]
    return any(
        connection.execute(
            "SELECT 1 FROM discovery_history_invalidations "
            "WHERE target_kind=? AND target_id=? AND target_revision=? LIMIT 1",
            reference,
        ).fetchone()
        is not None
        for reference in references
    )
