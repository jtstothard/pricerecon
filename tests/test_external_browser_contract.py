from __future__ import annotations

from collections.abc import AsyncIterator

from pricerecon.connectors.external_browser_contract import (
    AdapterOutcome,
    BackendSelection,
    BrowserBackend,
    BrowserCapability,
    BrowserSession,
    EmptyResult,
    FatalError,
    InterceptedResponse,
    RawInterceptedResponse,
    RawRenderedContent,
    RenderedResponse,
    RetryableError,
)


class ExampleBackend:
    name = "example"

    async def start_session(self, *, timeout_ms: int) -> BrowserSession:
        return BrowserSession("session-1")

    async def navigate(self, session: BrowserSession, url: str, *, timeout_ms: int) -> str:
        return "https://example.test/final"

    def intercept_responses(
        self, session: BrowserSession
    ) -> AsyncIterator[RawInterceptedResponse] | None:
        return None

    async def rendered_content(self, session: BrowserSession) -> RawRenderedContent:
        return RawRenderedContent("<main>result</main>", "https://example.test/final")

    async def cleanup(self, session: BrowserSession) -> None:
        return None


def test_example_backend_implements_contract() -> None:
    assert isinstance(ExampleBackend(), BrowserBackend)


def test_response_variants_are_discriminated_and_truthful() -> None:
    selection = BackendSelection(("example",), "example")
    intercepted = InterceptedResponse(
        status_code=200,
        headers={"content-type": "application/json"},
        body=b"{}",
        final_url="https://example.test/api",
        selection=selection,
    )
    rendered = RenderedResponse(
        content="<main>result</main>",
        final_url="https://example.test/final",
        selection=selection,
    )

    assert intercepted.kind == "intercepted"
    assert intercepted.capability is BrowserCapability.INTERCEPTED_RESPONSE
    assert rendered.kind == "rendered"
    assert rendered.capability is BrowserCapability.RENDERED_CONTENT
    assert not hasattr(rendered, "status_code")
    assert not hasattr(rendered, "headers")


def test_degraded_and_fallback_errors_retain_diagnostics() -> None:
    selection = BackendSelection(("primary", "backup"), "backup")
    result: AdapterOutcome = EmptyResult("no browser evidence", "backup", selection)
    retryable = RetryableError("connection refused", backend_name="primary")
    fatal = FatalError("retailer rejected request", backend_name="primary")

    assert result.kind == "empty_result"
    assert result.backend_name == "backup"
    assert retryable.reason == "connection refused"
    assert fatal.backend_name == "primary"
