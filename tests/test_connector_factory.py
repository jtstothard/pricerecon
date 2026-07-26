"""Regression tests for generic connector construction."""

from typing import Any

from pricerecon.connectors.factory import validate_and_create_connector


def test_operational_source_metadata_is_not_passed_to_strict_constructor() -> None:
    received: dict[str, Any] = {}

    class StrictConnector:
        def __init__(self, config: dict[str, Any] | None = None) -> None:
            received["config"] = config

    connector = validate_and_create_connector(
        StrictConnector,
        "amazon_uk",
        {"enabled": True, "config": {"impersonate": "chrome124"}},
    )

    assert isinstance(connector, StrictConnector)
    assert received == {"config": {"impersonate": "chrome124"}}


def test_connector_specific_settings_are_preserved() -> None:
    received: dict[str, Any] = {}

    class StrictConnector:
        def __init__(self, app_id: str, cert_id: str | None = None) -> None:
            received.update(app_id=app_id, cert_id=cert_id)

    validate_and_create_connector(
        StrictConnector,
        "ebay",
        {"enabled": False, "app_id": "app", "cert_id": "cert"},
    )

    assert received == {"app_id": "app", "cert_id": "cert"}