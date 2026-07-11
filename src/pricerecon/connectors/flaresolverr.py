"""FlareSolverr-compatible HTML fetch client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(slots=True)
class FlareSolverrResult:
    response: str
    status: int | None = None
    headers: dict[str, str] | None = None
    url: str | None = None


class FlareSolverrClient:
    """Minimal client for any FlareSolverr-compatible endpoint."""

    def __init__(self, endpoint: str, timeout: float = 90.0) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    async def request_html(self, url: str, *, max_timeout: int = 60000) -> str:
        payload = {"cmd": "request.get", "url": url, "maxTimeout": max_timeout}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.endpoint, json=payload)
            response.raise_for_status()
            data: dict[str, Any] = response.json()

        solution = data.get("solution") or {}
        html = solution.get("response")
        if not isinstance(html, str):
            raise ValueError("FlareSolverr response missing solution.response HTML")
        return html
