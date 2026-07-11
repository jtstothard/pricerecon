"""Connectors package."""

from pricerecon.connectors.base import BaseConnector

__all__ = ["BaseConnector", "discover_connectors"]


def discover_connectors() -> dict[str, type[BaseConnector]]:
    """Discover all connectors via entry points.

    Returns:
        Dict of connector_id -> connector class
    """
    import importlib.metadata

    connectors: dict[str, type[BaseConnector]] = {}

    for ep in importlib.metadata.entry_points(group="pricerecon.connectors"):
        try:
            connector_class = ep.load()
            if isinstance(connector_class, type) and issubclass(
                connector_class, BaseConnector
            ):
                connectors[ep.name] = connector_class
        except Exception as e:
            print(f"Failed to load connector {ep.name}: {e}")

    return connectors