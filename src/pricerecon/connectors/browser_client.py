"""Shared browser client utilities for browser-based connectors.

Supports either a local Playwright browser, a remote Camofox REST backend,
or the CloakBrowser patched Chromium binary (anti-bot bypass).
"""

from __future__ import annotations

import asyncio
import glob
import json
import logging
import os
from collections.abc import Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator
from urllib.parse import urlsplit, urlunsplit

import httpx

logger = logging.getLogger(__name__)

try:
    from browserforge.fingerprints import FingerprintGenerator  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    FingerprintGenerator = None  # type: ignore[assignment]

try:
    from playwright.async_api import async_playwright  # type: ignore
except Exception as exc:  # pragma: no cover - optional dependency
    async_playwright = None  # type: ignore[assignment]
    _PLAYWRIGHT_IMPORT_ERROR: Exception | None = exc
else:
    _PLAYWRIGHT_IMPORT_ERROR = None

try:
    from playwright_stealth import stealth_async  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    stealth_async = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# CloakBrowser binary resolution
# ---------------------------------------------------------------------------


def resolve_cloakbrowser_binary() -> str | None:
    """Return the path to the CloakBrowser Chromium binary, or None.

    Resolution order:
    1. ``PRICERECON_CLOAKBROWSER_CHROME`` env var (absolute path).
    2. Glob ``~/.cloakbrowser/chromium-*/chrome``, highest semver wins.
    3. ``None`` — CloakBrowser unavailable; callers must degrade gracefully.
    """
    env_path = os.environ.get("PRICERECON_CLOAKBROWSER_CHROME", "").strip()
    if env_path and os.path.isfile(env_path):
        return env_path

    pattern = os.path.expanduser("~/.cloakbrowser/chromium-*/chrome")
    candidates = glob.glob(pattern)
    if not candidates:
        return None

    def _version_key(path: str) -> tuple[int, ...]:
        # Extract version numbers from the directory name
        dirname = os.path.basename(os.path.dirname(path))
        # dirname is like "chromium-146.0.7680.177.5"
        version_str = dirname.replace("chromium-", "")
        try:
            return tuple(int(x) for x in version_str.split("."))
        except ValueError:
            return (0,)

    candidates.sort(key=_version_key, reverse=True)
    best = candidates[0]
    if os.path.isfile(best):
        return best
    return None


class CloakBrowserBridgeUnavailable(RuntimeError):
    """The optional Node/CloakBrowser bridge could not be started or used."""


