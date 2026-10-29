"""Original fixture documents for compilation-path tests; never market evidence.

Every value here is fictional: reserved ``.invalid`` hosts, an invented maker,
and synthetic retention. These fixtures prove code paths, not live facts.
"""

from datetime import UTC, datetime

from pricerecon.connectors.manufacturer_spec import ManufacturerSpecDocument
from pricerecon.models.source_evidence import EvidenceUse, SourceReceipt

SPEC_HOST = "specs.synthetic.invalid"
FIXTURE_CONFIGURATION_KEY = "fixture:manufacturer:vx-9"

CAPTURED_AT = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)


def manufacturer_spec_document() -> ManufacturerSpecDocument:
    """A fictional manufacturer specification stating every identity dimension."""
    return ManufacturerSpecDocument(
        issuer="Northgate Instrument Co.",
        document_url=f"https://{SPEC_HOST}/catalogue/vx-9/specification",
        values={
            "product_kind": "complete_watch",
            "maker": "Northgate Instrument Co.",
            "reference": "VX-9",
            "generation": "1",
            "movement": "quartz",
            "case_width_mm": "36",
            "dial": "black",
            "strap": "steel",
            "date_display": "no_date",
        },
    )


def manufacturer_spec_capture() -> SourceReceipt:
    """The acquisition receipt the fixture document was captured under."""
    return SourceReceipt(
        route="manufacturer_spec_document",
        source_host=SPEC_HOST,
        capture_id="fixture-manufacturer-spec:vx-9",
        retrieved_at=CAPTURED_AT,
        use=EvidenceUse(
            permission_reference="original-fixture-document",
            retention="synthetic",
        ),
    )


def manufacturer_spec_page() -> dict[str, object]:
    """The specification-index payload as captured from the fixture host.

    This is the raw document a real acquisition transport returns from a
    registered manufacturer host, not a pre-compiled report.
    """
    return {
        "documents": [
            {
                "listing_id": FIXTURE_CONFIGURATION_KEY,
                "configuration_key": FIXTURE_CONFIGURATION_KEY,
                "document": manufacturer_spec_document().model_dump(mode="json"),
            }
        ]
    }
