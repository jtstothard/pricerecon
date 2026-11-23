"""CeX listing URLs must use the product-detail/?id=<boxId> form.

The old /product-detail/<slug>/<boxId>.html form returns 404 on uk.webuy.com.
"""

from pricerecon.connectors.cex import CexConnector


def _hit(**overrides: object) -> dict[str, object]:
    hit: dict[str, object] = {
        "boxId": "SMEM16G48001",
        "boxName": "16GB PC5-38400 DDR5 4800MTs 262 Pin Memory",
        "sellPrice": 120,
        "stores": ["Online"],
        "inStockOnline": True,
    }
    hit.update(overrides)
    return hit


def test_cex_url_uses_id_query_form() -> None:
    listing = CexConnector()._parse_hit(_hit())
    assert listing is not None
    assert listing.url == "https://uk.webuy.com/product-detail/?id=SMEM16G48001"


def test_cex_url_ignores_slug() -> None:
    listing = CexConnector()._parse_hit(_hit(slug="16gb-pc5-38400-ddr5"))
    assert listing is not None
    assert listing.url == "https://uk.webuy.com/product-detail/?id=SMEM16G48001"


def test_cex_url_encodes_box_id() -> None:
    listing = CexConnector()._parse_hit(_hit(boxId="A B/1&x"))
    assert listing is not None
    assert listing.url == "https://uk.webuy.com/product-detail/?id=A+B%2F1%26x"