async def run_cloakbrowser_bridge(
    url: str,
    *,
    storage_state: Mapping[str, Any] | None = None,
    wait_ms: int = 8000,
    nav_timeout_ms: int = 45_000,
    timeout_ms: int | None = None,
) -> dict[str, Any]:
    """Fetch one URL through the pinned Node CloakBrowser SDK bridge.

    The bridge is deliberately a one-request subprocess. This keeps browser
    lifecycle ownership unambiguous: success, timeout, malformed output, and
    every startup/error path terminate the child and fail closed.
    """
    bridge = Path(__file__).parents[3] / "tools" / "cloakbrowser-bridge" / "bridge.mjs"
    node = os.environ.get("PRICERECON_NODE", "node")
    if storage_state is not None:
        _validate_playwright_storage_state(storage_state)
    result: dict[str, Any] = {
        "status": 0,
        "title": "",
        "html": "",
        "content": "",
        "blocked": True,
        "used_cloakbrowser": True,
        "timing_ms": 0,
    }
    process: Any = None
    effective_timeout = timeout_ms if timeout_ms is not None else nav_timeout_ms + wait_ms + 10_000
    try:
        process = await asyncio.create_subprocess_exec(
            node,
            str(bridge),
            "--stdio",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        request = (
            json.dumps(
                {
                    "url": url,
                    "storageState": dict(storage_state or {"cookies": [], "origins": []}),
                    "options": {"wait_ms": wait_ms, "nav_timeout_ms": nav_timeout_ms},
                }
            ).encode()
            + b"\n"
        )
        assert process.stdin is not None
        process.stdin.write(request)
        await process.stdin.drain()
        process.stdin.close()
        assert process.stdout is not None
        raw = await asyncio.wait_for(process.stdout.readline(), effective_timeout / 1000)
        if not raw:
            raise CloakBrowserBridgeUnavailable("bridge returned no response")
        decoded = json.loads(raw)
        if not isinstance(decoded, dict):
            raise CloakBrowserBridgeUnavailable("bridge response was not an object")
        result.update(decoded)
    except FileNotFoundError as exc:
        result["error"] = CloakBrowserBridgeUnavailable(f"Node runtime unavailable: {exc}")
    except (TimeoutError, asyncio.TimeoutError) as exc:
        result["error"] = CloakBrowserBridgeUnavailable(f"CloakBrowser bridge timed out: {exc}")
    except (json.JSONDecodeError, OSError, CloakBrowserBridgeUnavailable) as exc:
        result["error"] = CloakBrowserBridgeUnavailable(str(exc))
    except Exception as exc:  # Fail closed for optional anti-bot infrastructure.
        result["error"] = CloakBrowserBridgeUnavailable(str(exc))
    finally:
        if process is not None:
            try:
                if process.returncode is None:
                    process.kill()
                await process.wait()
            except ProcessLookupError:
                pass  # already gone
            except Exception as exc:
                logger.warning(f"CloakBrowser bridge cleanup failed: {exc}")
    result["blocked"] = bool(result.get("blocked", True))
    return result


def _validate_playwright_storage_state(state: Mapping[str, Any]) -> None:
    """Validate the small Playwright storageState contract without retaining it."""
    if not isinstance(state, Mapping):
        raise ValueError("Playwright storageState must be an object")
    cookies = state.get("cookies", [])
    origins = state.get("origins", [])
    if not isinstance(cookies, list) or not isinstance(origins, list):
        raise ValueError("Playwright storageState cookies/origins must be arrays")
    for cookie in cookies:
        if not isinstance(cookie, Mapping) or not all(
            isinstance(cookie.get(field), str) for field in ("name", "value", "domain", "path")
        ):
            raise ValueError("Playwright storageState contains a malformed cookie")
    for origin in origins:
        if not isinstance(origin, Mapping) or not isinstance(origin.get("origin"), str):
            raise ValueError("Playwright storageState contains a malformed origin")
        local = origin.get("localStorage", [])
        if not isinstance(local, list) or any(
            not isinstance(entry, Mapping)
            or not isinstance(entry.get("name"), str)
            or not isinstance(entry.get("value"), str)
            for entry in local
        ):
            raise ValueError("Playwright storageState contains malformed localStorage")


# ---------------------------------------------------------------------------
# Block detection
# ---------------------------------------------------------------------------


def is_blocked(html: str, title: str, status: int = 200) -> bool:
    """Detect anti-bot block signals in page content.

    Args:
        html: Page HTML content.
        title: Page title.
        status: HTTP status code (if available).

    Returns:
        True if a block / challenge is detected.

    Note:
        Real eBay pages sometimes contain the word "captcha" inside hidden
        elements (e.g. accessibility labels or script payloads).  This
        function will still return True in that case — callers that want to
        distinguish a blocked page from a real results page should additionally
        check for presence of ``s-item`` or ``srp-results`` in the HTML, and
        should NOT rely solely on ``is_blocked`` as a success signal.
    """
    if status in (401, 403):
        return True

    html_lower = html.lower()
    title_lower = title.lower()

    # Cloudflare
    cloudflare_patterns = [
        "cf-challenge",
        "cf-turnstile",
        "challenge-platform",
        "jschl_answer",
    ]
    if any(p in html_lower for p in cloudflare_patterns):
        return True

    # DataDome
    if "datadome" in html_lower:
        return True

    # Generic error / block pages
    if (
        "error page" in title_lower
        or "something went wrong on our end" in html_lower
        or "access denied" in html_lower
        or "you have been blocked" in html_lower
    ):
        return True

    # CAPTCHA indicators
    captcha_patterns = [
        "captcha",
        "verify it",
        "verify you are human",
        "are you a robot",
    ]
    if any(p in html_lower for p in captcha_patterns):
        return True

    return False


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class BrowserSessionConfig:
    headless: bool = True
    viewport_width: int = 1366
    viewport_height: int = 768
    user_agent: str | None = None
    locale: str = "en-GB"
    timezone_id: str = "Europe/London"
    navigation_timeout_ms: int = 45_000
    wait_after_navigation_ms: int = 2_500
    camofox_url: str | None = None
    camofox_user_id: str | None = None
    camofox_session_key: str | None = None
    camofox_api_key: str | None = None
    camofox_access_key: str | None = None
    # CloakBrowser backend
    use_cloakbrowser: bool = field(default=False)
    cloakbrowser_fallback: bool = field(default=True)
    # Named external browser backends.  These are deliberately plain data so
    # credentials can remain in environment/config-local files and are never
    # included in reprs or error messages.
    browser_backends: Mapping[str, Any] | None = None
    browser_selection: str | list[str] | None = None
    browser_default: str | list[str] | None = None

    def backend_registry(self) -> "BrowserBackendRegistry | None":
        if self.browser_backends is None:
            return None
        return BrowserBackendRegistry.from_mapping(self.browser_backends)

    def __post_init__(self) -> None:
        env_timeout = os.environ.get("PRICERECON_BROWSER_NAV_TIMEOUT_MS", "").strip()
        if env_timeout.isdigit() and int(env_timeout) > 0:
            self.navigation_timeout_ms = int(env_timeout)
        env_wait = os.environ.get("PRICERECON_BROWSER_WAIT_MS", "").strip()
        if env_wait.isdigit() and int(env_wait) >= 0:
            self.wait_after_navigation_ms = int(env_wait)
        # env-var overrides for CloakBrowser flags
        env_use = os.environ.get("PRICERECON_CLOAKBROWSER_USE", "").strip().lower()
        if env_use in ("1", "true", "yes"):
            self.use_cloakbrowser = True
        elif env_use in ("0", "false", "no"):
            self.use_cloakbrowser = False

        env_fb = os.environ.get("PRICERECON_CLOAKBROWSER_FALLBACK", "").strip().lower()
        if env_fb in ("0", "false", "no"):
            self.cloakbrowser_fallback = False
        elif env_fb in ("1", "true", "yes"):
            self.cloakbrowser_fallback = True


class BrowserBackendConfig:
    """Validated, secret-safe description of one browser service."""

    __slots__ = ("name", "type", "endpoint", "options")

    def __init__(self, name: str, backend_type: str, endpoint: str, options: dict[str, Any]):
        self.name = name
        self.type = backend_type
        self.endpoint = endpoint
        self.options = dict(options)

    def __repr__(self) -> str:
        return f"BrowserBackendConfig(name={self.name!r}, type={self.type!r}, endpoint={_redact_endpoint(self.endpoint)!r})"


class BrowserBackendConfigError(ValueError):
    """Configuration is invalid or refers to an unknown backend."""


class BrowserBackendRegistry:
    """Registry and deterministic selector for configured external browsers.

    Accepted shape is ``{name: {type, endpoint, options}}``.  A list is used
    for ordered fallback; it is never silently replaced by local Playwright.
    """

    _SUPPORTED_TYPES = {"camofox", "playwright", "cloakbrowser", "flaresolverr"}

    def __init__(self, backends: dict[str, BrowserBackendConfig]):
        self.backends = backends

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "BrowserBackendRegistry":
        if not isinstance(raw, Mapping) or not raw:
            raise BrowserBackendConfigError("browser_backends must be a non-empty mapping")
        parsed: dict[str, BrowserBackendConfig] = {}
        for name, value in raw.items():
            if not isinstance(name, str) or not name.strip():
                raise BrowserBackendConfigError("browser backend names must be non-empty strings")
            if not isinstance(value, Mapping):
                raise BrowserBackendConfigError(f"browser backend '{name}' must be a mapping")
            backend_type = str(value.get("type", "")).strip().lower()
            if backend_type not in cls._SUPPORTED_TYPES:
                raise BrowserBackendConfigError(
                    f"browser backend '{name}' has unsupported type '{backend_type}'"
                )
            endpoint = str(value.get("endpoint", "")).strip()
            if not endpoint:
                raise BrowserBackendConfigError(f"browser backend '{name}' is missing endpoint")
            try:
                parsed_endpoint = urlsplit(endpoint)
            except ValueError as exc:
                raise BrowserBackendConfigError(
                    f"browser backend '{name}' endpoint must be a valid URL"
                ) from exc
            allowed_schemes = {
                "camofox": {"http", "https"},
                "playwright": {"http", "https", "ws", "wss"},
                "cloakbrowser": {"http", "https"},
                "flaresolverr": {"http", "https"},
            }[backend_type]
            if parsed_endpoint.scheme not in allowed_schemes or not parsed_endpoint.hostname:
                raise BrowserBackendConfigError(
                    f"browser backend '{name}' endpoint must be a valid URL for type '{backend_type}'"
                )
            try:
                parsed_endpoint.port
            except ValueError as exc:
                raise BrowserBackendConfigError(
                    f"browser backend '{name}' endpoint must be a valid URL"
                ) from exc
            options = value.get("options", {})
            if not isinstance(options, Mapping):
                raise BrowserBackendConfigError(
                    f"browser backend '{name}'.options must be a mapping"
                )
            parsed[name.strip()] = BrowserBackendConfig(
                name.strip(), backend_type, endpoint, dict(options)
            )
        return cls(parsed)

    def select(
        self, selection: str | list[str] | tuple[str, ...] | None
    ) -> list[BrowserBackendConfig]:
        if selection is None:
            raise BrowserBackendConfigError("no browser backend selection configured")
        if not isinstance(selection, (str, list, tuple)):
            raise BrowserBackendConfigError(
                "browser selection must be a string or list/tuple of strings (non-empty list)"
            )
        names = [selection] if isinstance(selection, str) else list(selection)
        if not names or any(not isinstance(name, str) or not name.strip() for name in names):
            raise BrowserBackendConfigError(
                "browser selection must be a string or list/tuple of strings (non-empty list)"
            )
        unknown = [name for name in names if name not in self.backends]
        if unknown:
            raise BrowserBackendConfigError(f"unknown browser backend(s): {', '.join(unknown)}")
        return [self.backends[name] for name in names]

    def public(self) -> dict[str, dict[str, str]]:
        """Return diagnostics safe to log (options/credentials are excluded)."""
        return {
            name: {"type": backend.type, "endpoint": _redact_endpoint(backend.endpoint)}
            for name, backend in self.backends.items()
        }


def _redact_endpoint(endpoint: str) -> str:
    """Remove credentials from an endpoint before it enters diagnostics."""
    parsed = urlsplit(endpoint)
    if parsed.username is None and parsed.password is None:
        return endpoint
    host = parsed.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme, host, parsed.path, parsed.query, parsed.fragment))


