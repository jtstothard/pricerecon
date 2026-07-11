"""Connectors package."""

from __future__ import annotations

from pricerecon.connectors.base import BaseConnector

__all__ = ["BaseConnector", "discover_connectors"]


def _builtin_connectors() -> dict[str, type[BaseConnector]]:
    """Return the connector inventory shipped in this source tree."""

    from pricerecon.connectors.amazon import AmazonConnector
    from pricerecon.connectors.aria import AriaConnector
    from pricerecon.connectors.box import BoxConnector
    from pricerecon.connectors.ccl import CclConnector
    from pricerecon.connectors.cex import CexConnector
    from pricerecon.connectors.currys import CurrysConnector
    from pricerecon.connectors.ebay import eBayConnector
    from pricerecon.connectors.ebuyer import EbuyerConnector
    from pricerecon.connectors.fb_marketplace import FacebookMarketplaceConnector
    from pricerecon.connectors.novatech import NovatechConnector
    from pricerecon.connectors.overclockers import OverclockersConnector
    from pricerecon.connectors.reddit import (
        HotUKDealsConnector,
        RedditBapcSalesUKConnector,
        RedditHardwareSwapUKConnector,
    )
    from pricerecon.connectors.scan import ScanConnector
    from pricerecon.connectors.shopify import ShopifyConnector

    return {
        "amazon_uk": AmazonConnector,
        "aria": AriaConnector,
        "box": BoxConnector,
        "ccl": CclConnector,
        "cex": CexConnector,
        "currys": CurrysConnector,
        "ebay": eBayConnector,
        "ebuyer": EbuyerConnector,
        "facebook_marketplace": FacebookMarketplaceConnector,
        "hotukdeals": HotUKDealsConnector,
        "novatech": NovatechConnector,
        "overclockers": OverclockersConnector,
        "reddit_bapcsalesuk": RedditBapcSalesUKConnector,
        "reddit_hardwareswapuk": RedditHardwareSwapUKConnector,
        "scan": ScanConnector,
        "shopify": ShopifyConnector,
    }


def discover_connectors() -> dict[str, type[BaseConnector]]:
    """Discover all connectors via built-in registry plus entry points.

    Returns:
        Dict of connector_id -> connector class.
    """
    import importlib.metadata

    connectors = _builtin_connectors()

    try:
        entry_points = importlib.metadata.entry_points(group="pricerecon.connectors")
    except TypeError:
        entry_points = importlib.metadata.entry_points().select(group="pricerecon.connectors")

    for ep in entry_points:
        try:
            connector_class = ep.load()
            if isinstance(connector_class, type) and issubclass(connector_class, BaseConnector):
                connectors.setdefault(ep.name, connector_class)
        except Exception as exc:
            print(f"Failed to load connector {ep.name}: {exc}")

    return connectors