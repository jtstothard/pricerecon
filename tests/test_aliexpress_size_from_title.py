"""Unit tests for the title-parsing helpers and the size gate they feed.

These cover the case-vs-strap disambiguation that MINOR 4 introduced and the
re-review found was a fail-open: a title like ``"Case 40mm Strap 20mm"`` must
resolve to the 40mm case, never the 20mm strap, because ``size`` is a fatal
qualification gate.
"""

from decimal import Decimal

from pricerecon.connectors.aliexpress_browser import (
    BrowserOfferEvidence,
    calibre_from_title,
    size_from_title,
)


def test_size_case_word_leading_wins_over_following_strap():
    assert size_from_title("Case 40mm Strap 20mm Diver Watch") == "40mm"


def test_size_case_word_with_colon_separator():
    assert size_from_title("Case:40mm Strap:20mm Diver Watch") == "40mm"


def test_size_case_word_trailing_wins_over_leading_strap():
    assert size_from_title("20mm strap 39mm case") == "39mm"


def test_size_case_word_mid_title():
    assert size_from_title("Men Watch Case 38mm Strap 20mm Sapphire") == "38mm"


def test_size_no_case_word_uses_first_two_digit_figure():
    # "Strap Width 22mm" is a compound strap label; the case is stated first.
    assert size_from_title("42mm Strap Width 22mm Automatic Watch") == "42mm"


def test_size_single_figure_is_the_case():
    assert size_from_title("San Martin 39mm NH34 Mechanical GMT Watch SN0109") == "39mm"


def test_size_decimal_case_qualified():
    assert size_from_title("38.5mm Case 20mm Strap") == "38.5mm"


def test_size_bare_three_digit_is_not_a_case():
    # A bare 105mm is a box/shipping dimension, not a case diameter.
    assert size_from_title("Watch 105mm box shipping") is None


def test_size_case_qualified_three_digit_is_accepted():
    # The title itself asserts the dimension, so a 3-digit case is trusted.
    assert size_from_title("Oversized 105mm case dive watch") == "105mm"


def test_size_no_dimension_returns_none():
    assert size_from_title("Mechanical wristwatch no dimensions") is None


def test_calibre_rejects_marketing_style_number():
    assert calibre_from_title("New 2024 515 Style") is None


def test_calibre_rejects_piece_count():
    assert calibre_from_title("39mm watch 2824 pieces") is None


def test_calibre_accepts_real_movement_number():
    assert calibre_from_title("San Martin 39mm NH34 Automatic") == "NH34"


def test_gate_40mm_case_never_satisfies_20mm_request():
    # The fail-open the re-review caught: with the old parser the title's strap
    # width (20mm) was recorded as the case size, so a 20mm request matched a
    # 40mm-case listing with zero issues. The fix records 40mm, so the gate
    # must now reject the 20mm request.
    title = "Case 40mm Strap 20mm Diver Watch"
    offer = BrowserOfferEvidence(
        pid="1",
        title=title,
        displayed_price=Decimal("10.00"),
        currency="GBP",
        selected_options={"size": size_from_title(title) or ""},
    )
    assert offer.selected_options["size"] == "40mm"
    assert "size_mismatch" in offer.qualification_issues({"size": "20mm"})


def test_gate_40mm_case_satisfies_40mm_request():
    title = "Case 40mm Strap 20mm Diver Watch"
    offer = BrowserOfferEvidence(
        pid="1",
        title=title,
        displayed_price=Decimal("10.00"),
        currency="GBP",
        selected_options={"size": size_from_title(title) or ""},
    )
    assert "size_mismatch" not in offer.qualification_issues({"size": "40mm"})
