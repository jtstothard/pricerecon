"""Compile manufacturer specification documents into configuration evidence.

`Configuration.state == "supported"` requires `issuer_kind="manufacturer"`
claims for every identity dimension (`core/qualification.rejection_reason`),
and this module is the production path that emits them. A structured
specification document captured from a manufacturer's own host is compiled
into field-level claims bound to the acquisition capture, so the positive
qualification branch is reachable from real acquisition instead of fabricated
test input: `ManufacturerSpecConnector` captures a specification index page
and compiles each document through `compile_manufacturer_spec`.

Fail-closed rules:
- The capture must carry an explicit evidence use (permission + retention);
  compilation never proceeds without it.
- The manufacturer classification is NOT caller-supplied. It is conferred by
  `MANUFACTURER_SPEC_HOSTS`, an operator-attested registry of manufacturer
  hosts recorded in reviewed code (the same shape as the storefront host
  allowlist in `categories/watch_sources.py`). A document URL whose host
  matches the capture's recorded `source_host` proves host agreement, not
  manufacturer identity: the host must also be a registry entry, and the
  document's declared issuer must equal the registry's attested manufacturer.
- The shared adapter helper `connectors/evidence.claim()` does not accept the
  manufacturer issuer kind; this module constructs those claims itself so the
  stamp exists in exactly one production place, behind the registry gate.
- The document URL must be a credential-bearing-link-safe pointer; a document
  cannot claim provenance for a host it was not captured from.
- Only dimensions the document actually states are emitted — no value is
  inferred, defaulted or copied from a seller listing.

The shipped registry contains only the reserved `.invalid` fixture host so
the offline workflows exercise the real path; it can never resolve to a live
host. Registering a real manufacturer host is an operator decision requiring
capture/display/reuse authority for that host, recorded here in review.
"""

from urllib.parse import quote_plus, urlsplit
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from pricerecon.connectors.base import BaseConnector
from pricerecon.connectors.evidence import receipt, require_evidence_use
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus
from pricerecon.core.collection_transport import collection_http_client
from pricerecon.models import NormalizedListing, SourceType
from pricerecon.models.qualification import (
    EvidenceContext,
    EvidenceSearchReport,
    FieldEvidence,
    IdentityField,
    MerchantEvidenceReport,
    safe_pointer,
)
from pricerecon.models.source_evidence import EvidenceUse, SourceReceipt

CONNECTOR_ID = "manufacturer_spec"
CAPTURE_ROUTE = "manufacturer_spec_documents_v1"

# Operator-attested manufacturer specification hosts: host (casefolded) to the
# manufacturer's legal name. Entries are code-review decisions, never runtime
# configuration, so no caller-supplied pair of strings can add a host.
MANUFACTURER_SPEC_HOSTS: dict[str, str] = {
    # Reserved unroutable fixture host (RFC 2606); offline capability only.
    "specs.synthetic.invalid": "Northgate Instrument Co.",
}


def manufacturer_for_host(host: str | None) -> str | None:
    """The operator-attested manufacturer for a capture host, if any."""
    if host is None:
        return None
    return MANUFACTURER_SPEC_HOSTS.get(host.strip().casefold())


class ManufacturerSpecDocument(BaseModel):
    """A captured manufacturer specification document in compiled form."""

    model_config = ConfigDict(extra="forbid")

    issuer: str = Field(min_length=1, max_length=250)
    document_url: str = Field(min_length=1, max_length=500)
    values: dict[IdentityField, str] = Field(default_factory=dict)

    @field_validator("values")
    @classmethod
    def nonblank_values(cls, value: dict[IdentityField, str]) -> dict[IdentityField, str]:
        if any(not entry.strip() for entry in value.values()):
            raise ValueError("Specification dimensions require stated values")
        return value


class CapturedSpecification(BaseModel):
    """One specification-document entry as captured from the index page."""

    model_config = ConfigDict(extra="forbid")

    listing_id: str = Field(min_length=1, max_length=250)
    configuration_key: str = Field(min_length=1, max_length=250)
    document: ManufacturerSpecDocument


class SpecificationPage(BaseModel):
    """A bounded specification-index page as returned by the host transport."""

    model_config = ConfigDict(extra="forbid")

    documents: list[CapturedSpecification] = Field(default_factory=list)


