from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest

from pricerecon.connectors.dell_uk import DellUKConnector
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus


FIXTURE = Path(__file__).parent / "fixtures" / "dell_uk" / "access_denied.html"
BY_PARR_FIXTURE = Path(__file__).parent / "fixtures" / "dell_uk" / "XPS_byparr.html"
CAMOFOX_FIXTURE = Path(__file__).parent / "fixtures" / "dell_uk" / "XPS_camofox.snapshot"


@pytest.mark.asyncio
async def test_dell_uk_reports_upstream_access_denied_instead_of_parse_error() -> None:
    html = FIXTURE.read_text()

    class DummyPage:
        async def goto(self, url: Any, wait_until: Any = None, timeout: Any = None) -> None:
            return None

        async def wait_for_timeout(self, ms: Any) -> None:
            return None

        async def content(self) -> str:
            return html

    class DummyContext:
        async def new_page(self) -> DummyPage:
            return DummyPage()

        async def close(self) -> None:
            return None

    class DummyBrowserClient:
        async def new_context(self) -> DummyContext:
            return DummyContext()

    connector = DellUKConnector(browser_client=cast(Any, DummyBrowserClient()))
    with pytest.raises(ConnectorDegradedError) as exc_info:
        await connector.search("XPS")

    error = exc_info.value
    assert error.status is ConnectorStatus.bot_blocked
    assert "Access Denied" in error.message
    assert error.detail == {"url": "https://www.dell.com/en-uk/search/laptops?text=XPS"}


def test_dell_uk_byparr_html_fixture_parses_products() -> None:
    connector = DellUKConnector()
    listings = connector._parse_listings(
        BY_PARR_FIXTURE.read_text(), "XPS", "https://www.dell.com/en-uk/search/laptops?text=XPS"
    )

    assert len(listings) == 12
    assert listings[0].title_raw == "Dell 16 Laptop"
    assert listings[0].price == Decimal("628.99")
    assert listings[0].source_listing_id == "cndc1625602"


@pytest.mark.asyncio
async def test_dell_uk_uses_flaresolverr_html_route(monkeypatch: pytest.MonkeyPatch) -> None:
    html = BY_PARR_FIXTURE.read_text()
    calls: list[str] = []

    async def request_html(self: Any, url: str, *, max_timeout: int = 60000) -> str:
        calls.append(url)
        return html

    monkeypatch.setattr("pricerecon.connectors.dell_uk.FlareSolverrClient.request_html", request_html)
    connector = DellUKConnector(flaresolverr_url="http://byparr.test/v1")
    listings = await connector.search("XPS")

    assert len(listings) == 12
    assert calls == ["https://www.dell.com/en-uk/search/laptops?text=XPS"]

def test_dell_uk_does_not_parse_camofox_snapshot_as_html() -> None:
    connector = DellUKConnector()
    assert connector._parse_listings(
        CAMOFOX_FIXTURE.read_text(), "XPS", "https://www.dell.com/en-uk/search/laptops?text=XPS"
    ) == []
