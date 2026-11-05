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


# --- Re-review #3 blocking table: Strap-first ordering (commonest AliExpress
# spec form). The non-directional anchor returned the strap width here, a
# fail-open where a 40mm-case listing satisfied a 20mm request with zero issues.


def test_size_strap_first_label_ordering():
    assert size_from_title("Strap 20mm Case 40mm Diver Watch") == "40mm"


def test_size_strap_first_with_colons():
    assert size_from_title("Strap: 20mm Case: 40mm Automatic Watch") == "40mm"


def test_size_strap_width_case_diameter():
    assert size_from_title("Strap Width 20mm Case Diameter 40mm Watch") == "40mm"


def test_size_strap_first_mid_title():
    assert size_from_title("Men Watch Strap 20mm Case 40mm Sapphire Crystal") == "40mm"


def test_size_band_first_case_second():
    assert size_from_title("Leather band 20mm case 40mm automatic") == "40mm"


def test_size_case_as_noun_not_a_size_label():
    # "case," with a comma is a noun, not a size label; no case diameter stated.
    assert size_from_title("Stainless steel case, 20mm strap, 22mm lugs") is None


def test_size_case_only_no_diameter():
    assert size_from_title("Case only Strap 20mm") is None


# --- Ambiguous orderings: the case word is a trailing label, so a strap-trailed
# leading figure is the strap and must be rejected.


def test_size_case_word_trailing_rejects_strap_trailed_lead():
    assert size_from_title("40mm case 20mm strap") == "40mm"


def test_size_case_word_trailing_after_strap():
    assert size_from_title("40mm strap 20mm case") == "20mm"


def test_size_small_case_large_strap():
    assert size_from_title("20mm case 40mm strap") == "20mm"


# --- Thickness guard: a figure followed by a thickness word is not a diameter.


def test_size_thickness_is_not_diameter():
    assert size_from_title("Case 12mm thick 40mm diameter 20mm strap") is None


# --- Glued token: "Case40mm" has no word boundary, so the case word is invisible
# and the strap fallback must not grab the strap width.


def test_size_glued_case_token_does_not_grab_strap():
    assert size_from_title("Case40mm Strap 20mm") is None


# --- Gate-level proof for the Strap-first ordering: a 20mm request against a
# 40mm-case title must now produce size_mismatch, never an empty issue list.


def test_gate_strap_first_40mm_case_never_satisfies_20mm_request():
    title = "Strap 20mm Case 40mm Diver Watch"
    offer = BrowserOfferEvidence(
        pid="1",
        title=title,
        displayed_price=Decimal("10.00"),
        currency="GBP",
        selected_options={"size": size_from_title(title) or ""},
    )
    assert offer.selected_options["size"] == "40mm"
    assert "size_mismatch" in offer.qualification_issues({"size": "20mm"})


def test_gate_strap_first_40mm_case_satisfies_40mm_request():
    title = "Strap Width 20mm Case Diameter 40mm Watch"
    offer = BrowserOfferEvidence(
        pid="1",
        title=title,
        displayed_price=Decimal("10.00"),
        currency="GBP",
        selected_options={"size": size_from_title(title) or ""},
    )
    assert "size_mismatch" not in offer.qualification_issues({"size": "40mm"})


# --- Re-review #4 fail-open: a strap-led preceding figure must not make the
# case word a trailing label. "Strap 20mm Case 40mm ..." — the 20mm is already
# the strap, so "Case" leads 40mm; the veto must not reject it.


def test_size_strap_led_preceding_does_not_veto_leading_case():
    assert size_from_title("Strap 20mm Case 40mm Strap 22mm") == "40mm"


def test_size_strap_led_preceding_with_bracelet():
    assert size_from_title("Watch Strap 20mm Case 40mm Bracelet Silver") == "40mm"


def test_size_silicone_strap_case_bracelet():
    assert size_from_title("Silicone Strap 20mm Case 40mm Bracelet 22mm Men Watch") == "40mm"


def test_size_leather_strap_case_band():
    assert size_from_title("Leather Strap 20mm Case 40mm Band Brown Automatic") == "40mm"


def test_size_strap_case_lugs():
    assert size_from_title("Strap 20mm Case 40mm Lugs 22mm Diver Watch") == "40mm"


def test_size_strap_case_strap_minimal():
    assert size_from_title("Strap 20mm Case 40mm Strap") == "40mm"


def test_gate_strap_led_preceding_40mm_never_satisfies_20mm_request():
    title = "Strap 20mm Case 40mm Strap 22mm"
    offer = BrowserOfferEvidence(
        pid="1",
        title=title,
        displayed_price=Decimal("10.00"),
        currency="GBP",
        selected_options={"size": size_from_title(title) or ""},
    )
    assert offer.selected_options["size"] == "40mm"
    assert "size_mismatch" in offer.qualification_issues({"size": "20mm"})