def resolve_browser_backend(
    runtime_config: Mapping[str, Any], connector_config: Mapping[str, Any] | None = None
) -> BrowserBackendConfig | None:
    """Resolve the configured backend for a connector without local fallback.

    ``browser_backend`` (or the legacy-friendly ``browser_selection``) on the
    connector wins over the top-level ``browser_default``. A list is accepted
    and returns its first configured backend; callers doing retries should use
    :meth:`BrowserBackendRegistry.select` to retain the complete ordered list.
    """
    raw = runtime_config.get("browser_backends")
    if raw is None:
        return None
    registry = BrowserBackendRegistry.from_mapping(raw)
    connector = connector_config or {}
    selection = connector.get("browser_backend", connector.get("browser_selection"))
    if selection is None:
        selection = runtime_config.get("browser_default", runtime_config.get("browser_selection"))
    return registry.select(selection)[0] if selection is not None else None


def resolve_browser_backends(
    runtime_config: Mapping[str, Any], connector_config: Mapping[str, Any] | None = None
) -> list[BrowserBackendConfig]:
    """Resolve the complete ordered backend fallback list for a connector."""
    raw = runtime_config.get("browser_backends")
    if raw is None:
        return []
    registry = BrowserBackendRegistry.from_mapping(raw)
    connector = connector_config or {}
    selection = connector.get("browser_backend", connector.get("browser_selection"))
    if selection is None:
        selection = runtime_config.get("browser_default", runtime_config.get("browser_selection"))
    return registry.select(selection) if selection is not None else []


