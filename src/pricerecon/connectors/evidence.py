"""Minimal shared report construction for existing source adapters."""

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus
from pricerecon.models.qualification import (
    EvidenceContext,
    FieldEvidence,
    IdentityField,
    OfferField,
)
from pricerecon.models.source_evidence import EvidenceUse, SourceReceipt


def receipt(route: str, use: EvidenceUse | None, prerequisites: list[str]) -> SourceReceipt:
    return SourceReceipt(
        route=route,
        capture_id=str(uuid4()),
        retrieved_at=datetime.now(UTC),
        use=use,
        prerequisites=prerequisites,
    )


def require_evidence_use(use: EvidenceUse | None, connector_id: str) -> None:
    if use is None:
        raise ConnectorDegradedError(
            ConnectorStatus.disabled,
            "Source evidence requires explicit capture and retention authority",
            connector_id,
        )


def claim(
    capture: SourceReceipt,
    *,
    subject: Literal["configuration", "selection", "offer"],
    field: IdentityField | OfferField,
    value: str,
    issuer: str,
    issuer_kind: Literal["seller", "visible_observation"],
    pointer: str,
    locator: str,
    context: EvidenceContext,
) -> FieldEvidence:
    """Build an adapter claim whose issuer kind the caller can self-assert.

    `manufacturer` is deliberately not accepted here: manufacturer provenance
    is conferred only by the operator-registry gate inside
    `connectors/manufacturer_spec.py`, never by a caller-supplied string.
    """
    if capture.use is None:
        raise ValueError("Evidence use missing")
    return FieldEvidence(
        id=f"{capture.capture_id}:{locator}:{field}",
        subject=subject,
        field=field,
        value=value,
        issuer=issuer,
        issuer_kind=issuer_kind,
        extractor=capture.route,
        extractor_kind="deterministic_dom" if "browser" in capture.route else "structured_data",
        observed_at=capture.retrieved_at,
        retrieved_at=capture.retrieved_at,
        capture_id=capture.capture_id,
        acquisition_capture_id=capture.capture_id,
        route=capture.route,
        pointer=pointer,
        locator=locator,
        context=context,
        derived_from=[f"{capture.capture_id}:{locator}"],
        permission_reference=capture.use.permission_reference,
        retention=capture.use.retention,
    )
