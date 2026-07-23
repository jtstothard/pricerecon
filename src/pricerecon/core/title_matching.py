"""Token-based title matching with phrase support.

Implements ADR 0001: synonym groups with OR-within-group, AND-across-groups.
Tokens are complete units after normalization — prevents "128gb" matching "1280gb".
Special characters like "+" are preserved as part of tokens.
"""

from __future__ import annotations

import re
from typing import Any


def _normalize_title(title: str) -> list[str]:
    """Normalize title to tokens.

    - Lowercase
    - Replace hyphens/dashes with spaces
    - Collapse "128 GB" → "128gb" for capacity matching
    - Split into tokens on non-alphanumeric (except + for things like "395+")
    """
    normalized = " ".join(title.casefold().replace("-", " ").split())
    # Normalize capacity patterns like "128 GB" to "128gb"
    normalized = re.sub(r"(?<=\d)\s+(?=gb\b)", "", normalized)
    # Split on non-alphanumeric, but preserve + as part of tokens
    tokens = re.split(r"[^a-z0-9+]+", normalized)
    return [token for token in tokens if token]


def _single_token_matches(term: str, title_tokens: list[str]) -> bool:
    """Check if a single token term matches as a complete token."""
    normalized_term = term.casefold().replace(" ", "")
    return normalized_term in title_tokens


def _phrase_matches(phrase: str, title_tokens: list[str]) -> bool:
    """Check if a multi-word phrase appears as a contiguous sequence."""
    phrase_tokens = _normalize_title(phrase)
    if not phrase_tokens:
        return False
    # Find first token, then check if rest follow contiguously
    for i, token in enumerate(title_tokens):
        if token == phrase_tokens[0]:
            if title_tokens[i:i+len(phrase_tokens)] == phrase_tokens:
                return True
    return False


def _term_matches(term: str, title_tokens: list[str]) -> bool:
    """Check if a term matches (single token or phrase)."""
    normalized_term = term.casefold()
    term_tokens = _normalize_title(normalized_term)
    if len(term_tokens) == 1:
        # Single token: match as complete token
        return _single_token_matches(term_tokens[0], title_tokens)
    else:
        # Multi-word phrase: match as contiguous sequence
        return _phrase_matches(normalized_term, title_tokens)


def synonym_groups_match(
    title: str,
    synonym_groups: list[list[str]],
    excluded_terms: list[str] | None = None,
) -> bool:
    """Check if title matches synonym groups (OR-within-group, AND-across-groups).

    A listing title must contain at least one term from every synonym group
    to pass. Excluded terms must NOT appear.

    Args:
        title: Listing title to check
        synonym_groups: List of synonym groups (each group is OR, groups are AND)
        excluded_terms: Terms that must NOT appear in the title

    Returns:
        True if title matches all groups and excludes all excluded_terms

    Example:
        synonym_groups: [["strix halo", "ryzen ai max", "ai max+ 395", "395+"], ["128gb"]]
        excluded_terms: ["iphone", "ipad"]

        "AMD Ryzen AI Max+ 395 128GB Mini PC" → True
        "Strix Halo 128GB" → True
        "Strix Halo 192GB" → False (no 128gb match)
        "Ryzen AI 395+ 1280GB" → False (128gb doesn't match 1280gb)
    """
    if not synonym_groups:
        return True

    title_tokens = _normalize_title(title)

    # Check excluded terms first (fail fast)
    excluded_terms = excluded_terms or []
    for excluded_term in excluded_terms:
        if _term_matches(excluded_term, title_tokens):
            return False

    # Check each synonym group (all must match)
    for group in synonym_groups:
        if not group:
            continue
        # OR-within-group: at least one term in the group must match
        group_matched = any(_term_matches(term, title_tokens) for term in group)
        if not group_matched:
            return False

    return True


def legacy_query_match(title: str, query: str) -> bool:
    """Legacy fallback: match if all query terms appear in title.

    Used for watches without synonym_groups. Preserves existing behavior.
    """
    terms = [term for term in re.split(r"[^a-z0-9]+", query.lower()) if term]
    if not terms:
        return True
    haystack = title.casefold()
    return all(term in haystack for term in terms)


def matches_watch_spec(
    listing_title: str,
    spec_match: Any,
    watch_synonym_groups: list[list[str]] | None = None,
) -> bool:
    """Check if a listing matches watch spec matching rules.

    Prioritizes synonym_groups if present; otherwise falls back to
    required_title_terms for backward compatibility.

    Args:
        listing_title: Title of the listing to check
        spec_match: SpecMatch object or dict with matching rules
        watch_synonym_groups: Optional synonym_groups from watch level

    Returns:
        True if listing matches all spec rules
    """
    match_dict = (
        spec_match.model_dump() if hasattr(spec_match, "model_dump") else (spec_match or {})
    )
    if not match_dict:
        return True

    title_tokens = _normalize_title(listing_title)

    # Check excluded terms (always active)
    excluded_terms = match_dict.get("excluded_title_terms", []) or []
    for excluded_term in excluded_terms:
        if _term_matches(excluded_term, title_tokens):
            return False

    # Prioritize watch-level synonym_groups if present
    if watch_synonym_groups:
        return synonym_groups_match(listing_title, watch_synonym_groups, excluded_terms)

    # Fall back to spec_match.synonym_groups if present
    spec_synonym_groups = match_dict.get("synonym_groups", []) or []
    if spec_synonym_groups:
        return synonym_groups_match(listing_title, spec_synonym_groups, excluded_terms)

    # Final fallback: legacy required_title_terms behavior
    required_terms = match_dict.get("required_title_terms", []) or []
    if required_terms:
        # Legacy AND semantics: all terms must appear
        return all(_term_matches(term, title_tokens) for term in required_terms)

    return True