def _attested_claim(
    capture: SourceReceipt,
    *,
    field: IdentityField,
    value: str,
    issuer: str,
    pointer: str,
    locator: str,
    context: EvidenceContext,
) -> FieldEvidence:
    """The only producer of manufacturer-issued claims in the codebase.

    `issuer_kind` is not a parameter: the manufacturer stamp is conferred by
    this module's registry gate in `compile_manufacturer_spec` alone. The
    shared adapter helper rejects the kind, so no other connector can pass it.
    """
    if capture.use is None:
        raise ValueError("Evidence use missing")
    return FieldEvidence(
        id=f"{capture.capture_id}:{locator}:{field}",
        subject="configuration",
        field=field,
        value=value,
        issuer=issuer,
        issuer_kind="manufacturer",
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


def compile_manufacturer_spec(
    document: ManufacturerSpecDocument,
    capture: SourceReceipt,
    *,
    configuration_key: str,
    source_listing_id: str,
) -> MerchantEvidenceReport:
    """Compile a captured manufacturer spec document into a configuration report."""
    if not configuration_key.strip():
        raise ValueError("Manufacturer definitions require an explicit configuration key")
    require_evidence_use(capture.use, CONNECTOR_ID)
    pointer = safe_pointer(document.document_url)
    if pointer is None:
        raise ValueError("Specification pointer must be a credential-free http(s) location")
    host = urlsplit(pointer).hostname or ""
    if capture.source_host is None or host.casefold() != capture.source_host.casefold():
        raise ValueError("Specification document does not match the captured source host")
    attested = manufacturer_for_host(host)
    if attested is None:
        raise ValueError("Specification host is not an operator-registered manufacturer host")
    if document.issuer.strip().casefold() != attested.strip().casefold():
        raise ValueError(
            "Document issuer does not match the operator-registered manufacturer for the host"
        )
    if not document.values:
        raise ValueError("Specification document states no identity dimensions")
    context = EvidenceContext(scope="configuration", configuration_key=configuration_key)
    locator_root = f"{host}{urlsplit(pointer).path or '/'}"
    claims = [
        _attested_claim(
            capture,
            field=field,
            value=value,
            issuer=attested,
            pointer=pointer,
            locator=f"{locator_root}#{field}",
            context=context,
        )
        for field, value in sorted(document.values.items())
    ]
    return MerchantEvidenceReport(
        source_listing_id=source_listing_id,
        configuration_key=configuration_key,
        claims=claims,
    )


def manufacturer_spec_evidence(payload: object, capture: SourceReceipt) -> EvidenceSearchReport:
    """Compile a captured specification-index page through the registry gate.

    Production document-compilation seam, in the shape of
    `connectors/shopify_evidence.shopify_evidence`: raw captured payload plus
    the acquisition capture recorded by the transport; the report is built
    only by `compile_manufacturer_spec`.
    """
    page = SpecificationPage.model_validate(payload)
    capture.pages_captured, capture.page_limit = 1, 1
    capture.discovered_count = len(page.documents)
    capture.completeness = "partial"
    capture.issues = [
        "single_specification_page",
        "pagination_not_exhausted",
        "query_not_catalogue_filter",
    ]
    listings, reports = [], []
    for entry in page.documents:
        report = compile_manufacturer_spec(
            entry.document,
            capture,
            configuration_key=entry.configuration_key,
            source_listing_id=entry.listing_id,
        )
        reference = entry.document.values.get("reference")
        listings.append(
            NormalizedListing.model_validate(
                {
                    "source": CONNECTOR_ID,
                    "source_type": SourceType.MANUFACTURER,
                    "source_listing_id": entry.listing_id,
                    "title_raw": f"{entry.document.issuer} {reference}".strip(),
                    "price": None,
                    "currency": "",
                    "url": entry.document.document_url,
                    "timestamp_seen": capture.retrieved_at,
                }
            )
        )
        reports.append(report)
    capture.inspected_count = len(listings)
    return EvidenceSearchReport(
        listings=listings,
        evidence=reports,
        source_evidence=capture,
        acquisition_state="partial",
        acquisition_reason="bounded_specification_page",
        completeness="partial",
    )


class ManufacturerSpecConnector(BaseConnector):
    """Capture specification documents from operator-registered manufacturer hosts.

    The configured base URL selects which registered host to capture; the
    registry decides whether that host may ever confer manufacturer
    provenance. A manufacturer host is a definition source, never a merchant:
    listings carry no price and reports claim no seller selection.
    """

    collection_accounting = "http_v1"

    def __init__(
        self,
        base_url: str | None = None,
        spec_host: str | None = None,
        *,
        evidence_use: dict[str, object] | None = None,
    ) -> None:
        self.base_url = (base_url or (f"https://{spec_host}" if spec_host else "")).rstrip("/")
        self._client = collection_http_client(timeout=30.0)
        self.evidence_use = (
            EvidenceUse.model_validate(evidence_use) if evidence_use is not None else None
        )

    @property
    def source_role(self) -> SourceType:
        return SourceType.MANUFACTURER

    @property
    def connector_id(self) -> str:
        return CONNECTOR_ID

    def validate_evidence_access(self) -> None:
        if not self.base_url:
            raise ConnectorDegradedError(
                status=ConnectorStatus.auth_failed,
                message="manufacturer_spec requires base_url for a registered specification host",
                connector_id=self.connector_id,
                detail={"missing": ["base_url"], "accepted_keys": ["base_url", "spec_host"]},
            )
        self.evidence_receipt = receipt(
            CAPTURE_ROUTE,
            self.evidence_use,
            [
                "manufacturer-host specification capture/display/reuse authority",
                "operator-registered host entry",
                "separate archive grant",
            ],
        )
        # The capture's host is recorded here at acquisition time from the URL
        # this connector actually fetches, exactly like the storefront seam.
        self.evidence_receipt.source_host = urlsplit(self.base_url).hostname
        if manufacturer_for_host(self.evidence_receipt.source_host) is None:
            raise ConnectorDegradedError(
                ConnectorStatus.disabled,
                "Manufacturer specifications require an operator-registered host",
                self.connector_id,
            )
        require_evidence_use(self.evidence_use, self.connector_id)

    async def search_with_evidence(
        self, query: str, filters: dict[str, Any] | None = None
    ) -> EvidenceSearchReport:
        self.validate_evidence_access()
        response = await self._client.get(
            f"{self.base_url}/specifications.json?q={quote_plus(query)}",
            headers={"User-Agent": "Mozilla/5.0 (compatible; PriceRecon/1.0)"},
        )
        response.raise_for_status()
        return manufacturer_spec_evidence(response.json(), self.evidence_receipt)

    async def search(
        self, query: str, filters: dict[str, Any] | None = None
    ) -> list[NormalizedListing]:
        raise ConnectorDegradedError(
            status=ConnectorStatus.disabled,
            message="Manufacturer specification captures require explicit evidence authority",
            connector_id=self.connector_id,
        )

    async def initialize(self) -> None:
        return None

    async def cleanup(self) -> None:
        await self._client.aclose()
