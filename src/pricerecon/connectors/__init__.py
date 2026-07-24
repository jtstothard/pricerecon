"""Connectors package with enabled source discovery."""

from __future__ import annotations

import sqlite3
from typing import Any

from pricerecon.connectors.base import BaseConnector
from pricerecon.db.schema import DB_PATH

__all__ = ["BaseConnector", "discover_connectors", "get_enabled_connectors"]


# Historical source rows used ``john_lewis`` before the connector was
# registered under its canonical id.  Keep the alias in one place so database
# migrations and runtime callers agree on the identifier that the registry
# exposes.
CONNECTOR_ID_ALIASES = {"john_lewis": "johnlewis"}


def canonical_connector_id(connector_id: str) -> str:
    """Return the registry id for a legacy or canonical connector id."""
    return CONNECTOR_ID_ALIASES.get(connector_id, connector_id)


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
        "camelcamelcamel",
        "costco_uk",
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
        "google_shopping",
        "laptopsdirect",
        "argos",
        "musicmagpie",
        "vinted",
        "gumtree",
    ]

    for module_name in fallback_modules:
        try:
            module = importlib.import_module(f"pricerecon.connectors.{module_name}")
        except Exception:
            continue
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseConnector)
                and attr is not BaseConnector
            ):
                connector_id = getattr(attr, "CONNECTOR_ID", None) or attr_name.lower().replace(
                    "connector",
                    "",
                )
                connectors[str(connector_id)] = attr

    return connectors


def get_enabled_connectors() -> list[dict[str, Any]]:
    """Get all enabled connector sources from the database.

    Returns:
        List of dicts with connector_id, config, and connector_class for each enabled source
    """
    import json

    # Get all connectors first
    connectors = discover_connectors()

    # Query enabled sources from database
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT connector_id, config_json FROM sources WHERE enabled = 1")
    rows = cursor.fetchall()

    enabled_sources = []
    for row in rows:
        connector_id = row["connector_id"]
        config = json.loads(row["config_json"])

        # Get the connector class
        connector_class = connectors.get(connector_id)
        if connector_class is None:
            print(f"Warning: connector class not found for {connector_id}")
            continue

        enabled_sources.append(
            {
                "connector_id": connector_id,
                "config": config,
                "connector_class": connector_class,
            }
        )

    conn.close()
    return enabled_sources
