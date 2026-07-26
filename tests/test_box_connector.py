"""Box connector tests for truthful degraded-state behavior."""

import pytest

from pricerecon.connectors.box import BoxConnector
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus


@pytest.mark.asyncio
async def test_box_raises_truthful_error_on_cloudflare_block() -> None:
    """Box raises ConnectorDegradedError with bot_blocked status when searched."""
    connector = BoxConnector()

    with pytest.raises(ConnectorDegradedError) as exc_info:
        await connector.search("RTX 3080")

    error = exc_info.value
    assert error.status is ConnectorStatus.bot_blocked
    assert error.connector_id == "box"
    assert "WAF" in error.message
    assert error.detail is not None
    assert "Cloudflare" in error.detail["root_cause"]
    assert "***REMOVED***" in error.detail["diagnosis_task"]
    assert error.detail["url"] == "https://www.box.co.uk"


@pytest.mark.asyncio
async def test_box_initialize_and_cleanup_are_noops() -> None:
    """Box initialize and cleanup are no-ops (no persistent resources)."""
    connector = BoxConnector()
    await connector.initialize()
    await connector.cleanup()
