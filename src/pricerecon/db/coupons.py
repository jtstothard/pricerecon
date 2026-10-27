"""Append coupon evidence in the acquisition owner's existing transaction."""

import sqlite3
from contextlib import closing

from pricerecon.core.coupons import assess_application, assess_coupon
from pricerecon.db.schema import DB_PATH
from pricerecon.models.coupons import CouponAssessment, CouponHistory, CouponInput
from pricerecon.models.qualification import MerchantOffer, SelectionBinding, safe_pointer


def init_coupon_tables(connection: sqlite3.Connection) -> None:
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS discovery_coupons (
            id TEXT NOT NULL, revision INTEGER NOT NULL,
            offer_id TEXT NOT NULL, offer_revision INTEGER NOT NULL,
            payload_json TEXT NOT NULL, PRIMARY KEY(id, revision),
            FOREIGN KEY(offer_id, offer_revision) REFERENCES discovery_offers(id, revision)
        );
        CREATE INDEX IF NOT EXISTS idx_coupons_offer ON discovery_coupons(offer_id, offer_revision);
        INSERT OR IGNORE INTO schema_migrations(version, description)
            VALUES ('1.8', 'Append exact-scenario coupon terms and reproduced application evidence');
    """)


def save_coupons(
    connection: sqlite3.Connection, offer: MerchantOffer, binding: SelectionBinding
) -> None:
    for coupon in offer.coupons:
        coupon.offer_revision = offer.revision
        coupon.binding_revision = binding.revision
        coupon.configuration_revision = binding.configuration_revision
        coupon.revision = connection.execute(
            "SELECT COALESCE(MAX(revision), 0) + 1 FROM discovery_coupons WHERE id = ?",
            (coupon.id,),
        ).fetchone()[0]
        assess_coupon(coupon, offer, binding)
        assess_application(coupon, offer, binding)
        sanitize_pointers(coupon)
        for conflict in coupon.source_conflicts:
            sanitize_pointers(conflict)
        connection.execute(
            "INSERT INTO discovery_coupons VALUES (?, ?, ?, ?, ?)",
            (coupon.id, coupon.revision, offer.id, offer.revision, coupon.model_dump_json()),
        )


def sanitize_pointers(coupon: CouponInput) -> None:
    """Sanitize even withheld/conflicting payloads that never reach accounting."""
    claims = list(coupon.opportunity_evidence)
    if coupon.terms:
        claims.extend(coupon.terms.evidence + coupon.terms.compatibility_evidence)
    if coupon.eligibility:
        claims.extend(coupon.eligibility.evidence)
    if coupon.application:
        application = coupon.application
        claims.extend(application.evidence + application.payable.context_evidence)
        claims.extend(e for line in application.lines for e in line.evidence)
        claims.extend(e for part in application.payable.components for e in part.evidence)
        claims.extend(e for fx in application.payable.fx_quotes for e in fx.evidence)
        claims.extend(e for benefit in application.payable.benefits for e in benefit.evidence)
        if application.receipt:
            receipt = application.receipt
            claims.append(receipt)
            observed = receipt.observation
            claims.extend(observed.eligibility.evidence)
            claims.extend(e for line in observed.lines for e in line.evidence)
            for scenario in (observed.before, observed.after):
                claims.extend(scenario.context_evidence)
                claims.extend(e for part in scenario.components for e in part.evidence)
                claims.extend(e for fx in scenario.fx_quotes for e in fx.evidence)
                claims.extend(e for benefit in scenario.benefits for e in benefit.evidence)
    for claim in claims:
        claim.pointer = safe_pointer(claim.pointer)


def read_coupons(connection: sqlite3.Connection, offer: MerchantOffer) -> list[CouponAssessment]:
    return [
        project_lineage(connection, CouponAssessment.model_validate_json(row[0]))
        for row in connection.execute(
            "SELECT payload_json FROM discovery_coupons WHERE offer_id = ? AND offer_revision = ? ORDER BY rowid",
            (offer.id, offer.revision),
        )
    ]


def project_lineage(connection: sqlite3.Connection, coupon: CouponAssessment) -> CouponAssessment:
    """Fail closed on newer source revisions; never rewrite stored receipts."""
    if coupon.resulting_cost is not None and (
        coupon.application is None or coupon.application.receipt is None
    ):
        coupon.state = "invalidated"
        coupon.historical_resulting_cost = coupon.resulting_cost
        coupon.resulting_cost = None
        coupon.issues = list(dict.fromkeys([*coupon.issues, "application_receipt_missing"]))
    row = connection.execute(
        "SELECT revision, binding_id, binding_revision, capture_id, candidate_id FROM discovery_offers WHERE id = ? ORDER BY revision DESC LIMIT 1",
        (coupon.offer_id,),
    ).fetchone()
    current = (
        row is not None and row[0] == coupon.offer_revision and row[2] == coupon.binding_revision
    )
    if current:
        latest_capture = connection.execute(
            "SELECT capture_id FROM discovery_leads WHERE candidate_id = ? ORDER BY rowid DESC LIMIT 1",
            (row[4],),
        ).fetchone()
        current = latest_capture is not None and latest_capture[0] == row[3]
    if current:
        binding = connection.execute(
            "SELECT revision, configuration_id, configuration_revision FROM discovery_bindings WHERE id = ? ORDER BY revision DESC LIMIT 1",
            (row[1],),
        ).fetchone()
        current = (
            binding is not None
            and binding[0] == coupon.binding_revision
            and binding[2] == coupon.configuration_revision
        )
        if current:
            latest_configuration = connection.execute(
                "SELECT revision, capture_id FROM discovery_configurations WHERE id = ? ORDER BY revision DESC LIMIT 1",
                (binding[1],),
            ).fetchone()
            # One capture can report the same configuration through multiple
            # offers. Those are retained input revisions, not later corrections.
            current = latest_configuration is not None and (
                latest_configuration[0] == coupon.configuration_revision
                or latest_configuration[1] == row[3]
            )
    from pricerecon.db.corrections import is_withdrawn

    if row is not None and is_withdrawn(connection, "offer", coupon.offer_id, coupon.offer_revision):
        current = False
    if row is not None and coupon.application is not None and coupon.application.receipt is not None:
        from pricerecon.models.corrections import CorrectionEntry

        boundaries = [CorrectionEntry.model_validate_json(r[0]).recorded_at for r in connection.execute(
            "SELECT payload_json FROM discovery_corrections WHERE candidate_id=?", (row[4],),
        )]
        receipt_time = coupon.application.receipt.observed_at
        if boundaries and (receipt_time is None or receipt_time <= max(boundaries)):
            current = False
            coupon.issues = list(dict.fromkeys([*coupon.issues, "receipt_predates_correction"]))
    if not current:
        coupon.lineage = "superseded"
        coupon.state = "invalidated"
        if coupon.resulting_cost is not None:
            coupon.historical_resulting_cost = coupon.resulting_cost
        coupon.resulting_cost = None
        coupon.issues = list(dict.fromkeys([*coupon.issues, "source_revision_superseded"]))
    return coupon


def get_coupon_history(offer_id: str) -> CouponHistory:
    with closing(sqlite3.connect(DB_PATH)) as connection:
        rows = connection.execute(
            "SELECT payload_json FROM discovery_coupons WHERE offer_id = ? ORDER BY rowid",
            (offer_id,),
        )
        return CouponHistory(
            offer_id=offer_id,
            assessments=[
                project_lineage(connection, CouponAssessment.model_validate_json(row[0]))
                for row in rows
            ],
        )
