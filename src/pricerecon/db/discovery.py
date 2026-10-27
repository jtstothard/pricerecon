"""Additive storage for category leads and acquisition receipts, independent of Watches."""

import sqlite3
from contextlib import closing
from datetime import UTC, datetime

from pricerecon.categories.watches import configuration_preference_fit, interpret, resolve_watch
from pricerecon.core.costs import public_summary
from pricerecon.core.qualification import qualify_offer
from pricerecon.db.schema import DB_PATH
from pricerecon.models.costs import CostHistory, CostScenario
from pricerecon.models.discovery import (
    DiscoveryCandidate,
    DiscoveryCapture,
    DiscoveryFeed,
    PreferenceFit,
    PreferenceProfile,
    PreferenceUpdate,
)
from pricerecon.models.history import HistorySummary
from pricerecon.models.qualification import (
    Configuration,
    MerchantEvidenceReport,
    MerchantOffer,
    Resolution,
    SelectionBinding,
)


def init_discovery_tables(connection: sqlite3.Connection) -> None:
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS discovery_captures (
            capture_id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            captured_at TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS discovery_leads (
            candidate_id TEXT NOT NULL,
            capture_id TEXT NOT NULL REFERENCES discovery_captures(capture_id),
            payload_json TEXT NOT NULL,
            PRIMARY KEY (candidate_id, capture_id)
        );
        CREATE INDEX IF NOT EXISTS idx_discovery_category
            ON discovery_captures(category, captured_at);
        CREATE TABLE IF NOT EXISTS discovery_preferences (
            category TEXT PRIMARY KEY,
            revision INTEGER NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS discovery_configurations (
            id TEXT NOT NULL, revision INTEGER NOT NULL, capture_id TEXT NOT NULL,
            payload_json TEXT NOT NULL, PRIMARY KEY(id, revision)
        );
        CREATE TABLE IF NOT EXISTS discovery_bindings (
            id TEXT NOT NULL, revision INTEGER NOT NULL, capture_id TEXT NOT NULL,
            candidate_id TEXT NOT NULL, configuration_id TEXT NOT NULL,
            configuration_revision INTEGER NOT NULL, payload_json TEXT NOT NULL,
            PRIMARY KEY(id, revision),
            FOREIGN KEY(configuration_id, configuration_revision)
                REFERENCES discovery_configurations(id, revision)
        );
        CREATE INDEX IF NOT EXISTS idx_discovery_bindings_capture
            ON discovery_bindings(candidate_id, capture_id);
        CREATE TABLE IF NOT EXISTS discovery_offers (
            id TEXT NOT NULL, revision INTEGER NOT NULL, capture_id TEXT NOT NULL,
            candidate_id TEXT NOT NULL, binding_id TEXT NOT NULL, binding_revision INTEGER NOT NULL,
            payload_json TEXT NOT NULL, PRIMARY KEY(id, revision),
            FOREIGN KEY(binding_id, binding_revision) REFERENCES discovery_bindings(id, revision)
        );
        CREATE INDEX IF NOT EXISTS idx_discovery_offers_capture
            ON discovery_offers(candidate_id, capture_id);
        CREATE TABLE IF NOT EXISTS discovery_assessments (
            offer_id TEXT NOT NULL, offer_revision INTEGER NOT NULL,
            kind TEXT NOT NULL CHECK(kind = 'comparison'), policy_version TEXT NOT NULL,
            payload_json TEXT NOT NULL, PRIMARY KEY(offer_id, offer_revision, kind),
            FOREIGN KEY(offer_id, offer_revision) REFERENCES discovery_offers(id, revision)
        );
        CREATE TABLE IF NOT EXISTS discovery_cost_scenarios (
            id TEXT NOT NULL, revision INTEGER NOT NULL, capture_id TEXT NOT NULL,
            offer_id TEXT NOT NULL, offer_revision INTEGER NOT NULL,
            policy_version TEXT NOT NULL, payload_json TEXT NOT NULL,
            PRIMARY KEY(id, revision),
            FOREIGN KEY(offer_id, offer_revision) REFERENCES discovery_offers(id, revision)
        );
        CREATE INDEX IF NOT EXISTS idx_discovery_cost_offer
            ON discovery_cost_scenarios(offer_id, offer_revision);
        INSERT OR IGNORE INTO schema_migrations (version, description)
            VALUES ('1.5', 'Append exact-offer buyer-scenario cost evidence revisions');
        INSERT OR IGNORE INTO schema_migrations (version, description)
            VALUES ('1.4', 'Separate configuration, selection, offer and comparison evidence revisions');
        INSERT OR IGNORE INTO schema_migrations (version, description)
            VALUES ('1.3', 'Add staged category discovery captures, leads and preferences');
    """)


def save_capture(capture: DiscoveryCapture, candidates: list[DiscoveryCandidate]) -> None:
    with closing(sqlite3.connect(DB_PATH)) as connection, connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "INSERT INTO discovery_captures VALUES (?, ?, ?, ?)",
            (
                capture.capture_id,
                capture.request.category,
                capture.captured_at.isoformat(),
                capture.model_dump_json(),
            ),
        )
        # Capture revisions are retained even when values are unchanged. They
        # identify the inputs used, not new independent corroboration/freshness.
        for candidate in candidates:
            config_revisions: dict[str, int] = {}
            for configuration in candidate.configurations:
                if configuration.id not in config_revisions:
                    row = connection.execute(
                        "SELECT COALESCE(MAX(revision), 0) + 1 FROM discovery_configurations WHERE id = ?",
                        (configuration.id,),
                    ).fetchone()
                    configuration.revision = row[0]
                    config_revisions[configuration.id] = configuration.revision
                    connection.execute(
                        "INSERT INTO discovery_configurations VALUES (?, ?, ?, ?)",
                        (
                            configuration.id,
                            configuration.revision,
                            capture.capture_id,
                            configuration.model_dump_json(),
                        ),
                    )
                configuration.revision = config_revisions[configuration.id]
            for binding in candidate.bindings:
                binding.configuration_revision = config_revisions[binding.configuration_id]
                binding.revision = connection.execute(
                    "SELECT COALESCE(MAX(revision), 0) + 1 FROM discovery_bindings WHERE id = ?",
                    (binding.id,),
                ).fetchone()[0]
                connection.execute(
                    "INSERT INTO discovery_bindings VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        binding.id,
                        binding.revision,
                        capture.capture_id,
                        candidate.id,
                        binding.configuration_id,
                        binding.configuration_revision,
                        binding.model_dump_json(),
                    ),
                )
            for offer in candidate.offers:
                offer.binding_revision = next(
                    b.revision for b in candidate.bindings if b.id == offer.binding_id
                )
                offer.revision = connection.execute(
                    "SELECT COALESCE(MAX(revision), 0) + 1 FROM discovery_offers WHERE id = ?",
                    (offer.id,),
                ).fetchone()[0]
                connection.execute(
                    "INSERT INTO discovery_offers VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        offer.id,
                        offer.revision,
                        capture.capture_id,
                        candidate.id,
                        offer.binding_id,
                        offer.binding_revision,
                        offer.model_dump_json(exclude={"comparison", "cost_scenarios"}),
                    ),
                )
                binding = next(b for b in candidate.bindings if b.id == offer.binding_id)
                for cost in offer.cost_scenarios:
                    cost.offer_revision = offer.revision
                    cost.binding_revision = binding.revision
                    cost.configuration_revision = binding.configuration_revision
                    cost.revision = connection.execute(
                        "SELECT COALESCE(MAX(revision), 0) + 1 FROM discovery_cost_scenarios WHERE id = ?",
                        (cost.id,),
                    ).fetchone()[0]
                    connection.execute(
                        "INSERT INTO discovery_cost_scenarios VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            cost.id,
                            cost.revision,
                            capture.capture_id,
                            offer.id,
                            offer.revision,
                            cost.policy_version,
                            cost.model_dump_json(),
                        ),
                    )
                connection.execute(
                    "INSERT INTO discovery_assessments VALUES (?, ?, 'comparison', ?, ?)",
                    (
                        offer.id,
                        offer.revision,
                        offer.policy_version,
                        offer.comparison.model_dump_json(),
                    ),
                )
            connection.execute(
                "INSERT INTO discovery_leads VALUES (?, ?, ?)",
                (
                    candidate.id,
                    capture.capture_id,
                    candidate.model_dump_json(
                        exclude={"configuration", "configurations", "bindings", "offers"}
                    ),
                ),
            )


def hydrate_candidate(connection: sqlite3.Connection, candidate: DiscoveryCandidate) -> None:
    candidate.bindings = [
        SelectionBinding.model_validate_json(row[0])
        for row in connection.execute(
            "SELECT payload_json FROM discovery_bindings WHERE candidate_id = ? AND capture_id = ? ORDER BY rowid",
            (candidate.id, candidate.capture_id),
        )
    ]
    if not candidate.bindings:
        # Pre-1.4 leads retain their original lead price and intent. Project
        # explicit unknowns on read without backfilling qualified evidence.
        report = MerchantEvidenceReport(source_listing_id=candidate.source_listing_id)
        candidate.configuration, binding = resolve_watch(
            report, candidate.captured_at, candidate.id, candidate.source
        )
        candidate.configurations = [candidate.configuration]
        candidate.bindings = [binding]
        candidate.offers = [qualify_offer(candidate.source, report, binding, candidate.captured_at)]
        return
    configurations = {}
    for binding in candidate.bindings:
        row = connection.execute(
            "SELECT payload_json FROM discovery_configurations WHERE id = ? AND revision = ?",
            (binding.configuration_id, binding.configuration_revision),
        ).fetchone()
        configurations[binding.configuration_id] = Configuration.model_validate_json(row[0])
    candidate.configurations = list(configurations.values())
    if candidate.configurations:
        candidate.configuration = candidate.configurations[0]
    candidate.offers = [
        MerchantOffer.model_validate_json(row[0])
        for row in connection.execute(
            "SELECT payload_json FROM discovery_offers WHERE candidate_id = ? AND capture_id = ? ORDER BY rowid",
            (candidate.id, candidate.capture_id),
        )
    ]
    for offer in candidate.offers:
        offer.cost_scenarios = [
            CostScenario.model_validate_json(row[0])
            for row in connection.execute(
                "SELECT payload_json FROM discovery_cost_scenarios WHERE offer_id = ? AND offer_revision = ? ORDER BY rowid",
                (offer.id, offer.revision),
            )
        ]
        row = connection.execute(
            "SELECT payload_json FROM discovery_assessments WHERE offer_id = ? AND offer_revision = ? AND kind = 'comparison'",
            (offer.id, offer.revision),
        ).fetchone()
        offer.comparison = Resolution.model_validate_json(row[0])


def get_feed() -> DiscoveryFeed:
    from pricerecon.db.history import get_history

    with closing(sqlite3.connect(DB_PATH)) as connection, connection:
        connection.execute("BEGIN")
        captures = [
            DiscoveryCapture.model_validate_json(row[0])
            for row in connection.execute(
                "SELECT payload_json FROM discovery_captures WHERE category = 'watches' ORDER BY rowid DESC"
            )
        ]
        rows = connection.execute("SELECT payload_json FROM discovery_leads ORDER BY rowid DESC")
        latest: dict[str, DiscoveryCandidate] = {}
        for row in rows:
            candidate = DiscoveryCandidate.model_validate_json(row[0])
            if candidate.id not in latest:
                hydrate_candidate(connection, candidate)
                history = get_history(candidate.id, connection=connection)
                if history is not None:
                    candidate.history = HistorySummary(
                        observation_count=len(history.observations),
                        last_good=history.last_good,
                        validity=history.history_state,
                    )
                latest[candidate.id] = candidate
    for candidate in latest.values():
        candidate.public_delivered_total = public_summary(candidate.offers)
    preferences = get_preferences()
    candidates = []
    for candidate in latest.values():
        candidate.preference_fit = configuration_preference_fit(
            preferences.values, candidate.configurations
        )
        total = candidate.public_delivered_total
        budget = preferences.values.budget_gbp
        if (
            budget is not None
            and total.state == "verified_at_observation"
            and total.currency == "GBP"
            and total.amount is not None
        ):
            candidate.preference_fit = [
                fit for fit in candidate.preference_fit if fit.field != "budget"
            ] + [
                PreferenceFit(
                    field="budget",
                    strength=preferences.values.budget_strength,
                    state="fits" if total.amount <= budget else "outside",
                    reason=(
                        "Public delivered cost at observation is within budget."
                        if total.amount <= budget
                        else "Public delivered cost at observation is above budget."
                    ),
                )
            ]
        candidates.append(candidate)
    return DiscoveryFeed(candidates=candidates, captures=captures, preferences=preferences)


class PreferenceConflict(Exception):
    """An edit used an older preference revision."""


def get_preferences() -> PreferenceProfile:
    with closing(sqlite3.connect(DB_PATH)) as connection:
        row = connection.execute(
            "SELECT payload_json FROM discovery_preferences WHERE category = 'watches'"
        ).fetchone()
    profile = PreferenceProfile.model_validate_json(row[0]) if row else PreferenceProfile()
    return profile.model_copy(update={"interpretation": interpret(profile.values)})


def save_preferences(update: PreferenceUpdate) -> PreferenceProfile:
    profile = PreferenceProfile(
        revision=update.expected_revision + 1,
        updated_at=datetime.now(UTC),
        values=update.values,
        interpretation=interpret(update.values),
    )
    with closing(sqlite3.connect(DB_PATH)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT revision FROM discovery_preferences WHERE category = 'watches'"
        ).fetchone()
        if (row[0] if row else 0) != update.expected_revision:
            raise PreferenceConflict()
        connection.execute(
            "INSERT INTO discovery_preferences VALUES ('watches', ?, ?) "
            "ON CONFLICT(category) DO UPDATE SET revision=excluded.revision, payload_json=excluded.payload_json",
            (profile.revision, profile.model_dump_json()),
        )
    return profile


def get_cost_history(offer_id: str) -> CostHistory:
    with closing(sqlite3.connect(DB_PATH)) as connection:
        scenarios = [
            CostScenario.model_validate_json(row[0])
            for row in connection.execute(
                "SELECT payload_json FROM discovery_cost_scenarios WHERE offer_id = ? ORDER BY rowid",
                (offer_id,),
            )
        ]
    return CostHistory(offer_id=offer_id, scenarios=scenarios)
