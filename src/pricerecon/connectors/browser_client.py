"""Shared Playwright browser client utilities for browser-based connectors."""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator

try:
    from browserforge.fingerprints import FingerprintGenerator  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    FingerprintGenerator = None  # type: ignore[assignment]

try:
    from playwright.async_api import async_playwright  # type: ignore
except Exception as exc:  # pragma: no cover - optional dependency
    async_playwright = None  # type: ignore[assignment]
    _PLAYWRIGHT_IMPORT_ERROR = exc
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


class BrowserClient:
    """Owns a Playwright browser and spawns contexts with optional stealth."""

    def __init__(self, *, config: BrowserSessionConfig | None = None) -> None:
        self.config = config or BrowserSessionConfig()
        self._playwright: Any = None
        self._browser: Any = None

    async def start(self) -> None:
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
        assert self._browser is not None
        context_kwargs: dict[str, Any] = {
            "viewport": {"width": self.config.viewport_width, "height": self.config.viewport_height},
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
