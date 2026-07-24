"""Tests for token-based title matching (ADR 0001)."""

from pricerecon.core.title_matching import (
    _normalize_title,
    _single_token_matches,
    _phrase_matches,
    _term_matches,
    synonym_groups_match,
    legacy_query_match,
    matches_watch_spec,
)


def test_normalize_title():
    """Title normalization to tokens."""
    assert _normalize_title("AMD Ryzen AI Max+ 395 128GB Mini PC") == [
        "amd",
        "ryzen",
        "ai",
        "max+",
        "395",
        "128gb",
        "mini",
        "pc",
    ]
    assert _normalize_title("Mac Studio Ultra 256GB") == ["mac", "studio", "ultra", "256gb"]
    # "128 GB" -> "128gb"
    assert _normalize_title("128 GB") == ["128gb"]
    # Hyphen -> space
    assert _normalize_title("strix-halo") == ["strix", "halo"]


def test_single_token_matches():
    """Single tokens match as complete tokens."""
    tokens = ["amd", "ryzen", "ai", "max+", "395", "128gb", "mini", "pc"]

    # Exact token matches
    assert _single_token_matches("128gb", tokens)
    assert _single_token_matches("max+", tokens)
    assert _single_token_matches("395", tokens)

    # 395+ is NOT a token in this list (title has "395" not "395+")
    assert not _single_token_matches("395+", tokens)

    # Partial matches fail (prevents 1280gb matching 128gb)
    assert not _single_token_matches("1280gb", tokens)
    assert not _single_token_matches("3950", tokens)


def test_phrase_matches():
    """Multi-word phrases match as contiguous sequences."""
    tokens = ["amd", "ryzen", "ai", "max+", "395", "128gb", "mini", "pc"]

    # Contiguous phrase matches
    assert _phrase_matches("ryzen ai", tokens)
    assert _phrase_matches("ai max+", tokens)
    assert _phrase_matches("amd ryzen ai max+", tokens)

    # Non-contiguous fails
    assert not _phrase_matches("ryzen 395", tokens)
    assert not _phrase_matches("amd pc", tokens)


def test_term_matches():
    """Terms match as single tokens or phrases."""
    tokens = ["amd", "ryzen", "ai", "max+", "395", "128gb", "mini", "pc"]

    # Single token
    assert _term_matches("128gb", tokens)
    assert not _term_matches("1280gb", tokens)

    # Multi-word phrase
    assert _term_matches("ryzen ai", tokens)
    assert not _term_matches("ryzen pc", tokens)


def test_synonym_groups_match_basic():
    """Basic OR-within-group, AND-across-groups semantics."""
    synonym_groups = [
        ["strix halo", "ryzen ai max", "ai max+ 395", "395+"],
        ["128gb"],
    ]
    excluded_terms = ["iphone", "ipad"]

    # Matches: one term from each group
    assert synonym_groups_match(
        "AMD Ryzen AI Max+ 395 128GB Mini PC", synonym_groups, excluded_terms
    )
    assert synonym_groups_match("Strix Halo 128GB", synonym_groups, excluded_terms)

    # Fails: missing 128gb
    assert not synonym_groups_match("AMD Ryzen AI Max+ 395 Mini PC", synonym_groups, excluded_terms)
    # Fails: 1280gb != 128gb (token boundary)
    assert not synonym_groups_match("Ryzen AI 395+ 1280GB", synonym_groups, excluded_terms)


def test_synonym_groups_match_exclusions():
    """Excluded terms prevent matching."""
    synonym_groups = [
        ["strix halo", "ryzen ai max"],
        ["128gb"],
    ]
    excluded_terms = ["iphone", "ipad", "macbook"]

    # Matches
    assert synonym_groups_match("Strix Halo 128GB", synonym_groups, excluded_terms)

    # Excluded term present
    assert not synonym_groups_match("iPhone 128GB", synonym_groups, excluded_terms)
    assert not synonym_groups_match("MacBook Pro 128GB", synonym_groups, excluded_terms)


def test_synonym_groups_match_empty():
    """Empty synonym_groups always pass."""
    assert synonym_groups_match("Any Title", [], None)
    assert synonym_groups_match("Any Title", [], ["excluded"])


def test_legacy_query_match():
    """Legacy query matching: all terms must appear."""
    assert legacy_query_match("AMD Ryzen AI Max+ 395 128GB Mini PC", "ryzen 128gb")
    assert not legacy_query_match("AMD Ryzen AI Max+ 395 Mini PC", "ryzen 128gb")


