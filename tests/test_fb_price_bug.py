"""Test for Facebook Marketplace USD price parsing bug.

Bug: USD prices in listing titles are incorrectly extracted as fragments.
The glue-price fallback regex matched arbitrary digit runs in titles
(e.g. "128GB", "16-inch") when no GBP marker was present.

Fix: extract_visible_gbp_price() now returns None when the text contains
a non-GBP currency marker ($, USD, EUR, …) and no explicit GBP amount,
instead of falling back to the glued-price regex.
"""

from decimal import Decimal

from pricerecon.connectors.price import extract_visible_gbp_price


class TestFBMarketplacePriceBug:
    """Regression for t_e0564506: USD prices must not produce GBP fragments."""

    def test_usd_price_returns_none_1(self):
        """$3,100 USD with "Workstation 300" in title → None (was £300)."""
        title = "Corsair AI Workstation 300 Desktop PC - AMD Strix Halo Ryzen AI Max 395+ 128GB UNIFIED RAM 4TB SSD"
        body_text = "$3,100"
        combined = f"{title} {body_text}"
        assert extract_visible_gbp_price(combined) is None

    def test_usd_price_returns_none_2(self):
        """$2,900 USD with "395+" in title → None (was £395)."""
        title = "Gmktec Evo-X2 AMD Ryzen 395+ 128GB RAM, 1TB mini pc"
        body_text = "$2,900"
        combined = f"{title} {body_text}"
        assert extract_visible_gbp_price(combined) is None

    def test_usd_price_returns_none_3(self):
        """$6,800 USD with "128GB" in title → None (was £128)."""
        title = '128GB M5 Max MacBook Pro 16" (open to trade)'
        body_text = "$6,800"
        combined = f"{title} {body_text}"
        assert extract_visible_gbp_price(combined) is None

    def test_usd_price_returns_none_4(self):
        """$4,960 USD with "16-inch" in title → None (was £16)."""
        title = "Apple MacBook Pro 16-inch M5 Max 128GB RAM 2TB SSD"
        body_text = "$4,960"
        combined = f"{title} {body_text}"
        assert extract_visible_gbp_price(combined) is None

    def test_gbp_price_extracted_correctly(self):
        """Control: Proper GBP prices are still extracted correctly."""
        combined = "Apple MacBook Pro 16-inch £4,960 M5 Max 128GB RAM 2TB SSD"
        assert extract_visible_gbp_price(combined) == Decimal("4960")

    def test_no_price_returns_none(self):
        """Control: Text with no price-like digits returns None."""
        combined = "Apple MacBook Pro M5 Max Silver"
        assert extract_visible_gbp_price(combined) is None

    def test_gbp_takes_priority_over_usd(self):
        """When both GBP and USD are present, GBP wins."""
        combined = "$4,960 Apple MacBook Pro 16-inch £4,960 M5 Max 128GB RAM 2TB SSD"
        assert extract_visible_gbp_price(combined) == Decimal("4960")

    def test_usd_only_no_gbp_returns_none(self):
        """Pure USD listing with no GBP marker returns None."""
        assert extract_visible_gbp_price("$3,100") is None

    def test_glued_gbp_still_works_without_foreign_currency(self):
        """Glued-price fallback still works when no foreign currency is present."""
        # No $, EUR, etc. — glued regex should still find a price.
        assert extract_visible_gbp_price("Great deal 4999 today only") == Decimal("4999")
