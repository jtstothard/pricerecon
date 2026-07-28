"""Tests for the RSS-backed HotUKDeals connector."""

from pricerecon.connectors.reddit import HotUKDealsConnector
from pricerecon.models import SourceType


def test_source_role() -> None:
    """Test connector is a deal signal source."""
    connector = HotUKDealsConnector()
    assert connector.source_role == SourceType.SIGNAL


def test_connector_id() -> None:
    """Test connector ID."""
    connector = HotUKDealsConnector()
    assert connector.connector_id == "hotukdeals"


def test_connector_uses_rss_implementation_not_phase_two_template() -> None:
    """The supported connector must use the canonical RSS feed path."""
    connector = HotUKDealsConnector()
    assert connector.template.endpoint_url == "https://www.hotukdeals.com/rss/new"
    assert not hasattr(connector, "template_name")
