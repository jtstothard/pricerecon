"""Box connector tests for truthful degraded-state behavior."""

import pytest
import yaml

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
    assert "Cloudflare" in error.detail["evidence"]
    assert "no product cards" in error.detail["evidence"]
    assert error.detail["diagnosis_task"] == "endpoint-drift-2026-07-28"
    assert error.detail["url"] == "https://www.box.co.uk"


@pytest.mark.asyncio
async def test_box_initialize_and_cleanup_are_noops() -> None:
    """Box initialize and cleanup are no-ops (no persistent resources)."""
    connector = BoxConnector()
    await connector.initialize()
    await connector.cleanup()


def test_box_template_preserves_disabled_endpoint_disposition() -> None:
    """The unverified 404 route is not advertised as a working connector."""
    with open("src/pricerecon/connectors/templates/box.yml", encoding="utf-8") as template_file:
        template = yaml.safe_load(template_file)

    assert template["disabled"] is True
    assert "404" in template["disabled_reason"]
    assert "alternate" in template["disabled_reason"]
