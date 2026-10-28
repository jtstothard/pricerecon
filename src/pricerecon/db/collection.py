"""Durable accounting in the application's SQLite, owned by the native limiter."""

import sqlite3
from contextlib import closing
from datetime import UTC, datetime

from pricerecon.db.connection import connect
from pricerecon.db.schema import DB_PATH
from pricerecon.models.collection import (
    CollectionAttempt,
    CollectionStatus,
    ProviderRequestUsage,
    ResourceUsage,
)
from pricerecon.models.discovery import DiscoveryRequest


def init_collection_tables(connection: sqlite3.Connection) -> None:
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS collection_policies (
            scope_id TEXT PRIMARY KEY, payload_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS collection_usage (
            scope_id TEXT NOT NULL, resource TEXT NOT NULL, used INTEGER NOT NULL,
            PRIMARY KEY(scope_id, resource)
        );
        CREATE TABLE IF NOT EXISTS collection_attempts (
            id TEXT PRIMARY KEY, scope_id TEXT NOT NULL, source TEXT NOT NULL,
            purpose TEXT NOT NULL, context_id TEXT NOT NULL, query TEXT NOT NULL, attempted_at TEXT NOT NULL,
            state TEXT NOT NULL, reason TEXT, next_eligible_at TEXT,
            last_good_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_collection_attempt_source
            ON collection_attempts(scope_id, source, attempted_at);
        CREATE TABLE IF NOT EXISTS collection_policy_selection (
            singleton INTEGER PRIMARY KEY CHECK(singleton=1),
            scope_id TEXT, reason TEXT
        );
        INSERT OR IGNORE INTO collection_policy_selection
            SELECT 1, CASE WHEN COUNT(*)=1 THEN MIN(scope_id) END,
                CASE WHEN COUNT(*)>1 THEN 'operating_policy_ambiguous' END
            FROM collection_policies HAVING COUNT(*)>0;
        INSERT OR IGNORE INTO schema_migrations(version, description)
            VALUES ('2.1', 'Durable database-wide collection policy selection');
        INSERT OR IGNORE INTO schema_migrations(version, description)
            VALUES ('1.9', 'Shared finite operating envelopes and durable attempt accounting');
    """)


def collection_status() -> CollectionStatus:
    from pricerecon.core.rate_limiter import DurableAdmission

    selection = DurableAdmission.select_policy()
    policy = selection.policy
    now = datetime.now(UTC)
    with closing(connect(DB_PATH)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute("SELECT * FROM collection_attempts ORDER BY rowid DESC LIMIT 100")
        attempts = []
        for row in rows:
            good = datetime.fromisoformat(row["last_good_at"]) if row["last_good_at"] else None
            state = row["state"]
            # Running rows are conservatively unrefreshed, including after a crash.
            attempts.append(
                CollectionAttempt(
                    id=row["id"],
                    source=row["source"],
                    purpose=row["purpose"],
                    context_id=row["context_id"],
                    query=row["query"],
                    attempted_at=row["attempted_at"],
                    state=state,
                    reason=row["reason"],
                    next_eligible_at=row["next_eligible_at"],
                    last_good_at=good,
                    last_good_age_seconds=max(0, int((now - good).total_seconds()))
                    if good
                    else None,
                    evidence_state="observed_at_attempt"
                    if state in {"success", "success_empty"}
                    else "unrefreshed",
                )
            )
        policy_gate = selection.reason
        usage = []
        provider_usage = []
        if policy:
            values = dict(
                connection.execute(
                    "SELECT resource, used FROM collection_usage WHERE scope_id=?",
                    (policy.scope_id,),
                ).fetchall()
            )
            provider_usage = [
                ProviderRequestUsage(
                    source=source,
                    used=values.get(f"provider:{source}:requests", 0),
                    limit=cap.limit,
                    tracking_reserve=cap.tracking_reserve,
                )
                for source, cap in policy.provider_request_caps.items()
            ]
            usage = [
                ResourceUsage(
                    resource=resource,
                    used=values.get(resource, 0),
                    limit=cap.limit,
                    tracking_reserve=cap.tracking_reserve,
                )
                for resource, cap in policy.caps.items()
            ]
    valid = policy is not None and policy.starts_at <= now < policy.stops_at and not policy_gate
    return CollectionStatus(
        state="supplied" if valid else "expired" if policy and not policy_gate else "blocked",
        gates=(
            []
            if valid
            else [
                policy_gate or ("operating_policy_expired" if policy else "operating_policy_required")
            ]
        )
        + ["live_activation_not_authorized", "production_operating_envelope_unproven"],
        scope_id=policy.scope_id if policy else None,
        version=policy.version if policy else None,
        stops_at=policy.stops_at if policy else None,
        usage=usage,
        provider_usage=provider_usage,
        attempts=attempts,
    )


def storage_size(connection: sqlite3.Connection) -> int:
    """Actual SQLite btree payload bytes, including indexes (not JSON estimates).

    Filesystem allocation, WAL, logs and backups require a separate operating
    gate; no source is activated by passing this retained-payload ceiling.
    """
    from pricerecon.core.rate_limiter import AdmissionDenied

    try:
        value = connection.execute("SELECT COALESCE(SUM(payload), 0) FROM dbstat").fetchone()[0]
        if not isinstance(value, int) or value < 0:
            raise AdmissionDenied("sqlite_storage_accounting_invalid", state="blocked")
        return value
    except sqlite3.OperationalError as exc:
        raise AdmissionDenied("sqlite_storage_accounting_unavailable", state="blocked") from exc


def reject_capture(context_id: str, reason: str, state: str) -> None:
    """Rollback evidence freshness while retaining the existing control receipt."""
    with closing(connect(DB_PATH)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """UPDATE collection_attempts SET state=?, reason=?, last_good_at=(
            SELECT MAX(prior.attempted_at) FROM collection_attempts AS prior
            WHERE prior.source=collection_attempts.source AND prior.query=collection_attempts.query AND prior.context_id!=?
            AND prior.state IN ('success','success_empty')) WHERE context_id=?""",
            (state, reason, context_id, context_id),
        )


def verification_sources(request: DiscoveryRequest) -> set[str]:
    """Reserve priority only for queries already backing saved exact intent."""
    from pricerecon.db.tracking import list_tracking
    from pricerecon.models.discovery import DiscoveryCandidate

    candidate_ids = {intent.candidate_id for intent in list_tracking().items}
    result = set()
    with closing(connect(DB_PATH)) as connection:
        for row in connection.execute(
            "SELECT payload_json FROM discovery_leads ORDER BY rowid DESC"
        ):
            candidate = DiscoveryCandidate.model_validate_json(row[0])
            if candidate.id not in candidate_ids:
                continue
            if candidate.query == request.source_queries.get(candidate.source, request.query):
                result.add(candidate.source)
    return result


def refresh_unavailable(
    connection: sqlite3.Connection, candidate_id: str, assessed_at: datetime | None
) -> bool:
    if assessed_at is None:
        return False
    row = connection.execute(
        "SELECT payload_json FROM discovery_leads WHERE candidate_id=? ORDER BY rowid DESC LIMIT 1",
        (candidate_id,),
    ).fetchone()
    if not row:
        return False
    from pricerecon.models.discovery import DiscoveryCandidate

    candidate = DiscoveryCandidate.model_validate_json(row[0])
    latest = connection.execute(
        """SELECT state, attempted_at FROM collection_attempts
        WHERE source=? AND query=? AND purpose='verification' ORDER BY rowid DESC LIMIT 1""",
        (candidate.source, candidate.query),
    ).fetchone()
    return bool(
        latest
        and latest[0] not in {"success", "success_empty"}
        and datetime.fromisoformat(latest[1]) >= assessed_at
    )
