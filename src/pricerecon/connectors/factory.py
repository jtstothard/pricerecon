"""Connector factory with config validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# These fields describe whether a source participates in a watch, rather than
# how its connector should be constructed.  They can be present in persisted
# source/config-file records and must not leak into arbitrary connector
# constructors (which intentionally have connector-specific signatures).
OPERATIONAL_CONNECTOR_CONFIG_KEYS = frozenset({"enabled"})


@dataclass(slots=True)
class ConnectorConfigError(Exception):
    """Raised when connector configuration is invalid or missing."""

    connector_id: str
    message: str

    def __str__(self) -> str:
        return self.message


def validate_and_create_connector(
    connector_class: type,
    connector_id: str,
    connector_kwargs: dict[str, Any],
) -> Any:
    """Validate connector config and create an instance.

    Inspects the connector's __init__ signature and validates that all
    required parameters are provided. Raises ConnectorConfigError with a
    helpful message if validation fails.

    This replaces the broad TypeError catch as a config fallback.
    """
    import inspect

    # Source metadata is merged with connector settings by the watch executor.
    # Strip it at this generic boundary so every connector gets the same
    # protection, including strict constructors and **kwargs constructors.
    constructor_kwargs = {
        key: value
        for key, value in connector_kwargs.items()
        if key not in OPERATIONAL_CONNECTOR_CONFIG_KEYS
    }

    # If the class doesn't define its own __init__ (inherits object.__init__),
    # it accepts no constructor arguments — create the instance directly.
    # Use getattr on the type to satisfy mypy (direct .__init__ access is unsound).
    if getattr(connector_class, "__init__", None) is object.__init__:
        return connector_class()

    try:
        sig = inspect.signature(connector_class.__init__)  # type: ignore[misc]
    except Exception:
        # Can't inspect signature - just try to create the instance
        return connector_class(**constructor_kwargs)

    required_params = []
    optional_params = []

    for name, param in sig.parameters.items():
        if name == "self":
            continue
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            # Skip *args and **kwargs - they accept anything
            continue
        if param.default == inspect.Parameter.empty:
            required_params.append(name)
        else:
            optional_params.append(name)

    # Check required parameters
    missing_params = [p for p in required_params if p not in constructor_kwargs]
    if missing_params:
        raise ConnectorConfigError(
            connector_id=connector_id,
            message=f"Connector '{connector_id}' missing required config parameters: {', '.join(missing_params)}. "
            f"Required: {', '.join(required_params)}. Provided: {', '.join(constructor_kwargs.keys()) or 'none'}",
        )

    # Create instance with validated config
    return connector_class(**constructor_kwargs)
