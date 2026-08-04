from __future__ import annotations

import pytest

from pricerecon.connectors.browser_client import (
    BrowserBackendConfigError,
    BrowserBackendRegistry,
    resolve_browser_backends,
)

BACKENDS = {
    "primary": {
        "type": "camofox",
        "endpoint": "https://browser-a.example/api",
        "options": {"api_key": "secret"},
    },
    "backup": {"type": "camofox", "endpoint": "https://browser-b.example/api"},
}


def test_named_backends_validate_and_public_view_excludes_options() -> None:
    registry = BrowserBackendRegistry.from_mapping(BACKENDS)
    assert [b.name for b in registry.select("primary")] == ["primary"]
    assert registry.public() == {
        "primary": {"type": "camofox", "endpoint": "https://browser-a.example/api"},
        "backup": {"type": "camofox", "endpoint": "https://browser-b.example/api"},
    }
    assert "secret" not in repr(registry.select("primary")[0])


def test_ordered_selection_and_retailer_precedence() -> None:
    config = {"browser_backends": BACKENDS, "browser_default": ["backup", "primary"]}
    selected = resolve_browser_backends(config, {"browser_backend": ["primary", "backup"]})
    assert [backend.name for backend in selected] == ["primary", "backup"]
    assert [backend.name for backend in resolve_browser_backends(config)] == ["backup", "primary"]


@pytest.mark.parametrize(
    "raw, message",
    [
        ({"x": {"type": "camofox"}}, "missing endpoint"),
        ({"x": {"type": "local", "endpoint": "http://x"}}, "unsupported type"),
        ({"x": "http://x"}, "must be a mapping"),
    ],
)
def test_invalid_backend_is_actionable(raw: object, message: str) -> None:
    with pytest.raises(BrowserBackendConfigError, match=message):
        BrowserBackendRegistry.from_mapping(raw)  # type: ignore[arg-type]


def test_unknown_or_malformed_selection_fails_closed() -> None:
    registry = BrowserBackendRegistry.from_mapping(BACKENDS)
    with pytest.raises(BrowserBackendConfigError, match="unknown browser backend"):
        registry.select("missing")
    with pytest.raises(BrowserBackendConfigError, match="non-empty list"):
        registry.select([])


@pytest.mark.parametrize("selection", [1, True, {"primary": 1}, ["primary", ["backup"]]])
def test_non_list_selection_shapes_fail_with_actionable_error(selection: object) -> None:
    registry = BrowserBackendRegistry.from_mapping(BACKENDS)
    with pytest.raises(BrowserBackendConfigError, match="string or list/tuple of strings"):
        registry.select(selection)  # type: ignore[arg-type]


def test_endpoint_userinfo_is_redacted_from_diagnostics() -> None:
    registry = BrowserBackendRegistry.from_mapping(
        {"primary": {"type": "camofox", "endpoint": "https://user:password@browser.example/api"}}
    )
    assert registry.public()["primary"]["endpoint"] == "https://browser.example/api"
    assert "password" not in repr(registry.select("primary")[0])


@pytest.mark.parametrize(
    "endpoint",
    ["not-a-url", "/tmp/browser", "https:///missing-host", "http://"],
)
def test_malformed_endpoint_fails_closed(endpoint: str) -> None:
    with pytest.raises(BrowserBackendConfigError, match="valid URL"):
        BrowserBackendRegistry.from_mapping({"x": {"type": "camofox", "endpoint": endpoint}})
