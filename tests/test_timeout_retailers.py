"""Regression tests for WAF-blocked retailer fail-fast behavior."""

import pytest

from pricerecon.connectors.box import BoxConnector
from pricerecon.connectors.overclockers import OverclockersConnector
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus


@pytest.mark.parametrize(
    "connector_class, connector_id",
    [
        (OverclockersConnector, "overclockers"),
        (BoxConnector, "box"),
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
async def test_overclockers_reports_captured_turnstile_diagnosis() -> None:
    connector = OverclockersConnector()

    with pytest.raises(ConnectorDegradedError) as raised:
        await connector.search("RTX 3080")

    error = raised.value
    assert "Cloudflare Turnstile" in error.message
    assert error.detail is not None
    assert error.detail["diagnosis_task"] == "TASK-XXXX"
    assert "Playwright" in error.detail["evidence"]
    assert "Camofox" in error.detail["evidence"]


@pytest.mark.asyncio
async def test_waf_blocked_retailer_initialize_and_cleanup_are_noops() -> None:
    connector = OverclockersConnector()
    await connector.initialize()
    await connector.cleanup()
