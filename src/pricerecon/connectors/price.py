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
# Detect any currency marker so the glued-price fallback does not fire on
# foreign-currency listings (USD, EUR, AUD, etc.).  The glued regex is a
# last-resort guess and must never run when an explicit non-GBP price is present.
_FOREIGN_CURRENCY_RE = re.compile(r"\$|USD|EUR|€|AUD|CAD", flags=re.IGNORECASE)


def extract_visible_gbp_price(text: str) -> Decimal | None:
    """Return the first visibly marked or clearly glued GBP amount in free-form text.

    Returns ``None`` when the text contains a non-GBP currency marker (``$``,
    ``USD``, ``EUR``, …) and no explicit GBP amount — the glued-price fallback
    must not invent a GBP value from a foreign-currency listing.
    """

    normalized = text.replace("\xa0", " ").strip()
    match = _GBP_VISIBLE_PRICE_RE.search(normalized)
    if not match:
        # Only fall back to the glued-price regex when there is no evidence of
        # a foreign currency.  Without this guard the regex matches arbitrary
        # digit runs in titles (e.g. "128GB", "16-inch") and returns fragments.
        if _FOREIGN_CURRENCY_RE.search(normalized):
            return None
        match = _GBP_GLUED_PRICE_RE.search(normalized)
    if not match:
        return None
    try:
        return Decimal(match.group("amount").replace(",", ""))
    except InvalidOperation:
        return None
