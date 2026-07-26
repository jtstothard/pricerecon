"""Ebuyer connector regression tests.

Captures and validates the fix for /search?q= endpoint retirement
(replaced by /searchresults?descriptionfilter=).

Fix scope:
- Update search_url from /search?q= to /searchresults?descriptionfilter=
- Re-enable connector (remove disabled/disabled_reason)
- Add productImpressions JSON parsing to TemplateConnector

TDD sequence:
1. RED: verify current implementation fails against fixtures
2. GREEN: minimal fix applied
3. Verify full test suite
"""
import json

import pytest

from pricerecon.connectors.html import SelectorConfig, parse_listings_from_html
from pricerecon.connectors.template_connector import TemplateConnector
from pricerecon.models import SourceType


@pytest.fixture(scope="module")
def ebuyer_searchresults_html() -> str:
    """Return the captured searchresults page HTML for RTX 3080."""
    path = "tests/fixtures/ebuyer/searchresults-description-0.html"
    with open(path) as f:
        return f.read()


@pytest.fixture(scope="module")
def ebuyer_byparr_metadata() -> dict:
    """Return the metadata from the retired /search?q= endpoint."""
    path = "tests/fixtures/ebuyer/byparr-metadata.json"
    with open(path) as f:
        return json.load(f)


def test_retired_search_endpoint_returns_not_found(ebuyer_byparr_metadata: dict) -> None:
    """The old /search?q= endpoint returns the site's Not Found page."""
    # The capture metadata confirms HTTP 200 but a 346KB 404-like page
    assert ebuyer_byparr_metadata["status"] == 200
    assert ebuyer_byparr_metadata["message"] == "Challenge not detected!"
    assert ebuyer_byparr_metadata["html_length"] == 346866
    # Note: a real 404 page is returned despite HTTP 200


def test_current_ebuyer_selectors_fail_on_searchresults_page(
    ebuyer_searchresults_html: str,
) -> None:
    """Current selectors do not extract listings from the new endpoint."""
    template = TemplateConnector._load_yaml("ebuyer")
    selectors = SelectorConfig(**template["selectors"])
    listings = parse_listings_from_html(
        ebuyer_searchresults_html,
        base_url="https://www.ebuyer.com",
        source="ebuyer",
        source_type=SourceType.RETAILER,
        selector=selectors,
        category="gpu",
    )
    # RED: current selectors find 0 listings due to empty product-line-card elements
    assert len(listings) == 0, f"Expected 0 listings with current selectors, got {len(listings)}"


def test_ebuyer_json_parser_extracts_listings(
    ebuyer_searchresults_html: str,
) -> None:
    """Ebuyer parser extracts listings from productImpressions JSON."""
    from pricerecon.connectors.ebuyer import EbuyerConnector

    connector = EbuyerConnector(base_url="https://www.ebuyer.com")
    listings = connector._parse_ebuyer_json(ebuyer_searchresults_html)

    # GREEN: verify listings can be extracted from productImpressions JSON
    assert len(listings) > 0, f"Expected listings from productImpressions, got {len(listings)}"

    # Verify first listing structure
    first = listings[0]
    assert first.title_raw
    assert first.price is not None
    assert first.url.startswith('https://www.ebuyer.com/')
    assert 'RTX' in first.title_raw or '3080' in first.title_raw.lower()
    assert first.currency == 'GBP'