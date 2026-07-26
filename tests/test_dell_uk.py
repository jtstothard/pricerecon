from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from pricerecon.connectors.dell_uk import DellUKConnector
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus


FIXTURE = Path(__file__).parent / "fixtures" / "dell_uk" / "access_denied.html"


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
