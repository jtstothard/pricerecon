"""CCL connector tests for truthful degraded-state behavior."""

import pytest

from pricerecon.connectors.ccl import CclConnector
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus


@pytest.mark.asyncio
async def test_ccl_raises_truthful_error_on_cloudflare_block() -> None:
    """CCL raises ConnectorDegradedError with bot_blocked status when searched."""
    connector = CclConnector()

    with pytest.raises(ConnectorDegradedError) as exc_info:
        await connector.search("RTX 5090")

    error = exc_info.value
    assert error.status is ConnectorStatus.bot_blocked
    assert error.connector_id == "ccl"
    assert "Cloudflare" in error.message
    assert error.detail is not None
    assert "Cloudflare" in error.detail["root_cause"]
    assert "***REMOVED***" in error.detail["diagnosis_task"]
    assert error.detail["url"] == "https://www.cclonline.com"
    assert "Byparr" in error.detail["evidence"]


@pytest.mark.asyncio
async def test_ccl_initialize_and_cleanup_are_noops() -> None:
    """CCL initialize and cleanup are no-ops (no persistent resources)."""
    connector = CclConnector()
    await connector.initialize()
    await connector.cleanup()
