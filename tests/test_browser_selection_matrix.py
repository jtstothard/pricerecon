from __future__ import annotations

from pricerecon.connectors.browser_client import BrowserBackendConfig
from pricerecon.core.browser_selection_matrix import FailureCategory, ProbeResult, run_case

CONFIG = {
    "browser_backends": {
        "primary": {"type": "camofox", "endpoint": "https://primary.invalid"},
        "backup": {"type": "camofox", "endpoint": "https://backup.invalid"},
    },
    "browser_default": ["primary", "backup"],
}


def test_retailer_override_wins_and_retry_is_limited_to_retryable() -> None:
    seen: list[str] = []

    def probe(backend: BrowserBackendConfig) -> ProbeResult:
        seen.append(backend.name)
        return ProbeResult(parsed_listing_count=2, elapsed_ms=7)

    rows = run_case(
        retailer="Acme",
        connector="html",
        runtime_config=CONFIG,
        connector_config={"browser_backend": "backup"},
        probe=probe,
    )
    assert seen == ["backup"]
    assert rows[0].selected_backend == "backup"
    assert rows[0].configured_selection == "backup"


def test_ordered_fallback_only_on_documented_retryable_failure() -> None:
    seen: list[str] = []

    def probe(backend: BrowserBackendConfig) -> ProbeResult:
        seen.append(backend.name)
        if backend.name == "primary":
            return ProbeResult(
                page_outcome="blocked", failure=FailureCategory.BLOCKED, elapsed_ms=10
            )
        return ProbeResult(parsed_listing_count=1, elapsed_ms=12)

    rows = run_case(
        retailer="Acme", connector="html", runtime_config=CONFIG, connector_config=None, probe=probe
    )
    assert seen == ["primary", "backup"]
    assert [r.failure_category for r in rows] == ["blocked", "none"]
    assert rows[1].fell_through is True


def test_malformed_response_does_not_fall_through() -> None:
    seen: list[str] = []

    def probe(backend: BrowserBackendConfig) -> ProbeResult:
        seen.append(backend.name)
        return ProbeResult(page_outcome="malformed", failure=FailureCategory.MALFORMED_RESPONSE)

    rows = run_case(
        retailer="Acme", connector="html", runtime_config=CONFIG, connector_config=None, probe=probe
    )
    assert seen == ["primary"]
    assert rows[0].failure_category == "malformed_response"


def test_unconfigured_connector_is_explicitly_reported() -> None:
    rows = run_case(
        retailer="Acme",
        connector="html",
        runtime_config={"browser_backends": CONFIG["browser_backends"]},
        connector_config=None,
        probe=lambda _: ProbeResult(),
    )
    assert rows[0].selected_backend is None
    assert rows[0].failure_category == "backend_unavailable"