# ---------------------------------------------------------------------------
# Remote Camofox backend (unchanged)
# ---------------------------------------------------------------------------


class _RemoteCamofoxPage:
    def __init__(self, context: "_RemoteCamofoxContext") -> None:
        self._context = context
        self._tab_id: str | None = None

    async def goto(
        self, url: str, *, wait_until: str | None = None, timeout: int | None = None
    ) -> None:
        if self._tab_id is None:
            payload = {
                "userId": self._context.user_id,
                "sessionKey": self._context.session_key,
                "listItemId": self._context.session_key,
                "url": url,
            }
            data = await self._context._post("/tabs", payload, timeout=timeout)
            self._tab_id = str(data.get("tabId") or data.get("id") or "").strip() or None
            if self._tab_id is None:
                raise RuntimeError(f"Camofox did not return a tab id: {data}")
        else:
            await self._context._post(
                f"/tabs/{self._tab_id}/navigate",
                {
                    "userId": self._context.user_id,
                    "url": url,
                    "sessionKey": self._context.session_key,
                },
                timeout=timeout,
            )

    async def wait_for_timeout(self, timeout_ms: int) -> None:
        await self._context._wait(timeout_ms)

    async def content(self) -> str:
        if self._tab_id is None:
            raise RuntimeError("No tab open; call goto() first")
        snapshot = await self._context._get(
            f"/tabs/{self._tab_id}/snapshot",
            params={"userId": self._context.user_id, "format": "text"},
        )
        return str(snapshot.get("snapshot") or snapshot.get("text") or "")


