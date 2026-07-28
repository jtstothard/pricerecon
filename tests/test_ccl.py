"""CCL connector tests for Cloudflare challenge recovery and failure handling."""

import httpx
import pytest

from pricerecon.connectors.ccl import CclConnector
from pricerecon.connectors.flaresolverr import FlareSolverrClient
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus


@pytest.mark.asyncio
async def test_ccl_recovers_through_flaresolverr(monkeypatch) -> None:
    """CCL uses the challenge-recovery lane and parses the returned HTML."""

    async def request_html(_self, url: str) -> str:
        assert url == "https://www.cclonline.com/search/RTX+5090"
        return """
        <article class="product">
          <a href="/product/test"><h3>RTX 5090 Test</h3></a>
          <span class="price">£1,999.99</span>
        </article>
        """

    monkeypatch.setattr(FlareSolverrClient, "request_html", request_html)
    connector = CclConnector(flaresolverr_url="http://solverr.test/v1")

    listings = await connector.search("RTX 5090")

    assert listings
    assert any(listing.source == "ccl" for listing in listings)
    assert any(listing.price is not None for listing in listings)
    await connector.cleanup()


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
    assert error.detail["url"] == "https://www.cclonline.com/search/RTX+5090"
    await connector.cleanup()


@pytest.mark.asyncio
async def test_ccl_initialize_and_cleanup() -> None:
    """CCL initializes and releases its connector HTTP client."""
    connector = CclConnector()
    await connector.initialize()
    await connector.cleanup()
