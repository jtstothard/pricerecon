"""Supplied runtime policy context; this module cannot activate a source."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from pricerecon.models.collection import OperatingPolicy

_policy: ContextVar[OperatingPolicy | None] = ContextVar("collection_policy", default=None)


def current_policy() -> OperatingPolicy | None:
    return _policy.get()


@contextmanager
def operating_policy(policy: OperatingPolicy | None) -> Iterator[None]:
    token = _policy.set(policy)
    try:
        yield
    finally:
        _policy.reset(token)
