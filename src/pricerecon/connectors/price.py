"""Shared price parsing helpers for messy marketplace text."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re

_GBP_VISIBLE_PRICE_RE = re.compile(
    r"(?<!\w)(?:£|GBP\s*)(?P<amount>\d[\d,]*(?:\.\d{1,2})?)",
    flags=re.IGNORECASE,
)
_GBP_GLUED_PRICE_RE = re.compile(
    r"(?<!\w)(?:£|GBP\s*)?(?P<amount>\d{2,}(?:[\d,]*(?:\.\d{1,2})?))(?=[^\d]|$)",
    flags=re.IGNORECASE,
)


def extract_visible_gbp_price(text: str) -> Decimal | None:
    """Return the first visibly marked or clearly glued GBP amount in free-form text."""

    normalized = text.replace("\xa0", " ").strip()
    match = _GBP_VISIBLE_PRICE_RE.search(normalized) or _GBP_GLUED_PRICE_RE.search(normalized)
    if not match:
        return None
    try:
        return Decimal(match.group("amount").replace(",", ""))
    except InvalidOperation:
        return None
