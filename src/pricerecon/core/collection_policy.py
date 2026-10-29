"""Supplied runtime policy context; this module cannot activate a source."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from pricerecon.models.collection import OperatingPolicy

_policy: ContextVar[OperatingPolicy | None] = ContextVar("collection_policy", default=None)


def supplied_policy() -> OperatingPolicy | None:
    return _policy.get()


def current_policy(connection: sqlite3.Connection | None = None) -> OperatingPolicy | None:
    from pricerecon.core.rate_limiter import AdmissionDenied, DurableAdmission

    selection = DurableAdmission.select_policy(connection)
    if selection.reason:
        raise AdmissionDenied(selection.reason, state="blocked")
    return selection.policy


@contextmanager
def operating_policy(policy: OperatingPolicy | None) -> Iterator[None]:
    token = _policy.set(policy)
    try:
        yield
    finally:
        _policy.reset(token)
