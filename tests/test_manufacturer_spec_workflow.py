"""B2: `supported` is reachable only through the manufacturer compilation path.

The test never hand-constructs `issuer_kind="manufacturer"` — it compiles a
fixture manufacturer specification document through production code and asserts
what that compiler emitted, then resolves the configuration.
"""

import pytest

from pricerecon.categories.watches import IDENTITY_FIELDS, resolve_watch
from pricerecon.connectors.manufacturer_spec import compile_manufacturer_spec
from pricerecon.models.source_evidence import EvidenceUse, SourceReceipt
from tests.support.document_fixtures import (
    CAPTURED_AT,
    FIXTURE_CONFIGURATION_KEY,
    manufacturer_spec_capture,
    manufacturer_spec_document,
)


def compiled_report(*, document=None, capture=None):
    capture = capture or manufacturer_spec_capture()
    document = document or manufacturer_spec_document()
    report = compile_manufacturer_spec(
        document,
        capture,
        configuration_key=FIXTURE_CONFIGURATION_KEY,
        source_listing_id="fixture:manufacturer:vx-9",
    )
    return report, capture


def test_compiled_manufacturer_document_reaches_supported_configuration():
    report, capture = compiled_report()
    # Provenance comes from the compiler's output; this test never writes it.
    assert report.claims
    assert all(claim.issuer_kind == "manufacturer" for claim in report.claims)
    assert {claim.field for claim in report.claims} == set(IDENTITY_FIELDS)
    assert all(claim.acquisition_capture_id == capture.capture_id for claim in report.claims)

    configuration, binding = resolve_watch(
        report, capture.retrieved_at, "fixture:manufacturer:vx-9", "manufacturer_spec"
    )

    assert configuration.state == "supported"
    assert configuration.values["maker"] == "Northgate Instrument Co."
    assert configuration.values["case_width_mm"] == "36"
    # Seller selection evidence is an independent subject: configuration
    # support must not leak into the binding claim.
    assert binding.resolution.state != "supported"


def test_downgraded_configuration_claim_cannot_keep_supported_state():
    report, capture = compiled_report()
    tampered = report.model_copy(
        update={
            "claims": [
                claim.model_copy(update={"issuer_kind": "seller"}) for claim in report.claims
            ]
        }
    )

    configuration, _ = resolve_watch(
        tampered, capture.retrieved_at, "fixture:manufacturer:vx-9", "manufacturer_spec"
    )

    assert configuration.state == "unresolved"


def test_incomplete_specification_document_cannot_resolve_configuration():
    document = manufacturer_spec_document().model_copy(
        update={"values": {"maker": "Northgate Instrument Co."}}
    )
    report, capture = compiled_report(document=document)

    configuration, _ = resolve_watch(
        report, capture.retrieved_at, "fixture:manufacturer:vx-9", "manufacturer_spec"
    )

    assert configuration.state == "unresolved"


def test_document_from_a_different_host_is_refused_at_compilation():
    capture = manufacturer_spec_capture()
    document = manufacturer_spec_document().model_copy(
        update={"document_url": "https://elsewhere.invalid/catalogue/vx-9/specification"}
    )

    with pytest.raises(ValueError, match="does not match the captured source host"):
        compile_manufacturer_spec(
            document,
            capture,
            configuration_key=FIXTURE_CONFIGURATION_KEY,
            source_listing_id="fixture:manufacturer:vx-9",
        )


def test_same_host_third_party_capture_cannot_reach_manufacturer_claims():
    """A marketplace capture plus a same-host 'spec document' forges nothing.

    The classic forgery is two caller-supplied strings made to agree: a
    third-party capture whose `source_host` matches a document URL on that
    same third-party host. Host agreement alone must never confer the
    manufacturer issuer kind.
    """
    capture = SourceReceipt(
        route="ebay_browse_item_v1",
        source_host="www.ebay.co.uk",
        capture_id="third-party-capture",
        retrieved_at=CAPTURED_AT,
        use=EvidenceUse(
            permission_reference="marketplace-capture-authority",
            retention="minimal_fields",
        ),
    )
    document = manufacturer_spec_document().model_copy(
        update={
            "issuer": "Rolex",
            "document_url": "https://www.ebay.co.uk/itm/vx-9/specification",
        }
    )

    with pytest.raises(ValueError, match="not an operator-registered manufacturer"):
        compile_manufacturer_spec(
            document,
            capture,
            configuration_key="ebay:vx-9",
            source_listing_id="ebay:vx-9",
        )


def test_spoofed_document_on_a_registered_host_is_refused_for_a_third_party_capture():
    """Cross-host spoofing: the document sits on the registered host, the capture does not."""
    capture = SourceReceipt(
        route="ebay_browse_item_v1",
        source_host="www.ebay.co.uk",
        capture_id="third-party-capture",
        retrieved_at=CAPTURED_AT,
        use=EvidenceUse(
            permission_reference="marketplace-capture-authority",
            retention="minimal_fields",
        ),
    )

    with pytest.raises(ValueError, match="does not match the captured source host"):
        compile_manufacturer_spec(
            manufacturer_spec_document(),
            capture,
            configuration_key=FIXTURE_CONFIGURATION_KEY,
            source_listing_id="fixture:manufacturer:vx-9",
        )


def test_registered_host_document_declaring_a_foreign_issuer_is_refused():
    """The issuer is the operator attestation for the host, not document content."""
    document = manufacturer_spec_document().model_copy(update={"issuer": "Somebody Else Ltd"})

    with pytest.raises(ValueError, match="does not match the operator-registered manufacturer"):
        compile_manufacturer_spec(
            document,
            manufacturer_spec_capture(),
            configuration_key=FIXTURE_CONFIGURATION_KEY,
            source_listing_id="fixture:manufacturer:vx-9",
        )
