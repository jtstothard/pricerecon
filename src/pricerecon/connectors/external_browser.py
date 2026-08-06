"""Truthful adapter for configured external browser backends.

This is deliberately separate from :mod:`browser_client`: connectors that need
an external browser receive a uniform, typed result rather than a Playwright or
vendor-specific object.  A configured selection is authoritative; this module
never falls back to a local browser.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx

from pricerecon.connectors.browser_client import (
    BrowserBackendConfig,
    _validate_playwright_storage_state,
    resolve_browser_backends,
)
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus


class BrowserDegradation(StrEnum):
    NONE = "none"
    NOT_CONFIGURED = "not_configured"
    BACKEND_UNAVAILABLE = "backend_unavailable"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"
    EMPTY_RESULT = "empty_result"
    MALFORMED_RESPONSE = "malformed_response"
    UNSUPPORTED = "unsupported"


_DEFAULT_RETRYABLE = frozenset({BrowserDegradation.BACKEND_UNAVAILABLE, BrowserDegradation.TIMEOUT})
_SECRET_HEADER = re.compile(
    r"cookie|authorization|token|secret|key|akamai|proxy-authorization", re.I
)
_SECRET_FIELD = re.compile(r"cookie|authorization|token|secret|password|api.?key|session", re.I)
_URL_IN_ERROR = re.compile(r"(?:https?|wss?)://[^\s'\"<>]+")


@dataclass(frozen=True, slots=True)
class RenderedContent:
    """Content rendered by a browser; ``snapshot`` is not claimed to be HTML."""

    title: str = ""
    html: str = ""
    snapshot: str = ""


@dataclass(frozen=True, slots=True)
class NetworkResponse:
    """A response observed by a backend that explicitly supports interception."""

    url: str
    status: int | None
    headers: Mapping[str, str] = field(default_factory=dict)
    body: str = ""
    intercepted: bool = False


@dataclass(frozen=True, slots=True)
class BrowserAttempt:
    backend: str
    degradation: BrowserDegradation
    reason: str = ""
    status: int | None = None


@dataclass(frozen=True, slots=True)
class ExternalBrowserResult:
    """Uniform adapter outcome. Empty content is explicit, never fabricated."""

    selected_backend: str | None
    attempts: tuple[BrowserAttempt, ...]
    rendered: RenderedContent = field(default_factory=RenderedContent)
    responses: tuple[NetworkResponse, ...] = ()
    degradation: BrowserDegradation = BrowserDegradation.NONE
    network_interception_supported: bool = False

    @property
    def degraded(self) -> bool:
        return self.degradation is not BrowserDegradation.NONE


def _safe_endpoint(endpoint: str) -> str:
    parsed = urlsplit(endpoint)
    if parsed.username is None and parsed.password is None:
        return endpoint
    host = parsed.hostname or ""
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme, host, parsed.path, parsed.query, parsed.fragment))


def _safe_error(error: Exception) -> str:
    return _URL_IN_ERROR.sub(lambda match: _safe_endpoint(match.group(0)), str(error))[:300]


def _redact_headers(headers: Mapping[str, Any]) -> dict[str, str]:
    return {
        str(key): "[redacted]" if _SECRET_HEADER.search(str(key)) else str(value)[:300]
        for key, value in headers.items()
    }


def _redact_body(value: Any, limit: int) -> str:
    def redact(item: Any) -> Any:
        if isinstance(item, Mapping):
            return {
                str(key): "[redacted]" if _SECRET_FIELD.search(str(key)) else redact(val)
                for key, val in item.items()
            }
        if isinstance(item, list):
            return [redact(entry) for entry in item]
        return item

    if isinstance(value, str):
        return value[:limit]
    try:
        return json.dumps(redact(value), separators=(",", ":"), ensure_ascii=False)[:limit]
    except (TypeError, ValueError):
        return "[unserializable response body]"


def _retryable(backend: BrowserBackendConfig, degradation: BrowserDegradation) -> bool:
    configured = backend.options.get("fallback_on")
    if configured is None:
        return degradation in _DEFAULT_RETRYABLE
    if not isinstance(configured, list) or not all(isinstance(value, str) for value in configured):
        raise ValueError(
            "fallback_on must be a list of degradation strings, " f"got {type(configured).__name__}"
        )
    return degradation.value in configured


class ExternalBrowserAdapter:
    """Invoke only the named configured backend(s), in policy-controlled order."""

    def __init__(
        self,
        backends: list[BrowserBackendConfig],
        *,
        client_factory: Callable[..., httpx.AsyncClient] = httpx.AsyncClient,
    ) -> None:
        self._backends = backends
        self._client_factory = client_factory

    @classmethod
    def from_config(
        cls,
        runtime_config: Mapping[str, Any],
        connector_config: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> "ExternalBrowserAdapter":
        return cls(resolve_browser_backends(runtime_config, connector_config), **kwargs)

    def has_authenticated_camofox_profile(self) -> bool:
        """Return whether every selected backend is a persistent Camofox profile.

        This intentionally exposes only the presence of the required profile
        identifiers, never their values. Connectors with stricter policies can
        use it to reject anonymous or mixed backend selections before any
        navigation is attempted.
        """
        return bool(self._backends) and all(
            backend.type == "camofox"
            and all(str(backend.options.get(key, "")).strip() for key in ("user_id", "session_key"))
            for backend in self._backends
        )

    def has_authenticated_cloakbrowser_reddit(self) -> bool:
        """Return whether the explicit Camofox-to-CloakBrowser bridge is usable."""
        camo = [backend for backend in self._backends if backend.type == "camofox"]
        return (
            len(self._backends) == 2
            and len(camo) == 1
            and any(backend.type == "cloakbrowser" for backend in self._backends)
            and all(str(camo[0].options.get(key, "")).strip() for key in ("user_id", "session_key"))
        )

    async def navigate_with_camofox_storage_state(
        self, url: str, *, wait_ms: int = 3_000, timeout_ms: int = 60_000
    ) -> ExternalBrowserResult:
        """Navigate with Camofox storageState passed in memory to CloakBrowser.

        The state is never persisted, returned, or included in an exception or
        diagnostic. Failure is an explicit degraded result so callers retain
        their normal unauthenticated fallback chain.
        """
        if not self.has_authenticated_cloakbrowser_reddit():
            return ExternalBrowserResult(
                selected_backend=None,
                attempts=(
                    BrowserAttempt(
                        "cloakbrowser-auth",
                        BrowserDegradation.NOT_CONFIGURED,
                        "authenticated backend pair not configured",
                    ),
                ),
                degradation=BrowserDegradation.NOT_CONFIGURED,
            )
        camo = next(backend for backend in self._backends if backend.type == "camofox")
        cloak = next(backend for backend in self._backends if backend.type == "cloakbrowser")
        options = camo.options
        token = str(options.get("api_key", options.get("access_key", ""))).strip()
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        state_path = str(options.get("storage_state_path", "/storage-state"))
        if not state_path.startswith("/"):
            state_path = "/" + state_path
        try:
            async with self._client_factory(timeout=timeout_ms / 1000) as client:
                response = await client.get(
                    f"{camo.endpoint.rstrip('/')}{state_path}",
                    params={
                        "userId": str(options["user_id"]),
                        "sessionKey": str(options["session_key"]),
                    },
                    headers=headers,
                )
                response.raise_for_status()
                payload = response.json()
            state: Any = (
                payload.get("storageState", payload) if isinstance(payload, Mapping) else None
            )
            _validate_playwright_storage_state(state)
            # POST the validated storageState to the CloakBrowser HTTP wrapper
            # in memory. The wrapper injects it into browser.newContext({storageState})
            # and never persists/logs it. This replaces the local Node subprocess
            # bridge (run_cloakbrowser_bridge) which requires the cloakbrowser SDK
            # to be resolvable inside the PriceRecon container — it is not, so the
            # bridge cannot start. The HTTP wrapper is the deployed sidecar at
            # cloak.endpoint (for example, the internal CloakBrowser service URL).
            wrapper_url = f"{cloak.endpoint.rstrip('/')}/api/browser/authenticated-session"
            async with self._client_factory(
                timeout=(timeout_ms + wait_ms + 10_000) / 1000
            ) as render_client:
                render_response = await render_client.post(
                    wrapper_url,
                    json={
                        "url": url,
                        "storageState": dict(state),
                        "waitMs": wait_ms,
                        "redditStructured": True,
                    },
                )
                render_response.raise_for_status()
                bridge = render_response.json()
            if (
                not isinstance(bridge, Mapping)
                or bridge.get("ok") is not True
                or bridge.get("navigated") is not True
            ):
                reason = (
                    str(bridge.get("error"))
                    if isinstance(bridge, Mapping)
                    else "authenticated wrapper returned malformed response"
                )
                return ExternalBrowserResult(
                    selected_backend=cloak.name,
                    attempts=(
                        BrowserAttempt(cloak.name, BrowserDegradation.BACKEND_UNAVAILABLE, reason),
                    ),
                    degradation=BrowserDegradation.BACKEND_UNAVAILABLE,
                )
            structured = {
                "authenticated": bool(bridge.get("authenticated")),
                "items": bridge.get("items", []),
            }
            if not structured["authenticated"]:
                return ExternalBrowserResult(
                    selected_backend=cloak.name,
                    attempts=(
                        BrowserAttempt(
                            cloak.name,
                            BrowserDegradation.BLOCKED,
                            "Reddit authentication was not proven",
                        ),
                    ),
                    degradation=BrowserDegradation.BLOCKED,
                )
            return ExternalBrowserResult(
                selected_backend=cloak.name,
                attempts=(BrowserAttempt(cloak.name, BrowserDegradation.NONE),),
                rendered=RenderedContent(
                    title=str(bridge.get("title") or ""),
                    snapshot=json.dumps(structured, separators=(",", ":")),
                ),
            )
        except (httpx.HTTPError, OSError, TypeError, ValueError, KeyError):
            return ExternalBrowserResult(
                selected_backend=cloak.name,
                attempts=(
                    BrowserAttempt(
                        cloak.name,
                        BrowserDegradation.MALFORMED_RESPONSE,
                        "authenticated state unavailable",
                    ),
                ),
                degradation=BrowserDegradation.MALFORMED_RESPONSE,
            )

    async def evaluate_readonly(
        self,
        url: str,
        expression: str,
        *,
        timeout_ms: int = 60_000,
    ) -> Any:
        """Evaluate one read-only expression in an authenticated Camofox page.

        This is intentionally narrower than a browser automation API: it only
        supports a named, persistent Camofox profile, creates one temporary tab,
        evaluates one expression, and closes that tab in a ``finally`` block.
        Callers must keep the expression read-only; no click/type/press or
        arbitrary tab/session operations are exposed here.
        """
        if not expression.strip():
            raise ValueError("Camofox evaluation expression must not be empty")
        if not self.has_authenticated_camofox_profile() or len(self._backends) != 1:
            raise ValueError("read-only evaluation requires one authenticated Camofox profile")
        backend = self._backends[0]
        if backend.type != "camofox":
            raise ValueError("read-only evaluation requires a Camofox backend")
        return await self._camofox_evaluate(backend, url, expression, timeout_ms)

    async def navigate(
        self,
        url: str,
        *,
        api_url: str | None = None,
        wait_ms: int = 3_000,
        timeout_ms: int = 60_000,
        response_body_limit: int = 32_768,
    ) -> ExternalBrowserResult:
        if not self._backends:
            return ExternalBrowserResult(
                selected_backend=None,
                attempts=(
                    BrowserAttempt(
                        "", BrowserDegradation.NOT_CONFIGURED, "no browser backend selected"
                    ),
                ),
                degradation=BrowserDegradation.NOT_CONFIGURED,
            )

        attempts: list[BrowserAttempt] = []
        for backend in self._backends:
            try:
                rendered, responses, interception = await self._invoke(
                    backend, url, api_url, wait_ms, timeout_ms, response_body_limit
                )
                degradation = (
                    BrowserDegradation.EMPTY_RESULT
                    if not (rendered.html or rendered.snapshot or rendered.title or responses)
                    else BrowserDegradation.NONE
                )
                attempts.append(BrowserAttempt(backend.name, degradation))
                if degradation is BrowserDegradation.NONE:
                    return ExternalBrowserResult(
                        backend.name,
                        tuple(attempts),
                        rendered,
                        tuple(responses),
                        degradation,
                        interception,
                    )
                if _retryable(backend, degradation):
                    continue
                return ExternalBrowserResult(
                    backend.name,
                    tuple(attempts),
                    degradation=degradation,
                    network_interception_supported=interception,
                )
            except httpx.TimeoutException as exc:
                degradation, reason = BrowserDegradation.TIMEOUT, _safe_error(exc)
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                degradation = (
                    BrowserDegradation.BLOCKED
                    if status in {401, 403, 429}
                    else BrowserDegradation.BACKEND_UNAVAILABLE
                )
                reason = f"backend returned HTTP {status} at {_safe_endpoint(str(exc.request.url))}"
                attempts.append(BrowserAttempt(backend.name, degradation, reason, status))
                if _retryable(backend, degradation):
                    continue
                return ExternalBrowserResult(backend.name, tuple(attempts), degradation=degradation)
            except (httpx.HTTPError, OSError) as exc:
                degradation, reason = BrowserDegradation.BACKEND_UNAVAILABLE, _safe_error(exc)
            except (TypeError, ValueError, KeyError) as exc:
                degradation, reason = BrowserDegradation.MALFORMED_RESPONSE, _safe_error(exc)
            except Exception as exc:  # fail closed on optional external infrastructure
                degradation, reason = BrowserDegradation.UNSUPPORTED, _safe_error(exc)
            attempts.append(BrowserAttempt(backend.name, degradation, reason))
            if _retryable(backend, degradation):
                continue
            return ExternalBrowserResult(backend.name, tuple(attempts), degradation=degradation)

        selected = attempts[-1].backend if attempts else None
        degradation = attempts[-1].degradation if attempts else BrowserDegradation.NOT_CONFIGURED
        return ExternalBrowserResult(selected, tuple(attempts), degradation=degradation)

    async def _invoke(
        self,
        backend: BrowserBackendConfig,
        url: str,
        api_url: str | None,
        wait_ms: int,
        timeout_ms: int,
        response_body_limit: int,
    ) -> tuple[RenderedContent, list[NetworkResponse], bool]:
        if backend.type == "cloakbrowser":
            return await self._cloakbrowser(
                backend, url, api_url, wait_ms, timeout_ms, response_body_limit
            )
        if backend.type == "camofox":
            return await self._camofox(backend, url, timeout_ms)
        if backend.type == "playwright":
            return await self._playwright(backend, url, wait_ms, timeout_ms, response_body_limit)
        if backend.type == "flaresolverr":
            return await self._flaresolverr(backend, url, timeout_ms)
        raise ValueError(f"unsupported browser backend type {backend.type!r}")

    async def _flaresolverr(
        self, backend: BrowserBackendConfig, url: str, timeout_ms: int
    ) -> tuple[RenderedContent, list[NetworkResponse], bool]:
        """Use a FlareSolverr-compatible endpoint without claiming interception.

        Its ``solution.response`` is serialized rendered HTML.  It is neither
        an intercepted response nor a direct retailer HTTP response.
        """
        async with self._client_factory(timeout=timeout_ms / 1000) as client:
            response = await client.post(
                backend.endpoint.rstrip("/"),
                json={"cmd": "request.get", "url": url, "maxTimeout": timeout_ms},
            )
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, Mapping):
            raise ValueError("FlareSolverr response was not an object")
        solution = payload.get("solution")
        if not isinstance(solution, Mapping):
            raise ValueError("FlareSolverr response missing solution")
        html = solution.get("response")
        if not isinstance(html, str):
            raise ValueError("FlareSolverr response missing solution.response HTML")
        return RenderedContent(html=html), [], False

    async def _cloakbrowser(
        self,
        backend: BrowserBackendConfig,
        url: str,
        api_url: str | None,
        wait_ms: int,
        timeout_ms: int,
        limit: int,
    ) -> tuple[RenderedContent, list[NetworkResponse], bool]:
        endpoint = f"{backend.endpoint.rstrip('/')}/api/browser/session"
        async with self._client_factory(timeout=timeout_ms / 1000) as client:
            response = await client.post(
                endpoint, json={"url": url, "apiUrl": api_url, "waitMs": wait_ms}
            )
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, Mapping) or payload.get("navigated") is not True:
            raise ValueError("CloakBrowser response omitted navigated=true")
        html = payload.get("html", payload.get("content", ""))
        snapshot = payload.get("snapshot", "")
        if not isinstance(html, str) or not isinstance(snapshot, str):
            raise ValueError("CloakBrowser rendered content must be strings")
        rendered = RenderedContent(
            title=str(payload.get("title") or ""), html=html, snapshot=snapshot
        )
        responses: list[NetworkResponse] = []
        # A sidecar may provide explicit network captures. Do not label its
        # navigation/snapshot-only data as intercepted.
        captures = payload.get("networkResponses", payload.get("interceptedResponses", []))
        if captures is not None and not isinstance(captures, list):
            raise ValueError("networkResponses must be a list")
        for capture in captures or []:
            if not isinstance(capture, Mapping):
                raise ValueError("network response must be an object")
            responses.append(
                NetworkResponse(
                    url=str(capture.get("url") or ""),
                    status=_as_status(capture.get("status")),
                    headers=_redact_headers(_as_mapping(capture.get("headers"))),
                    body=_redact_body(capture.get("body", ""), limit),
                    intercepted=True,
                )
            )
        # ``api`` is an explicit in-page fetch, not passive interception. It is
        # still useful rendered-browser evidence and is truthfully marked false.
        api = payload.get("api")
        if isinstance(api, Mapping):
            responses.append(
                NetworkResponse(
                    url=str(payload.get("apiUrl") or api_url or ""),
                    status=_as_status(api.get("status")),
                    headers=_redact_headers({"content-type": api.get("contentType", "")}),
                    body=_redact_body(api.get("body", ""), limit),
                    intercepted=False,
                )
            )
        return rendered, responses, True

    async def _camofox_evaluate(
        self,
        backend: BrowserBackendConfig,
        url: str,
        expression: str,
        timeout_ms: int,
    ) -> Any:
        opts = backend.options
        user_id = str(opts["user_id"])
        session_key = str(opts["session_key"])
        token = str(opts.get("api_key", opts.get("access_key", ""))).strip()
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        base = backend.endpoint.rstrip("/")
        async with self._client_factory(timeout=timeout_ms / 1000) as client:
            opened = await client.post(
                f"{base}/tabs",
                json={
                    "userId": user_id,
                    "sessionKey": session_key,
                    "listItemId": session_key,
                    "url": url,
                },
                headers=headers,
            )
            opened.raise_for_status()
            data = opened.json()
            if not isinstance(data, Mapping):
                raise ValueError("Camofox tab response was not an object")
            tab_id = str(data.get("tabId") or data.get("id") or "").strip()
            if not tab_id:
                raise ValueError("Camofox did not return a tab id")
            try:
                evaluated = await client.post(
                    f"{base}/tabs/{tab_id}/evaluate",
                    json={"userId": user_id, "expression": expression},
                    headers=headers,
                )
                evaluated.raise_for_status()
                payload = evaluated.json()
                if not isinstance(payload, Mapping) or payload.get("ok") is not True:
                    raise ValueError("Camofox evaluation response omitted ok=true")
                return payload.get("result")
            finally:
                try:
                    await client.delete(
                        f"{base}/tabs/{tab_id}", params={"userId": user_id}, headers=headers
                    )
                except Exception:
                    pass

    async def _camofox(
        self, backend: BrowserBackendConfig, url: str, timeout_ms: int
    ) -> tuple[RenderedContent, list[NetworkResponse], bool]:
        opts = backend.options
        user_id = str(opts.get("user_id", "pricerecon"))
        session_key = str(opts.get("session_key", "external-browser"))
        token = str(opts.get("api_key", opts.get("access_key", ""))).strip()
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        base = backend.endpoint.rstrip("/")
        async with self._client_factory(timeout=timeout_ms / 1000) as client:
            opened = await client.post(
                f"{base}/tabs",
                json={
                    "userId": user_id,
                    "sessionKey": session_key,
                    "listItemId": session_key,
                    "url": url,
                },
                headers=headers,
            )
            opened.raise_for_status()
            data = opened.json()
            if not isinstance(data, Mapping):
                raise ValueError("Camofox tab response was not an object")
            tab_id = str(data.get("tabId") or data.get("id") or "").strip()
            if not tab_id:
                raise ValueError("Camofox did not return a tab id")
            try:
                # Camofox returns the tab before Reddit's client-side page has
                # populated the accessibility tree. Poll briefly instead of
                # treating the initial shell (often just "Skip to main
                # content") as a parse failure.
                text = ""
                for attempt in range(10):
                    snapshot = await client.get(
                        f"{base}/tabs/{tab_id}/snapshot",
                        params={"userId": user_id, "format": "text"},
                        headers=headers,
                    )
                    snapshot.raise_for_status()
                    document = snapshot.json()
                    if not isinstance(document, Mapping):
                        raise ValueError("Camofox snapshot response was not an object")
                    text = str(document.get("snapshot") or document.get("text") or "")
                    if "/comments/" in text or attempt == 9:
                        break
                    await asyncio.sleep(1)
            finally:
                try:
                    await client.delete(
                        f"{base}/tabs/{tab_id}", params={"userId": user_id}, headers=headers
                    )
                except Exception:
                    pass
        return RenderedContent(snapshot=text), [], False

    async def _playwright(
        self, backend: BrowserBackendConfig, url: str, wait_ms: int, timeout_ms: int, limit: int
    ) -> tuple[RenderedContent, list[NetworkResponse], bool]:
        from pricerecon.connectors.browser_client import async_playwright

        if async_playwright is None:
            raise RuntimeError("Playwright is unavailable")
        captures: list[NetworkResponse] = []
        capture_pattern = re.compile(str(backend.options.get("capture_url_pattern", ".")))
        playwright = await async_playwright().start()
        browser: Any = None
        try:
            browser = await playwright.chromium.connect_over_cdp(
                backend.endpoint, timeout=timeout_ms
            )
            context = await browser.new_context()
            page = await context.new_page()

            async def capture(response: Any) -> None:
                if not capture_pattern.search(response.url):
                    return
                try:
                    body = await response.body()
                    captures.append(
                        NetworkResponse(
                            response.url,
                            response.status,
                            _redact_headers(response.headers),
                            body[:limit].decode("utf-8", "replace"),
                            True,
                        )
                    )
                except Exception:
                    captures.append(
                        NetworkResponse(
                            response.url,
                            response.status,
                            _redact_headers(response.headers),
                            "",
                            True,
                        )
                    )

            page.on("response", lambda response: asyncio.create_task(capture(response)))
            main = await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            await page.wait_for_timeout(wait_ms)
            html, title = await page.content(), await page.title()
            if main is not None:
                captures.append(
                    NetworkResponse(url, main.status, _redact_headers(main.headers), "", True)
                )
            await context.close()
            return RenderedContent(title=title, html=html), captures, True
        finally:
            if browser is not None:
                await browser.close()
            await playwright.stop()


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("headers must be an object")
    return value


def _as_status(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("status must be an integer")
    return int(value)


def as_connector_degraded_error(
    result: ExternalBrowserResult, connector_id: str
) -> ConnectorDegradedError:
    """Translate a typed adapter outcome into a connector-visible degradation."""
    status = {
        BrowserDegradation.BLOCKED: ConnectorStatus.bot_blocked,
        BrowserDegradation.TIMEOUT: ConnectorStatus.timeout,
        BrowserDegradation.EMPTY_RESULT: ConnectorStatus.parse_error,
        BrowserDegradation.MALFORMED_RESPONSE: ConnectorStatus.parse_error,
    }.get(result.degradation, ConnectorStatus.unknown_error)
    attempts = [
        {
            "backend": attempt.backend,
            "degradation": attempt.degradation.value,
            "reason": attempt.reason,
            "status": attempt.status,
        }
        for attempt in result.attempts
    ]
    return ConnectorDegradedError(
        status=status,
        message=(f"{connector_id} external browser degraded: {result.degradation.value}"),
        connector_id=connector_id,
        detail={
            "selected_backend": result.selected_backend,
            "degradation": result.degradation.value,
            "attempts": attempts,
        },
    )
