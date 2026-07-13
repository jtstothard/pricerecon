"""HTML parsing helpers for retailer connectors."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin
import re

from selectolax.parser import HTMLParser, Node

from pricerecon.models import NormalizedListing, SourceType, StockState
from .specs import extract_specs

_PRICE_RE = re.compile(r"(?P<currency>£|GBP|\$|EUR|€)?\s*(?P<amount>\d+(?:,\d{3})*(?:\.\d{2})?)")


@dataclass(slots=True)
class SelectorConfig:
    card: str
    title: str
    price: str
    url: str
    stock: str | None = None
    image: str | None = None
    id: str | None = None
    pagination_next: str | None = None
    dedupe: bool = True
    stock_in: tuple[str, ...] = field(
        default=("in stock", "available", "dispatch", "add to basket", "buy now")
    )
    stock_out: tuple[str, ...] = field(
        default=("out of stock", "sold out", "unavailable", "coming soon", "pre-order", "preorder")
    )


def parse_price(text: str) -> Decimal | None:
    match = _PRICE_RE.search(text.replace("\xa0", " "))
    if not match:
        return None
    try:
        return Decimal(match.group("amount").replace(",", ""))
    except InvalidOperation:
        return None


def _text(node: Node | None) -> str:
    return re.sub(r"\s+", " ", node.text(separator=" ", strip=True) if node else "").strip()


def _first(node: Node, selector: str) -> Node | None:
    return node.css_first(selector) if selector else None


def _stock_state(text: str, config: SelectorConfig) -> tuple[bool | None, StockState | None]:
    lowered = text.lower()
    if any(token in lowered for token in config.stock_in):
        return True, StockState.IN_STOCK
    if any(token in lowered for token in config.stock_out):
        return False, StockState.OUT_OF_STOCK
    return None, None


def parse_listings_from_html(
    html: str,
    *,
    base_url: str,
    source: str,
    source_type: SourceType,
    selector: SelectorConfig,
    category: str | None = None,
) -> list[NormalizedListing]:
    parser = HTMLParser(html)
    listings: list[NormalizedListing] = []

    for card in parser.css(selector.card):
        title_node = _first(card, selector.title)
        price_node = _first(card, selector.price)
        url_node = _first(card, selector.url)
        if not (title_node and price_node and url_node):
            continue

        title = _text(title_node)
        price = parse_price(_text(price_node))
        href = url_node.attributes.get("href") if url_node.attributes else None
        if price is None or not href:
            continue

        stock_text = _text(_first(card, selector.stock)) if selector.stock else ""
        in_stock, stock_state = _stock_state(stock_text, selector) if stock_text else (None, None)
        image_url = None
        if selector.image:
            image_node = _first(card, selector.image)
            if image_node:
                image_url = image_node.attributes.get("src") or image_node.attributes.get(
                    "data-src"
                )
                if image_url:
                    image_url = urljoin(base_url, image_url)

        listing_id = None
        if selector.id:
            id_node = _first(card, selector.id)
            if id_node:
                listing_id = id_node.attributes.get("data-id") or _text(id_node) or None
        if not listing_id:
            listing_id = href.rstrip("/").split("/")[-1]

        listings.append(
            NormalizedListing(
                source=source,
                source_type=source_type,
                source_listing_id=listing_id,
                title_raw=title,
                price=price,
                currency="GBP",
                url=urljoin(base_url, href),
                product_normalized=None,
                variant_normalized=extract_specs(title, category),
                condition=None,
                condition_raw=None,
                shipping_cost=None,
                total_landed_cost=None,
                seller_or_store=None,
                seller_feedback_score=None,
                seller_feedback_pct=None,
                location=None,
                in_stock=in_stock,
                stock_state=stock_state,
                image_url=image_url,
                exact_variant_confirmed=None,
                variant_match_confidence=None,
                mismatch_flags=None,
                risk_flags=None,
                category=category,
            )
        )

    return listings
