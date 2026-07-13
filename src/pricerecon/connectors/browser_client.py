"""Shared browser client utilities for browser-based connectors.

Supports either a local Playwright browser or a remote Camofox REST backend.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
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


class BrowserClient:
    """Owns either a Playwright browser or a remote Camofox session."""

    def __init__(self, *, config: BrowserSessionConfig | None = None) -> None:
        self.config = config or BrowserSessionConfig()
        self._playwright: Any = None
        self._browser: Any = None
        self._remote_client: httpx.AsyncClient | None = None

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
        self._browser = await self._playwright.chromium.launch(headless=self.config.headless)

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
        context_kwargs.update(self._fingerprint_kwargs())
        if self.config.user_agent:
            context_kwargs["user_agent"] = self.config.user_agent
        context = await self._browser.new_context(**context_kwargs)
        if cookies:
            await context.add_cookies(cookies)
        if stealth_async is not None:
            try:
                await stealth_async(context)
            except Exception:
                pass
        return context


@asynccontextmanager
async def browser_context(*, cookies: list[dict[str, Any]] | None = None) -> AsyncIterator[Any]:
    client = BrowserClient()
    context = await client.new_context(cookies=cookies)
    try:
        yield context
    finally:
        await context.close()
        await client.close()
