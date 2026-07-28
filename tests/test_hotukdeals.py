"""Tests for HotUKDeals connector."""

import pytest
from pricerecon.connectors.hotukdeals import HotUKDealsConnector
from pricerecon.models import SourceType


@pytest.fixture
def connector() -> HotUKDealsConnector:
    """Create connector instance."""
    instance = HotUKDealsConnector()
    # Keep parser tests focused on fixture parsing; the production template is
    # disabled because the live upstream currently serves a Cloudflare page.
    instance.template.disabled = False
    return instance


def test_source_role(connector: HotUKDealsConnector) -> None:
    """Test connector is a deal signal source."""
    assert connector.source_role == SourceType.SIGNAL


def test_connector_id(connector: HotUKDealsConnector) -> None:
    """Test connector ID."""
    assert connector.connector_id == "hotukdeals"
