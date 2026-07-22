"""Shared browser client utilities for browser-based connectors.

Supports either a local Playwright browser, a remote Camofox REST backend,
or the CloakBrowser patched Chromium binary (anti-bot bypass).
"""

from __future__ import annotations

import glob
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import httpx

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
    camofox_url: str | None = None
    camofox_user_id: str | None = None
    camofox_session_key: str | None = None
    camofox_api_key: str | None = None
    camofox_access_key: str | None = None
    # CloakBrowser backend
    use_cloakbrowser: bool = field(default=False)
    cloakbrowser_fallback: bool = field(default=True)

    def __post_init__(self) -> None:
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

    def _uses_camofox(self) -> bool:
        return bool((self.config.camofox_url or "").strip())

    async def start(self) -> None:
        if self._uses_camofox():
            if self._remote_client is None:
                self._remote_client = httpx.AsyncClient(timeout=60.0)
            return
        if async_playwright is None:
            raise RuntimeError(f"Playwright is unavailable: {_PLAYWRIGHT_IMPORT_ERROR}")
        if self._browser is not None:
            return
        self._playwright = await async_playwright().start()

        cloakbrowser_path: str | None = None
        if self.config.use_cloakbrowser:
            cloakbrowser_path = resolve_cloakbrowser_binary()
            if cloakbrowser_path is None:
                # Binary missing — degrade silently to plain Playwright
                pass

        if cloakbrowser_path:
            self._browser = await self._playwright.chromium.launch(
                headless=self.config.headless,
                executable_path=cloakbrowser_path,
            )
            self._using_cloakbrowser = True
        else:
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
            }

        # Blocked — try CloakBrowser fallback if available
        if not self.config.cloakbrowser_fallback:
            return {
                "html": html,
                "title": title,
                "status": status,
                "used_cloakbrowser": False,
                "blocked": True,
            }

        cloak_path = resolve_cloakbrowser_binary()
        if cloak_path is None:
            return {
                "html": html,
                "title": title,
                "status": status,
                "used_cloakbrowser": False,
                "blocked": True,
            }

        # Close existing browser, reopen with CloakBrowser binary
        await self.close()
        assert self._playwright is None
        if async_playwright is None:
            raise RuntimeError(f"Playwright is unavailable: {_PLAYWRIGHT_IMPORT_ERROR}")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.config.headless,
            executable_path=cloak_path,
        )
        self._using_cloakbrowser = True

        context = await self._browser.new_context(
            viewport={
                "width": self.config.viewport_width,
                "height": self.config.viewport_height,
            },
            locale=self.config.locale,
            timezone_id=self.config.timezone_id,
        )
        html, title, status = await _navigate(context)
        blocked_after = is_blocked(html, title, status)

        return {
            "html": html,
            "title": title,
            "status": status,
            "used_cloakbrowser": True,
            "blocked": blocked_after,
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
