"""Deterministic browser-selection verification matrix.

This module deliberately exercises selection and retry policy without touching
production polling. A runner supplies bounded backend probes; the matrix emits
one evidence row per attempt and preserves discovery-vs-authoritative roles.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any, Callable, Iterable, Mapping, cast

from pricerecon.connectors.browser_client import BrowserBackendConfig, resolve_browser_backends


class FailureCategory(StrEnum):
    NONE = "none"
    BLOCKED = "blocked"
    TIMEOUT = "timeout"
    MALFORMED_RESPONSE = "malformed_response"
    BACKEND_UNAVAILABLE = "backend_unavailable"
    EMPTY_RESULT = "empty_result"
    ERROR = "error"


RETRYABLE = frozenset({FailureCategory.BLOCKED, FailureCategory.TIMEOUT, FailureCategory.BACKEND_UNAVAILABLE})


@dataclass(frozen=True, slots=True)
class ProbeResult:
    endpoint_class: str = "authoritative"
    http_status: int | None = 200
    page_outcome: str = "success"
    parsed_listing_count: int = 0
    elapsed_ms: int = 0
    failure: FailureCategory = FailureCategory.NONE


@dataclass(frozen=True, slots=True)
class MatrixRow:
    retailer: str
    connector: str
    configured_selection: str | list[str] | None
    selected_backend: str | None
    endpoint_class: str
    http_status: int | None
    page_outcome: str
    parsed_listing_count: int
    elapsed_ms: int
    failure_category: str
    attempt: int
    fell_through: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


Probe = Callable[[BrowserBackendConfig], ProbeResult]


def run_case(
    *, retailer: str, connector: str, runtime_config: Mapping[str, object],
    connector_config: Mapping[str, object] | None, probe: Probe,
) -> list[MatrixRow]:
    """Run a bounded selection case, retrying only documented retryable failures."""
    configured = cast(str | list[str] | None, (connector_config or {}).get("browser_backend", (connector_config or {}).get("browser_selection")))
    if configured is None:
        configured = cast(str | list[str] | None, runtime_config.get("browser_default", runtime_config.get("browser_selection")))
    backends = resolve_browser_backends(runtime_config, connector_config)
    rows: list[MatrixRow] = []
    if not backends:
        return [MatrixRow(retailer, connector, configured, None, "authoritative", None, "not_configured", 0, 0, FailureCategory.BACKEND_UNAVAILABLE.value, 1, False)]
    for attempt, backend in enumerate(backends, 1):
        result = probe(backend)
        rows.append(MatrixRow(retailer, connector, configured, backend.name, result.endpoint_class, result.http_status, result.page_outcome, result.parsed_listing_count, result.elapsed_ms, result.failure.value, attempt, attempt > 1))
        if result.failure not in RETRYABLE:
            break
    return rows


def run_matrix(cases: Iterable[Mapping[str, Any]], probes: Mapping[str, Probe]) -> list[dict[str, object]]:
    """Run cases; ``probes`` is keyed by connector id and keeps tests offline."""
    rows: list[dict[str, object]] = []
    for case in cases:
        connector = str(case["connector"])
        case_rows = run_case(
            retailer=str(case["retailer"]), connector=connector,
            runtime_config=cast(Mapping[str, object], case["runtime_config"]), connector_config=cast(Mapping[str, object] | None, case.get("connector_config")),
            probe=probes[connector],
        )
        rows.extend(row.as_dict() for row in case_rows)
    return rows
