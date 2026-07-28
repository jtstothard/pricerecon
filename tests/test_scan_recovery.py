"""Scan connector recovery test using real Camofox fixture.

This test validates that Scan connector recovers via TemplateConnector
using the correct selectors for the actual HTML structure from the
diagnosis task (TASK-XXXX).

Diagnosis findings:
- Direct HTTP: 403 Cloudflare block
- Camofox/Byparr route: Works (257KB fixture with 480 products)
- Template selectors need fixing to match real HTML structure
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


def test_scan_recovery_with_correct_selectors_parsers_camofox_fixture(
    scan_rtx_html: str,
) -> None:
    """Scan TemplateConnector with correct selectors must parse Camofox fixture.

    This test would fail with the original incorrect selectors and pass
    after the selectors are fixed to match the real HTML structure.
    """
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
    assert len(listings) > 0, f"Expected listings from Camofox fixture, got {len(listings)}"
    assert listings[0].price is not None
    assert listings[0].url.startswith("https://www.scan.co.uk/products/")
    assert "RTX" in listings[0].title_raw or "GPU" in listings[0].title_raw
    # Verify we get a reasonable number of products from the fixture
    assert len(listings) >= 30, f"Expected at least 30 products from fixture, got {len(listings)}"


def test_scan_connector_is_template_not_timeout_stub() -> None:
    """Scan connector must use TemplateConnector after recovery, not TimeoutRetailerConnector."""
    from pricerecon.connectors.scan import ScanConnector
    from pricerecon.connectors.template_connector import TemplateConnector

    # After recovery, ScanConnector should be TemplateConnector-based
    connector = ScanConnector()
    assert isinstance(connector, TemplateConnector), (
        "Scan connector should use TemplateConnector after recovery, "
        "not the TimeoutRetailerConnector stub"
    )
    assert connector.template_name == "scan"


@pytest.mark.asyncio
async def test_scan_template_connector_accepts_camofox_config() -> None:
    """Scan TemplateConnector should accept flaresolverr_url for Camofox integration."""
    from pricerecon.connectors.scan import ScanConnector

    # Connector must accept flaresolverr_url parameter for Camofox
    connector = ScanConnector(flaresolverr_url="http://test-camofox.example.com")
    assert connector.template_name == "scan"
    assert connector.template.use_flare_solverr is True
