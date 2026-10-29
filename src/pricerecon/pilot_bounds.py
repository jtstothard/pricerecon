"""Additional containment for the finite pilot, layered on DurableAdmission."""

import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from urllib.parse import unquote

import httpx

from pricerecon.core.rate_limiter import AdmissionDenied
from pricerecon.models.collection import OperatingPolicy

QUERIES = ("Addiesdive AD2066 Mint Green", "Casio MTP-B145D-2A2VEF")
MIB = 1024 * 1024


@dataclass
class PilotBounds:
    deadline: float = field(default_factory=lambda: time.monotonic() + 1200)
    response_bytes: int = 0
    requests: int = 0
    normalized_bytes: int = 0
    pages: int = 0
    details: int = 0
    token: str | None = field(default=None, repr=False)
    live_eligible: bool = False
    stopped: bool = False
    busy: bool = False
    seen: set[str] = field(default_factory=set)
    candidates: dict[str, str] = field(default_factory=dict)
    detail_counts: dict[str, int] = field(default_factory=dict)

    def deny(self, reason: str) -> None:
        self.stopped = True
        raise AdmissionDenied(reason, state="blocked")

    def check(self) -> None:
        if self.stopped:
            self.deny("pilot_stopped")
        if time.monotonic() >= self.deadline:
            self.deny("pilot_deadline")

    def normalized(self, size: int) -> None:
        self.check()
        if self.normalized_bytes + size > 2 * MIB:
            self.deny("pilot_normalized_cap")
        self.normalized_bytes += size

    def admit(self, request: httpx.Request) -> None:
        self.check()
        if request.extensions.get("collection_fallback") is True:
            self.deny("pilot_fallback_denied")
        url = request.url
        path = url.path
        allowed = url.scheme == "https" and url.host == "api.ebay.com" and url.port in (None, 443)
        allowed = allowed and not url.userinfo and "#" not in str(url)
        key = str(url)
        if request.method == "POST" and path == "/identity/v1/oauth2/token" and not url.query:
            pass
        elif request.method == "GET" and path == "/buy/browse/v1/item_summary/search":
            allowed = allowed and sorted(url.params.keys()) == ["filter", "limit", "q"]
            allowed = allowed and url.params.get("q") in QUERIES and url.params.get("limit") == "5"
            allowed = (
                allowed
                and url.params.get("filter")
                == "conditions:{NEW},buyingOptions:{FIXED_PRICE},deliveryCountry:GB"
            )
            if allowed:
                self.pages += 1
        elif request.method == "GET" and path.startswith("/buy/browse/v1/item/") and not url.query:
            item_id = unquote(path.removeprefix("/buy/browse/v1/item/"))
            subject = self.candidates.get(item_id)
            allowed = allowed and subject is not None
            if allowed and subject:
                count = self.detail_counts.get(subject, 0)
                if count >= 2:
                    self.deny("pilot_subject_detail_cap")
                self.detail_counts[subject] = count + 1
                self.details += 1
        else:
            allowed = False
        if not allowed:
            self.deny("pilot_route_denied")
        if key in self.seen or self.requests >= 7 or self.pages > 2 or self.details > 4:
            self.deny("pilot_request_cap_or_retry")
        self.seen.add(key)
        self.requests += 1


active_pilot: ContextVar[PilotBounds | None] = ContextVar("active_pilot", default=None)
pilot_transport: ContextVar[httpx.AsyncBaseTransport | None] = ContextVar(
    "pilot_transport", default=None
)


class PilotTransport(httpx.AsyncBaseTransport):
    """Consume bounded decoded chunks before HTTPX's ordinary eager read.

    All redirects and non-success statuses stop the entire lane. No transport
    retries, proxy, environment credentials, or fallback routing are configured.
    """

    def __init__(self, inner: httpx.AsyncBaseTransport, bounds: PilotBounds):
        self.inner = inner
        self.bounds = bounds

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        b = self.bounds
        if b.busy:
            b.deny("pilot_parallel_request")
        b.admit(request)
        b.busy = True
        try:
            response = await self.inner.handle_async_request(request)
            try:
                if not 200 <= response.status_code < 300:
                    b.deny("pilot_source_denied")
                if response.headers.get("content-encoding", "identity").lower() != "identity":
                    b.deny("pilot_compressed_response_denied")
                body = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    b.check()
                    b.response_bytes += len(chunk)
                    if len(body) + len(chunk) > 2 * MIB or b.response_bytes > 8 * MIB:
                        b.deny("pilot_response_cap")
                    body.extend(chunk)
                headers = dict(response.headers)
                headers.pop("content-encoding", None)
                headers.pop("content-length", None)
                return httpx.Response(response.status_code, headers=headers, content=bytes(body))
            finally:
                await response.aclose()
        except BaseException:
            b.stopped = True
            raise
        finally:
            b.busy = False

    async def aclose(self) -> None:
        await self.inner.aclose()


def pilot_policy() -> OperatingPolicy:
    """The two sequential connector attempts reserve 600s each, no refill."""
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    return OperatingPolicy.model_validate(
        {
            "scope_id": "watch-pilot-2026-10-28-once",
            "version": "live-pilot-plan-2026-10-28-v1",
            "owner_reference": "Codex active session; Jay approval 2026-10-28",
            "permission_reference": "reviewed standard search/getItem endpoint-access evidence required before live use",
            "retention_reference": "external transient retention evidence required before live use",
            "starts_at": now,
            "stops_at": now + timedelta(seconds=1200),
            "run_timeout_seconds": 600,
            "recovery_spacing_seconds": 0,
            "caps": {
                key: {"limit": value, "tracking_reserve": 0}
                for key, value in {
                    "requests": 7,
                    "pages": 2,
                    "details": 4,
                    "retries": 0,
                    "fallbacks": 0,
                    "browser_contexts": 0,
                    "browser_seconds": 0,
                    "ai_calls": 0,
                    "ai_tokens": 0,
                    "storage_bytes": 2 * MIB,
                    "elapsed_seconds": 1200,
                }.items()
            },
            "provider_request_caps": {"ebay": {"limit": 7, "tracking_reserve": 0}},
        }
    )
