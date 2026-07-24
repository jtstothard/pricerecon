"""Regression tests for WAF-blocked retailer fail-fast behavior."""

import pytest

from pricerecon.connectors.box import BoxConnector
from pricerecon.connectors.currys import CurrysConnector
from pricerecon.connectors.overclockers import OverclockersConnector
from pricerecon.connectors.scan import ScanConnector
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus


@pytest.mark.parametrize(
    "connector_class, connector_id",
    [
        (ScanConnector, "scan"),
        (OverclockersConnector, "overclockers"),
        (BoxConnector, "box"),
        (CurrysConnector, "currys"),
    ],
)
@pytest.mark.asyncio
async def test_waf_blocked_retailers_fail_fast_with_truthful_status(
    connector_class: type, connector_id: str
) -> None:
    connector = connector_class()

    with pytest.raises(ConnectorDegradedError) as raised:
        await connector.search("RTX 5090")

    error = raised.value
    assert error.status is ConnectorStatus.bot_blocked
    assert error.connector_id == connector_id
    assert "WAF" in error.message
    assert error.detail is not None
    assert error.detail["url"].startswith("https://")


@pytest.mark.asyncio
async def test_waf_blocked_retailer_initialize_and_cleanup_are_noops() -> None:
    connector = ScanConnector()
    await connector.initialize()
    await connector.cleanup()
