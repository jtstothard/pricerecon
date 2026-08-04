"""Type-level contract shared by PriceRecon external-browser backends.

This module deliberately contains no HTTP or browser implementation.  It is the
boundary between a vendor-specific browser backend and connectors: all browser
output is either a truthful ``AdapterResponse`` or a typed ``DegradedResult``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal, Protocol, TypeAlias, runtime_checkable


class BrowserCapability(StrEnum):
    """The evidence capability actually exercised for one adapter response."""

    INTERCEPTED_RESPONSE = "intercepted_response"
    RENDERED_CONTENT = "rendered_content"


@dataclass(frozen=True, slots=True)
class BrowserSession:
    """Opaque session handle returned by a backend's ``start_session`` call.

    ``id`` is only an adapter correlation value. Backends must not put secrets
    in it because degraded-result diagnostics may retain it.
    """

    id: str


@dataclass(frozen=True, slots=True)
class RawInterceptedResponse:
    """Backend-native intercepted response before adapter redaction/bounding."""

    status_code: int
    headers: Mapping[str, str]
    body: bytes | str
    final_url: str


@dataclass(frozen=True, slots=True)
class RawRenderedContent:
    """Backend-native rendered DOM or accessibility snapshot before normalization."""

    content: str
    final_url: str


@runtime_checkable
class BrowserBackend(Protocol):
    """Interface every external browser backend must implement.

    ``intercept_responses`` is optional at the capability level: a
    rendered-only backend returns ``None``. It must never synthesize an HTTP
    response from DOM content. All sessions started by ``start_session`` must
    be passed to ``cleanup`` by the caller, including error paths.
    """

    name: str

    async def start_session(self, *, timeout_ms: int) -> BrowserSession:
        """Create and return one browser session, or raise a typed adapter error."""
        ...

    async def navigate(self, session: BrowserSession, url: str, *, timeout_ms: int) -> str:
        """Navigate the session and return the final URL after redirects."""
        ...

    def intercept_responses(
        self, session: BrowserSession
    ) -> AsyncIterator[RawInterceptedResponse] | None:
        """Return intercepted network responses, or ``None`` when unsupported."""
        ...

    async def rendered_content(self, session: BrowserSession) -> RawRenderedContent:
        """Return rendered DOM/snapshot evidence when the backend provides it."""
        ...

    async def cleanup(self, session: BrowserSession) -> None:
        """Close the session and release all backend resources; safe after failures."""
        ...


@dataclass(frozen=True, slots=True)
class BackendFailure:
    """A failed backend attempt retained when an ordered fallback is used."""

    backend_name: str
    reason: str


@dataclass(frozen=True, slots=True)
class BackendSelection:
    """Configured backend selection and truthful record of earlier failed attempts."""

    configured_backends: tuple[str, ...]
    selected_backend: str
    fallback_failures: tuple[BackendFailure, ...] = ()


@dataclass(frozen=True, slots=True)
class InterceptedResponse:
    """A normalized, bounded HTTP response observed through interception.

    ``headers`` must already be redacted and ``body`` must already respect the
    adapter's configured byte limit. ``body_truncated`` preserves that fact for
    downstream consumers rather than making a partial body look complete.
    """

    kind: Literal["intercepted"] = "intercepted"
    capability: Literal[BrowserCapability.INTERCEPTED_RESPONSE] = (
        BrowserCapability.INTERCEPTED_RESPONSE
    )
    status_code: int = 0
    headers: Mapping[str, str] = field(default_factory=dict)
    body: bytes | str = b""
    body_truncated: bool = False
    final_url: str = ""
    selection: BackendSelection | None = None


@dataclass(frozen=True, slots=True)
class RenderedResponse:
    """A normalized rendered DOM or snapshot, not an intercepted HTTP response.

    It intentionally has no status code or headers: rendered-only backends must
    not manufacture network evidence they did not exercise.
    """

    kind: Literal["rendered"] = "rendered"
    capability: Literal[BrowserCapability.RENDERED_CONTENT] = BrowserCapability.RENDERED_CONTENT
    content: str = ""
    final_url: str = ""
    selection: BackendSelection | None = None


AdapterResponse: TypeAlias = InterceptedResponse | RenderedResponse


@dataclass(frozen=True, slots=True)
class _DegradedResultBase:
    """Common diagnostic fields on a non-successful adapter outcome."""

    reason: str
    backend_name: str
    selection: BackendSelection | None = None


@dataclass(frozen=True, slots=True)
class EmptyResult(_DegradedResultBase):
    """The backend completed but yielded neither usable network nor rendered evidence."""

    kind: Literal["empty_result"] = "empty_result"


@dataclass(frozen=True, slots=True)
class BlockedResponse(_DegradedResultBase):
    """The retailer or backend returned an anti-bot, challenge, or access-denied response."""

    kind: Literal["blocked_response"] = "blocked_response"


@dataclass(frozen=True, slots=True)
class Timeout(_DegradedResultBase):
    """A navigation or total session deadline elapsed before usable evidence arrived."""

    kind: Literal["timeout"] = "timeout"


@dataclass(frozen=True, slots=True)
class MalformedResponse(_DegradedResultBase):
    """The backend returned an unparseable or contract-invalid payload."""

    kind: Literal["malformed_response"] = "malformed_response"


@dataclass(frozen=True, slots=True)
class BackendOutage(_DegradedResultBase):
    """The configured browser backend could not be reached or crashed."""

    kind: Literal["backend_outage"] = "backend_outage"


DegradedResult: TypeAlias = (
    EmptyResult | BlockedResponse | Timeout | MalformedResponse | BackendOutage
)
AdapterOutcome: TypeAlias = AdapterResponse | DegradedResult


class AdapterError(RuntimeError):
    """Base error used inside the adapter before conversion to a public outcome."""

    def __init__(self, reason: str, *, backend_name: str) -> None:
        super().__init__(reason)
        self.reason = reason
        self.backend_name = backend_name


class RetryableError(AdapterError):
    """Internal error that permits trying the next explicitly configured backend."""


class FatalError(AdapterError):
    """Internal error that stops the configured fallback chain immediately."""
