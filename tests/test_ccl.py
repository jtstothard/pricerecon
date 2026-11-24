"""CCL connector tests for Cloudflare challenge recovery and failure handling."""

from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from pricerecon.connectors.ccl import CclConnector
from pricerecon.connectors.flaresolverr import FlareSolverrClient
from pricerecon.connectors.html import parse_price
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus
from pricerecon.models import StockState

FIXTURE = Path(__file__).parent / "fixtures" / "ccl" / "search_rtx_5070.html"


@pytest.mark.asyncio
async def test_ccl_recovers_through_flaresolverr(monkeypatch) -> None:
    """CCL uses the challenge-recovery lane and parses real search-result cards."""

    async def request_html(_self, url: str) -> str:
        assert url == "https://www.cclonline.com/search?query=RTX+5070"
        return FIXTURE.read_text(encoding="utf-8")

    monkeypatch.setattr(FlareSolverrClient, "request_html", request_html)
    connector = CclConnector(flaresolverr_url="http://solverr.test/v1")

    listings = await connector.search("RTX 5070")
    await connector.cleanup()

    # Three in-stock cards parse; the sold-out card has no price and is skipped.
    assert [(listing.title_raw, listing.price) for listing in listings] == [
        ("ASUS GeForce RTX 5070 Dual OC 12GB GPU", Decimal("795.99")),
        ("Horizon Ryzen 5 RTX 5070 Pre-built Gaming PC", Decimal("1579.99")),
        ("Palit GeForce RTX 5070 Infinity 3 OC 12GB GPU", Decimal("779.99")),
    ]
    first = listings[0]
    assert first.source == "ccl"
    assert first.currency == "GBP"
    assert first.url == (
        "https://www.cclonline.com/"
        "90yv0m17-m0na00-asus-geforce-rtx-5070-dual-oc-12gb-gddr7-graphics-card-495643/"
    )
    assert first.source_listing_id == (
        "90yv0m17-m0na00-asus-geforce-rtx-5070-dual-oc-12gb-gddr7-graphics-card-495643"
    )
    assert all(listing.in_stock is True for listing in listings)
    assert all(listing.stock_state is StockState.IN_STOCK for listing in listings)


def test_parse_price_rejoins_pence_split_across_elements() -> None:
    """CCL renders "£795.<span>99</span>", which _text() flattens to "£795. 99"."""
    assert parse_price("£795. 99") == Decimal("795.99")
    assert parse_price("£1,579. 99") == Decimal("1579.99")
    assert parse_price("£795.99") == Decimal("795.99")
    assert parse_price("£795") == Decimal("795")


@pytest.mark.asyncio
async def test_ccl_reports_recovery_failure(monkeypatch) -> None:
    """A failed recovery attempt remains observable as a bounded timeout."""

    async def request_html(_self, _url: str) -> str:
        raise httpx.ReadTimeout("challenge timed out")

    monkeypatch.setattr(FlareSolverrClient, "request_html", request_html)
    connector = CclConnector(flaresolverr_url="http://solverr.test/v1")

    with pytest.raises(ConnectorDegradedError) as exc_info:
        await connector.search("RTX 5090")

    error = exc_info.value
    assert error.status is ConnectorStatus.timeout
    assert error.connector_id == "ccl"
    assert "timed out" in error.message
    assert error.detail is not None
    assert error.detail["endpoint"] == "http://solverr.test/v1"
    assert error.detail["url"] == "https://www.cclonline.com/search?query=RTX+5090"
    await connector.cleanup()


@pytest.mark.asyncio
async def test_ccl_initialize_and_cleanup() -> None:
    """CCL initializes and releases its connector HTTP client."""
    connector = CclConnector()
    await connector.initialize()
    await connector.cleanup()