class _RemoteCamofoxContext:
    def __init__(self, config: BrowserSessionConfig, *, client: httpx.AsyncClient) -> None:
        self._config = config
        self._client = client
        self._pages: list[_RemoteCamofoxPage] = []
        self.user_id = (config.camofox_user_id or "").strip() or f"pricerecon_{os.getpid()}"
        self.session_key = (config.camofox_session_key or "").strip() or "aliexpress"

    def _headers(self) -> dict[str, str]:
        token = (self._config.camofox_api_key or self._config.camofox_access_key or "").strip()
        return {"Authorization": f"Bearer {token}"} if token else {}

    async def _post(
        self, path: str, body: dict[str, Any], timeout: int | None = None
    ) -> dict[str, Any]:
        base_url = self._config.camofox_url
        assert base_url is not None
        response = await self._client.post(
            f"{base_url.rstrip('/')}{path}",
            json=body,
            headers=self._headers(),
            timeout=(timeout / 1000.0) if timeout else 60.0,
        )
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    async def _get(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        base_url = self._config.camofox_url
        assert base_url is not None
        response = await self._client.get(
            f"{base_url.rstrip('/')}{path}",
            params=params,
            headers=self._headers(),
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    async def _wait(self, timeout_ms: int) -> None:
        import asyncio

        await asyncio.sleep(max(timeout_ms, 0) / 1000.0)

    async def new_page(self) -> _RemoteCamofoxPage:
        page = _RemoteCamofoxPage(self)
        self._pages.append(page)
        return page

    async def add_cookies(self, cookies: list[dict[str, Any]]) -> None:
        base_url = self._config.camofox_url
        assert base_url is not None
        response = await self._client.post(
            f"{base_url.rstrip('/')}/sessions/{self.user_id}/cookies",
            json={"cookies": cookies},
            headers=self._headers(),
            timeout=60.0,
        )
        response.raise_for_status()

    async def close(self) -> None:
        base_url = self._config.camofox_url
        assert base_url is not None
        for page in self._pages:
            if page._tab_id:
                try:
                    await self._client.delete(
                        f"{base_url.rstrip('/')}/tabs/{page._tab_id}",
                        params={"userId": self.user_id},
                        headers=self._headers(),
                        timeout=30.0,
                    )
                except Exception:
                    pass
        self._pages.clear()


# ---------------------------------------------------------------------------
# BrowserClient
# ---------------------------------------------------------------------------


class BrowserClient:
    """Owns either a Playwright browser, the CloakBrowser patched binary, or a remote Camofox session."""

    def __init__(self, *, config: BrowserSessionConfig | None = None) -> None:
        self.config = config or BrowserSessionConfig()
        self._playwright: Any = None
        self._browser: Any = None
        self._remote_client: httpx.AsyncClient | None = None
        self._using_cloakbrowser: bool = False
        self._active_backend: BrowserBackendConfig | None = None

    def _configured_backends(self) -> list[BrowserBackendConfig]:
        registry = self.config.backend_registry()
        if registry is None:
            return []
        return registry.select(self.config.browser_selection or self.config.browser_default)

    def _apply_backend(self, backend: BrowserBackendConfig) -> None:
        self._active_backend = backend
        if backend.type == "camofox":
            self.config.camofox_url = backend.endpoint
            self.config.camofox_api_key = (
                str(backend.options.get("api_key", backend.options.get("access_key", ""))) or None
            )
            self.config.camofox_user_id = str(backend.options.get("user_id", "default"))
            self.config.camofox_session_key = str(backend.options.get("session_key", "default"))

    async def _start_backend(self, backend: BrowserBackendConfig) -> None:
        self._apply_backend(backend)
        if backend.type == "camofox":
            self._remote_client = httpx.AsyncClient(timeout=60.0)
            return
        if backend.type == "cloakbrowser":
            raise RuntimeError(
                "cloakbrowser named backend is fetch-only and cannot create a context"
            )
        if async_playwright is None:
            raise RuntimeError(f"Playwright is unavailable: {_PLAYWRIGHT_IMPORT_ERROR}")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.connect_over_cdp(backend.endpoint)

    def _uses_camofox(self) -> bool:
        return (
            self._active_backend is not None and self._active_backend.type == "camofox"
        ) or bool((self.config.camofox_url or "").strip())

    async def start(self) -> None:
        if (
            self._active_backend is not None
            or self._browser is not None
            or self._remote_client is not None
        ):
            return
        configured = self._configured_backends()
        if configured:
            failures: list[str] = []
            for backend in configured:
                try:
                    await self._start_backend(backend)
                    return
                except Exception as exc:
                    failures.append(f"{backend.name}: {exc}")
                    self._active_backend = None
                    if self._remote_client is not None:
                        await self._remote_client.aclose()
                        self._remote_client = None
                    if self._playwright is not None:
                        await self._playwright.stop()
                        self._playwright = None
            raise RuntimeError("all configured browser backends failed: " + "; ".join(failures))
        if self._uses_camofox():
            self._remote_client = httpx.AsyncClient(timeout=60.0)
            return
        if async_playwright is None:
            raise RuntimeError(f"Playwright is unavailable: {_PLAYWRIGHT_IMPORT_ERROR}")
        if self._browser is not None:
            return
        self._playwright = await async_playwright().start()
        # Playwright is always the primary browser. CloakBrowser is isolated in
        # the optional Node bridge and is only selected after block detection.
        self._browser = await self._playwright.chromium.launch(headless=self.config.headless)
        self._using_cloakbrowser = False

    async def close(self) -> None:
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None
        if self._remote_client is not None:
            await self._remote_client.aclose()
            self._remote_client = None
        self._using_cloakbrowser = False
        self._active_backend = None

    def _fingerprint_kwargs(self) -> dict[str, Any]:
        if FingerprintGenerator is None:
            return {}
        fingerprint = FingerprintGenerator().generate("chrome")
        return {
            "viewport": {
                "width": fingerprint.screen.width,
                "height": fingerprint.screen.height,
            },
            "user_agent": fingerprint.headers.get("User-Agent") or self.config.user_agent,
            "locale": self.config.locale,
            "timezone_id": self.config.timezone_id,
            "device_scale_factor": getattr(fingerprint.screen, "device_pixel_ratio", 1),
            "is_mobile": False,
        }

    async def new_context(self, *, cookies: list[dict[str, Any]] | None = None) -> Any:
        await self.start()
        if self._uses_camofox():
            assert self._remote_client is not None
            context = _RemoteCamofoxContext(self.config, client=self._remote_client)
            if cookies:
                await context.add_cookies(cookies)
            return context
        assert self._browser is not None
        context_kwargs: dict[str, Any] = {
            "viewport": {
                "width": self.config.viewport_width,
                "height": self.config.viewport_height,
            },
            "locale": self.config.locale,
            "timezone_id": self.config.timezone_id,
        }
        if not self._using_cloakbrowser:
            # CloakBrowser handles its own fingerprinting — do NOT override user_agent
            # when using the patched binary, as that breaks the anti-bot bypass.
            context_kwargs.update(self._fingerprint_kwargs())
            if self.config.user_agent:
                context_kwargs["user_agent"] = self.config.user_agent
        context = await self._browser.new_context(**context_kwargs)
        if cookies:
            await context.add_cookies(cookies)
        if stealth_async is not None and not self._using_cloakbrowser:
            try:
                await stealth_async(context)
            except Exception:
                pass
        return context

    async def fetch_with_fallback(
        self,
        url: str,
        *,
        wait_ms: int = 8000,
        nav_timeout: int = 45000,
    ) -> dict[str, Any]:
        """Fetch ``url``, falling back to CloakBrowser if the plain browser is blocked.

        Mirrors the Node helper's ``fetchWithFallback`` semantics in pure Python.
        Only active when ``config.cloakbrowser_fallback`` is True and the
        CloakBrowser binary is available.

        Returns a dict with keys: ``html``, ``title``, ``status``,
        ``used_cloakbrowser`` (bool), ``blocked`` (bool).
        """
        import asyncio

        async def _navigate(context: Any) -> tuple[str, str, int]:
            page = await context.new_page()
            status: int = 200

            def _on_response(response: Any) -> None:
                nonlocal status
                try:
                    if response.url == url:
                        status = response.status
                except Exception:
                    pass

            page.on("response", _on_response)
            page.set_default_navigation_timeout(nav_timeout)
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(wait_ms / 1000.0)
            title = await page.title()
            html = await page.content()
            await context.close()
            return html, title, status

        # Try plain browser first
        await self.start()
        try:
            context = await self.new_context()
            html, title, status = await _navigate(context)
        except Exception:
            html, title, status = "", "", 0

        blocked = is_blocked(html, title, status)

        if not blocked:
            return {
                "html": html,
                "title": title,
                "status": status,
                "used_cloakbrowser": self._using_cloakbrowser,
                "blocked": False,
                "primary_blocked": False,
                "primary_status": status,
            }

        # Blocked — try CloakBrowser fallback if available
        if not self.config.cloakbrowser_fallback:
            return {
                "html": html,
                "title": title,
                "status": status,
                "used_cloakbrowser": False,
                "blocked": True,
                "primary_blocked": True,
                "primary_status": status,
            }

        # The SDK bridge is optional and fail-closed. It is never selected
        # before the primary Playwright response is classified as blocked.
        bridge_result = await run_cloakbrowser_bridge(
            url,
            wait_ms=wait_ms,
            nav_timeout_ms=nav_timeout,
        )
        return {
            "html": str(bridge_result.get("html", "")),
            "content": str(bridge_result.get("content", "")),
            "title": str(bridge_result.get("title", "")),
            "status": int(bridge_result.get("status", 0)),
            "used_cloakbrowser": True,
            "blocked": bool(bridge_result.get("blocked", True)),
            "primary_blocked": True,
            "primary_status": status,
            "timing_ms": int(bridge_result.get("timing_ms", 0)),
            **({"error": bridge_result["error"]} if "error" in bridge_result else {}),
        }


@asynccontextmanager
async def browser_context(*, cookies: list[dict[str, Any]] | None = None) -> AsyncIterator[Any]:
    client = BrowserClient()
    context = await client.new_context(cookies=cookies)
    try:
        yield context
    finally:
        await context.close()
        await client.close()