def test_special_chars_preserved():
    """Special chars like + are preserved in tokens."""
    synonym_groups = [["395+"], ["128gb"]]

    # Exact match with +
    assert synonym_groups_match("AMD Ryzen AI Max+ 395+ 128GB", synonym_groups, None)

    # Without + fails (395 != 395+)
    assert not synonym_groups_match("AMD Ryzen AI Max 395 128GB", synonym_groups, None)


def test_capacity_boundary():
    """Capacity matching respects token boundaries (ADR 0001 key requirement)."""
    synonym_groups = [["128gb"]]

    # Exact 128gb match
    assert synonym_groups_match("Mac Studio 128GB", synonym_groups, None)

    # 1280gb != 128gb
    assert not synonym_groups_match("Mac Studio 1280GB", synonym_groups, None)

    # 128 is not 128gb
    assert not synonym_groups_match("Mac Studio 128", synonym_groups, None)


def test_matches_watch_spec_with_spec_match():
    """matches_watch_spec integrates with SpecMatch model."""
    from pricerecon.models.watches import SpecMatch

    spec = SpecMatch(
        synonym_groups=[["ryzen ai max", "strix halo"], ["128gb"]],
        excluded_title_terms=["iphone", "ipad"],
    )

    assert matches_watch_spec("AMD Ryzen AI Max 128GB Mini PC", spec)
    assert not matches_watch_spec("iPhone 128GB", spec)


def test_matches_watch_spec_with_watch_synonym_groups():
    """Watch-level synonym_groups override spec_match."""
    from pricerecon.models.watches import SpecMatch

    spec = SpecMatch(excluded_title_terms=["iphone"])

    # Watch-level groups take priority
    watch_synonym_groups = [["ryzen ai max"], ["128gb"]]
    assert matches_watch_spec("AMD Ryzen AI Max 128GB", spec, watch_synonym_groups)
    assert not matches_watch_spec("AMD Ryzen AI Max 1280GB", spec, watch_synonym_groups)


def test_matches_watch_spec_legacy_fallback():
    """Fallback to required_title_terms for backward compatibility."""
    from pricerecon.models.watches import SpecMatch

    spec = SpecMatch(
        required_title_terms=["ryzen", "128gb"],
        excluded_title_terms=["iphone"],
    )

    assert matches_watch_spec("AMD Ryzen AI Max 128GB", spec)
    assert not matches_watch_spec("iPhone 128GB", spec)
    assert not matches_watch_spec("AMD Ryzen AI Max 1280GB", spec)


def test_complex_strix_halo_example():
    """Full example from ADR 0001: Strix Halo 128GB watch."""
    synonym_groups = [
        ["strix halo", "ryzen ai max", "ai max+ 395", "395+"],
        ["128gb"],
    ]
    excluded_terms = ["iphone", "ipad", "android", "galaxy", "pixel", "phone", "tablet"]

    # Real matches (chipset name, not marketing name)
    assert synonym_groups_match(
        "AMD Ryzen AI Max+ 395 128GB Mini PC", synonym_groups, excluded_terms
    )
    assert synonym_groups_match("Strix Halo 128GB", synonym_groups, excluded_terms)

    # False positives prevented
    assert not synonym_groups_match("iPhone 128GB", synonym_groups, excluded_terms)
    assert not synonym_groups_match("Galaxy S23 128GB", synonym_groups, excluded_terms)

    # Wrong capacity
    assert not synonym_groups_match(
        "AMD Ryzen AI Max+ 395 192GB Mini PC", synonym_groups, excluded_terms
    )


def test_mac_studio_ultra_example():
    """Mac Studio Ultra 256GB example."""
    synonym_groups = [
        ["mac studio", "ultra"],
        ["256gb"],
    ]
    excluded_terms = ["macbook", "imac", "mac mini", "iphone", "ipad"]

    # Matches
    assert synonym_groups_match("Mac Studio Ultra 256GB", synonym_groups, excluded_terms)

    # Wrong product
    assert not synonym_groups_match("MacBook Pro 256GB", synonym_groups, excluded_terms)
    assert not synonym_groups_match("iMac 256GB", synonym_groups, excluded_terms)

    # Wrong capacity
    assert not synonym_groups_match("Mac Studio Ultra 512GB", synonym_groups, excluded_terms)
