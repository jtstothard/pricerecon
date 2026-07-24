"""Strict matching and source routing for GLM hardware watches.

These routes deliberately prefer false negatives over returning a plausible-looking
but wrong device (for example CeX's broad storage-only matches).
"""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class HardwareRoute:
    name: str
    required_terms: tuple[str, ...]
    excluded_terms: tuple[str, ...]
    allowed_sources: frozenset[str]
    required_any_terms: tuple[str, ...] = ()


_COMMON_EXCLUDES = (
    "iphone",
    "ipad",
    "android",
    "galaxy",
    "pixel",
    "phone",
    "tablet",
    "accessory",
    "case",
    "cover",
    "charger",
)

ROUTES: tuple[HardwareRoute, ...] = (
    HardwareRoute(
        name="strix-halo-128gb",
        required_terms=("strix", "halo", "128gb"),
        excluded_terms=("192gb", "64gb", "256gb", "macbook", "mac studio", *_COMMON_EXCLUDES),
        allowed_sources=frozenset(
            {"ebay", "cex", "facebook_marketplace", "gumtree", "reddit_hardwareswapuk"}
        ),
    ),
    HardwareRoute(
        name="strix-halo-192gb",
        required_terms=("strix", "halo", "192gb"),
        excluded_terms=("128gb", "64gb", "256gb", "macbook", "mac studio", *_COMMON_EXCLUDES),
        allowed_sources=frozenset(
            {"ebay", "cex", "facebook_marketplace", "gumtree", "reddit_hardwareswapuk"}
        ),
    ),
    HardwareRoute(
        name="strix-halo-128-or-192gb",
        required_terms=("strix", "halo"),
        required_any_terms=("128gb", "192gb"),
        excluded_terms=("64gb", "256gb", "macbook", "mac studio", *_COMMON_EXCLUDES),
        allowed_sources=frozenset(
            {"ebay", "cex", "facebook_marketplace", "gumtree", "reddit_hardwareswapuk"}
        ),
    ),
    HardwareRoute(
        name="mac-studio-ultra-256gb",
        required_terms=("mac studio", "ultra", "256gb"),
        excluded_terms=(
            "128gb",
            "192gb",
            "512gb",
            "macbook",
            "imac",
            "mac mini",
            *_COMMON_EXCLUDES,
        ),
        allowed_sources=frozenset({"ebay", "cex", "gumtree", "facebook_marketplace"}),
    ),
    HardwareRoute(
        name="mac-studio-ultra-512gb",
        required_terms=("mac studio", "ultra", "512gb"),
        excluded_terms=(
            "128gb",
            "192gb",
            "256gb",
            "macbook",
            "imac",
            "mac mini",
            *_COMMON_EXCLUDES,
        ),
        allowed_sources=frozenset({"ebay", "cex", "gumtree", "facebook_marketplace"}),
    ),
    HardwareRoute(
        name="mac-studio-ultra-256-or-512gb",
        required_terms=("mac studio", "ultra"),
        required_any_terms=("256gb", "512gb"),
        excluded_terms=("128gb", "192gb", "macbook", "imac", "mac mini", *_COMMON_EXCLUDES),
        allowed_sources=frozenset({"ebay", "cex", "gumtree", "facebook_marketplace"}),
    ),
    HardwareRoute(
        name="macbook-pro-m5-max-128gb",
        required_terms=("macbook", "pro", "m5", "max", "128gb"),
        excluded_terms=(
            "m4",
            "m3",
            "m2",
            "air",
            "imac",
            "mac mini",
            "mac studio",
            *_COMMON_EXCLUDES,
        ),
        allowed_sources=frozenset({"ebay", "cex", "gumtree", "facebook_marketplace"}),
    ),
)


def _normalize(text: str) -> str:
    """Normalize marketplace spelling without weakening product boundaries."""
    normalized = " ".join(text.casefold().replace("-", " ").split())
    # Treat "128 GB" and "128GB" as the same capacity, while retaining the
    # complete numeric token so a generic "128" cannot satisfy a route.
    return re.sub(r"(?<=\d)\s+(?=gb\b)", "", normalized)


def route_for_query(query: str) -> HardwareRoute | None:
    normalized = _normalize(query)
    compact = normalized.replace(" ", "")
    # Queries such as "256/512GB" describe an either/or watch. Resolve them
    # before the single-capacity routes, whose terms may otherwise substring
    # match the final capacity.
    if (
        "mac studio" in normalized
        and "ultra" in normalized
        and ("256/512gb" in compact or "512/256gb" in compact)
    ):
        return next(route for route in ROUTES if route.name == "mac-studio-ultra-256-or-512gb")
    if (
        "strix" in normalized
        and "halo" in normalized
        and ("128/192gb" in compact or "192/128gb" in compact)
    ):
        return next(route for route in ROUTES if route.name == "strix-halo-128-or-192gb")
    for route in ROUTES:
        if (
            all(term in normalized for term in route.required_terms)
            and (
                not route.required_any_terms
                or any(term in normalized for term in route.required_any_terms)
            )
            and not any(term in normalized for term in route.excluded_terms)
        ):
            return route
    return None


def route_title_matches(title: str, route: HardwareRoute) -> bool:
    normalized = _normalize(title)
    return (
        all(term in normalized for term in route.required_terms)
        and (
            not route.required_any_terms
            or any(term in normalized for term in route.required_any_terms)
        )
        and not any(term in normalized for term in route.excluded_terms)
    )
