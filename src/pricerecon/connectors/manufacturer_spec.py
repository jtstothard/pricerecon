"""Compile manufacturer specification documents into configuration evidence.

`Configuration.state == "supported"` requires `issuer_kind="manufacturer"`
claims for every identity dimension (`core/qualification.rejection_reason`),
and this module is the production path that emits them. A structured
specification document captured from the manufacturer's own host is compiled
into field-level claims bound to the acquisition capture, so the positive
qualification branch is reachable from real acquisition instead of fabricated
test input.

Fail-closed rules:
- The capture must carry an explicit evidence use (permission + retention);
  compilation never proceeds without it.
- The document URL must be a credential-bearing-link-safe pointer whose host
  matches the capture's `source_host`; a document cannot claim provenance for
  a host it was not captured from.
- Only dimensions the document actually states are emitted — no value is
  inferred, defaulted or copied from a seller listing.
"""

from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from pricerecon.connectors.evidence import claim, require_evidence_use
from pricerecon.models.qualification import (
    EvidenceContext,
    IdentityField,
    MerchantEvidenceReport,
    safe_pointer,
)
from pricerecon.models.source_evidence import SourceReceipt

CONNECTOR_ID = "manufacturer_spec"


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
    if not document.values:
        raise ValueError("Specification document states no identity dimensions")
    context = EvidenceContext(scope="configuration", configuration_key=configuration_key)
    locator_root = f"{host}{urlsplit(pointer).path or '/'}"
    claims = [
        claim(
            capture,
            subject="configuration",
            field=field,
            value=value,
            issuer=document.issuer,
            issuer_kind="manufacturer",
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
