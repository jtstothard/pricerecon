"""Connectors package."""

from pricerecon.connectors.base import BaseConnector

__all__ = ["BaseConnector", "discover_connectors"]


def discover_connectors() -> dict[str, type[BaseConnector]]:
    """Discover all connectors via entry points, with source-tree fallback.

    Returns:
        Dict of connector_id -> connector class
    """
    import importlib
    import importlib.metadata

    connectors: dict[str, type[BaseConnector]] = {}

    for ep in importlib.metadata.entry_points(group="pricerecon.connectors"):
        try:
            connector_class = ep.load()
            if isinstance(connector_class, type) and issubclass(connector_class, BaseConnector):
                connectors[ep.name] = connector_class
        except Exception as e:
            print(f"Failed to load connector {ep.name}: {e}")

    if connectors:
        return connectors

    fallback_modules = [
        "aliexpress",
        "ebay",
        "amazon",
        "cex",
        "scan",
        "overclockers",
        "box",
        "currys",
        "ebuyer",
        "ccl",
        "novatech",
        "aria",
        "shopify",
        "fb_marketplace",
        "johnlewis",
        "dell_uk",
        "reddit",
        "hotukdeals",
    ]

    for module_name in fallback_modules:
        try:
            module = importlib.import_module(f"pricerecon.connectors.{module_name}")
        except Exception:
            continue
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, BaseConnector) and attr is not BaseConnector:
                connector_id = getattr(attr, "CONNECTOR_ID", None) or attr_name.lower().replace("connector", "")
                connectors[str(connector_id)] = attr

    return connectors
