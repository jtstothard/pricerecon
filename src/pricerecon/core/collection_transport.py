"""HTTP attempt hook, including redirects, auth, retries and fallback requests.

Only mapped HTTP lanes are admitted. Browser origin subrequests/local native
transports cannot yet be bounded here and remain gated under a supplied policy.
"""

from contextvars import ContextVar

import httpx
from pydantic import TypeAdapter

from pricerecon.core.rate_limiter import AdmissionDenied, DurableAdmission
from pricerecon.models.collection import Resource

active_admission: ContextVar[DurableAdmission | None] = ContextVar("active_admission", default=None)


def debit_resources(**costs: int) -> None:
    admission = active_admission.get()
    if admission:
        admission.debit(TypeAdapter(dict[Resource, int]).validate_python(costs))


def require_bounded_browser() -> None:
    if active_admission.get():
        raise AdmissionDenied("browser_origin_accounting_unavailable", state="blocked")


async def account_request(request: httpx.Request) -> None:
    admission = active_admission.get()
    if admission is None:
        return
    key = f"{request.method} {request.url}"
    previous = admission.requests.get(key, 0)
    path = request.url.path
    costs: dict[Resource, int] = {"requests": 1}
    if "search" in path or "item_summary" in path:
        costs["pages"] = 1
    elif "/item/" in path or "/item.get" in path:
        costs["details"] = 1
    elif "oauth2" not in path:
        raise AdmissionDenied("request_classification_required", state="blocked")
    if previous:
        costs["retries"] = 1
    if request.extensions.get("collection_fallback") is True:
        costs["fallbacks"] = 1
    admission.debit(costs)
    admission.requests[key] = previous + 1


def collection_http_client(
    *, timeout: float = 30.0, transport: httpx.AsyncBaseTransport | None = None
) -> httpx.AsyncClient:
    """Public HTTPX event hooks run before each transport send/redirect."""
    return httpx.AsyncClient(
        event_hooks={"request": [account_request]}, timeout=timeout, transport=transport
    )
