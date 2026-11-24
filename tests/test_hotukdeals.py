"""Tests for the RSS-backed HotUKDeals connector."""

from pathlib import Path
from typing import Any

import pytest

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


@pytest.mark.asyncio
async def test_watch_acquisition_constructs_registered_rss_connector(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The watch executor must build the registered RSS connector as-is.

    Regression: acquisition kept a HotUKDeals branch from the retired Phase 2
    Camofox/template stub that passed ``config=`` and ``browser_client=``.
    The RSS connector rejects both, so every HotUKDeals watch failed with
    ``unknown_error: ... unexpected keyword argument 'config'`` (seen live on
    the deployed service's source health).
    """
    from pricerecon.core.acquisition import acquire_sources
    from pricerecon.models.watches import SourceConfig

    monkeypatch.setenv("CAMOFOX_URL", "http://camofox.test:9377")
    monkeypatch.setattr(
        "pricerecon.core.acquisition.load_config", lambda *args, **kwargs: {"connectors": {}}
    )
    monkeypatch.setattr(
        "pricerecon.core.connector_health.list_connector_health", lambda path=None: {}
    )
    monkeypatch.setattr(
        "pricerecon.core.collection_policy.current_policy", lambda connection=None: None
    )
    recorded: list[tuple[str, str, str | None]] = []
    monkeypatch.setattr(
        "pricerecon.core.acquisition.upsert_connector_health",
        lambda connector_id, status, last_error=None, details=None, **_kw: recorded.append(
            (connector_id, status, last_error)
        ),
    )

    class FixtureHotUKDeals(HotUKDealsConnector):
        def __init__(self, cache_path: str | Path | None = None) -> None:
            super().__init__(cache_path=cache_path or tmp_path / "hotukdeals.json")

        async def search(self, query: str, filters: dict[str, Any] | None = None) -> list[Any]:
            return []

    monkeypatch.setattr(
        "pricerecon.connectors.discover_connectors", lambda: {"hotukdeals": FixtureHotUKDeals}
    )

    result = await acquire_sources(
        [SourceConfig(connector="hotukdeals", config={})],
        query="RTX 5070",
        source_queries={},
        filters={},
        context_id="hotukdeals-construction",
    )

    assert recorded == [("hotukdeals", "ok", None)]
    assert [(o.source, o.state) for o in result.outcomes] == [("hotukdeals", "success_empty")]
