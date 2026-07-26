"""Scan connector diagnosis test.

Captures the live Camofox/Byparr response for RTX query and verifies
the parser can extract listings.

Used to diagnose the WAF blocking issue and validate recovery via Camofox.
"""
import pytest
from pricerecon.connectors.html import SelectorConfig, parse_listings_from_html
from pricerecon.models import SourceType


@pytest.fixture(scope="module")
def scan_rtx_html() -> str:
    """Return the actual Camofox-captured HTML for RTX query."""
    path = "tests/fixtures/scan/RTX_camofox.html"
    with open(path) as f:
        return f.read()


def test_scan_template_selectors_parse_captured_listings(scan_rtx_html: str) -> None:
    """The checked-in Scan template must parse a real Camofox page."""
    from pricerecon.connectors.template_connector import TemplateConnector

    template = TemplateConnector._load_yaml("scan")
    selectors = SelectorConfig(**template["selectors"])
    listings = parse_listings_from_html(
        scan_rtx_html,
        base_url="https://www.scan.co.uk",
        source="scan",
        source_type=SourceType.RETAILER,
        selector=selectors,
        category="gpu",
    )
    assert len(listings) > 0, f"Expected listings, got {len(listings)}"
    assert listings[0].price is not None
    assert listings[0].url.startswith("https://www.scan.co.uk")
    assert "RTX" in listings[0].title_raw or "GPU" in listings[0].title_raw


def test_scan_camofox_fixture_structure_valid(scan_rtx_html: str) -> None:
    """Verify the Camofox fixture has valid HTML structure."""
    assert len(scan_rtx_html) > 100_000, "Fixture should be a real page (large HTML)"
    assert "<html" in scan_rtx_html or "<HTML" in scan_rtx_html
    assert "product" in scan_rtx_html.lower() or "item" in scan_rtx_html.lower()