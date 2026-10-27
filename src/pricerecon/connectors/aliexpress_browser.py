"""Read-only AliExpress evidence. A displayed price is not a selected offer."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from decimal import Decimal
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from pricerecon.connectors.external_browser import ExternalBrowserResult

HOSTS = {"www.aliexpress.com", "aliexpress.com", "m.aliexpress.com"}
OPTION_NAMES = {
    "color": "dial",
    "colour": "dial",
    "dial": "dial",
    "movement": "movement",
    "strap": "strap",
    "band": "strap",
    "size": "size",
}
MONEY = re.compile(r"(GBP|USD|EUR|US\$|£|￡|€|\$)\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)")


def product_id(url: str) -> str | None:
    try:
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname not in HOSTS
            or parsed.username
            or parsed.password
            or parsed.port not in (None, 443)
        ):
            return None
    except ValueError:
        return None
    match = re.fullmatch(r"/item/(\d{10,20})\.html", parsed.path)
    return match[1] if match else None


def discovery_ids(result: ExternalBrowserResult) -> list[str]:
    """Read links, not IDs mentioned in scripts, adverts or arbitrary text."""
    if result.rendered.html_truncated or (
        not result.rendered.html and result.rendered.snapshot_truncated is not False
    ):
        raise ValueError("Partial browser content is not complete discovery evidence")
    hrefs: list[str] = []
    if result.rendered.html:
        soup = BeautifulSoup(result.rendered.html, "html.parser")
        hrefs = [str(node.get("href", "")) for node in soup.select("a[href]")]
    else:
        for line in result.rendered.snapshot.splitlines():
            if len(line) <= 2048 and (match := re.match(r"\s*- /url:\s*(.+)$", line)):
                hrefs.append(match[1].strip('"'))
    return list(
        dict.fromkeys(
            pid
            for href in hrefs
            if (pid := product_id(urljoin("https://www.aliexpress.com/", href)))
        )
    )


@dataclass(frozen=True)
class BrowserOfferEvidence:
    pid: str
    title: str | None
    displayed_price: Decimal | None
    currency: str | None
    selected_options: dict[str, str] = field(default_factory=dict)
    selected_sku: str | None = None
    price_bound_to_sku: bool = False
    destination: str | None = None
    shipping_claim: Decimal | None = None
    vat_included_claim: bool = False
    issues: tuple[str, ...] = ()
    quantity: int | None = None
    destination_literal: str | None = None

    @property
    def total_landed_cost(self) -> None:
        # No checkout/import-liability proof exists in this read-only protocol.
        return None

    def qualification_issues(self, requested: dict[str, str]) -> list[str]:
        issues = list(self.issues)
        if not self.selected_sku or not self.price_bound_to_sku:
            issues.append("selected_sku_price_unverified")
        for name in ("movement", "dial", "strap", "size"):
            actual, expected = self.selected_options.get(name), requested.get(name)
            if not actual or not expected:
                issues.append(f"{name}_unverified")
            elif actual.casefold().strip() != expected.casefold().strip():
                issues.append(f"{name}_mismatch")
        if requested.get("sku") and requested["sku"] != self.selected_sku:
            issues.append("sku_mismatch")
        if self.currency != "GBP" or self.displayed_price is None:
            issues.append("gbp_item_price_unverified")
        if self.destination != "GB":
            issues.append("uk_destination_unverified")
        if self.quantity != 1:
            issues.append("unit_quantity_unverified")
        return issues

    def summary(self) -> dict[str, object]:
        return {
            "pid": self.pid,
            "title": self.title,
            "displayed_price": (
                str(self.displayed_price) if self.displayed_price is not None else None
            ),
            "currency": self.currency,
            "selected_options": self.selected_options,
            "selected_sku": self.selected_sku,
            "price_bound_to_sku": self.price_bound_to_sku,
            "destination": self.destination,
            "destination_literal": self.destination_literal,
            "quantity": self.quantity,
            "shipping_claim": str(self.shipping_claim) if self.shipping_claim is not None else None,
            "vat_included_claim": self.vat_included_claim,
            "total_landed_cost": None,
            "issues": list(self.issues),
        }


@dataclass(frozen=True)
class BrowserSearchReport:
    discovery_url: str | None
    discovered_count: int
    inspected_count: int
    capped: bool
    offers: tuple[BrowserOfferEvidence, ...]


def money(text: str) -> tuple[Decimal | None, str | None]:
    match = MONEY.search(text)
    if not match:
        return None, None
    currency = {
        "£": "GBP",
        "￡": "GBP",
        "GBP": "GBP",
        "US$": "USD",
        "USD": "USD",
        "€": "EUR",
        "EUR": "EUR",
    }.get(match[1])
    # A bare dollar symbol is deliberately not converted to GBP or USD.
    return Decimal(match[2].replace(",", "")), currency


def parse_offer(pid: str, result: ExternalBrowserResult) -> BrowserOfferEvidence:
    title: str | None = None
    selected: dict[str, str] = {}
    sku: str | None = None
    bound = False
    price_text = ""
    issues: list[str] = []
    if result.rendered.html_truncated:
        issues.append("truncated_product_content")
    if not result.rendered.html and result.rendered.snapshot_truncated is not False:
        issues.append("partial_product_snapshot")
    if not result.rendered.final_url:
        issues.append("final_product_url_unverified")
    if result.rendered.final_url and product_id(result.rendered.final_url) != pid:
        issues.append("product_redirect_mismatch")
    if result.rendered.html:
        soup = BeautifulSoup(result.rendered.html, "html.parser")
        for node in soup.select("script,style,noscript,template"):
            node.decompose()
        titles = [node.get_text(" ", strip=True) for node in soup.select("h1")]
        title = next(
            (value for value in reversed(titles) if value.casefold() != "aliexpress"), None
        )
        # Only explicit current controls count. An option elsewhere in a SKU
        # list, the product title, or JSON-LD inventory is not a selection.
        for node in soup.select("input[checked],select"):
            name = OPTION_NAMES.get(str(node.get("name", "")).casefold())
            if name:
                value = node.get("value")
                if node.name == "select":
                    option = node.select_one("option[selected]")
                    value = option.get_text(" ", strip=True) if option else None
                if isinstance(value, str) and value.strip():
                    selected[name] = value.strip()
        for node in soup.select('[class*="sku-item--property"]'):
            label = node.get_text(" ", strip=True).replace("\xa0", " ")
            if match := re.match(
                r"^(Color|Colour|Dial|Movement|Strap|Band|Size):\s*(.{1,100})$",
                label,
                re.IGNORECASE,
            ):
                selected[OPTION_NAMES[match[1].casefold()]] = match[2].strip()
        sku_node = soup.select_one('input[name="skuId"],input[name="sku_id"]')
        if sku_node and re.fullmatch(r"\d{1,30}", str(sku_node.get("value", ""))):
            sku = str(sku_node["value"])
        price_node = soup.select_one('[class*="price--currentPriceText"],[data-current-price]')
        if price_node:
            price_text = price_node.get_text(" ", strip=True)
            bound = sku is not None and price_node.get("data-sku-id") == sku
        text = soup.get_text(" ", strip=True)
        quantity_node = soup.select_one('input[name="quantity"]')
        quantity = (
            int(str(quantity_node["value"]))
            if quantity_node and str(quantity_node.get("value", "")).isdigit()
            else None
        )
    else:
        lines = [line for line in result.rendered.snapshot.splitlines() if len(line) <= 300]
        heading = next(
            (
                i
                for i, line in enumerate(lines)
                if "heading" in line and "level=1" in line and '"Aliexpress"' not in line
            ),
            None,
        )
        if heading is not None:
            match = re.search(r'heading "(.+)".*\[level=1\]', lines[heading])
            title = match[1] if match else None
            # Inspect only the primary product section, never a review or a
            # recommendation's first price, or the entire page's first number.
            section = lines[heading : heading + 50]
            price_text = next((line for line in section if MONEY.search(line)), "")
            for line in section:
                text_match = re.fullmatch(r"\s*- text:\s*(.+)", line)
                if not text_match:
                    continue
                label = text_match[1]
                if label.startswith('"'):
                    try:
                        label = json.loads(label)
                    except json.JSONDecodeError:
                        continue
                if not isinstance(label, str):
                    continue
                if match := re.fullmatch(
                    r"(Color|Colour|Dial|Movement|Strap|Band|Size):\s*(.{1,100})",
                    label,
                    re.IGNORECASE,
                ):
                    selected[OPTION_NAMES[match[1].casefold()]] = match[2].strip()
        text = " ".join(lines)
        quantity_match = re.search(r'spinbutton "quantity"[^\n]*:\s*"?(\d+)', "\n".join(lines))
        quantity = int(quantity_match[1]) if quantity_match else None
    if not title:
        issues.append("product_title_unresolved")
    amount, currency = money(price_text)
    if amount is not None and (not amount.is_finite() or amount <= 0):
        amount = None
        issues.append("invalid_display_price")
    # A selected color label can itself expose a movement conflict. Never use
    # a VH31 title to overwrite an explicit 2035 label (observed live).
    movement = re.search(r"\b(VH31|VH65|2035|515)\b", " ".join(selected.values()), re.IGNORECASE)
    if movement and "movement" not in selected:
        selected["movement"] = movement[1].upper()
    destination = (
        "GB" if re.search(r"(?:Ship|Deliver) to:\s*United Kingdom\b", text, re.IGNORECASE) else None
    )
    shipping = Decimal(0) if re.search(r"\bShipping:\s*Free\b", text, re.IGNORECASE) else None
    return BrowserOfferEvidence(
        pid,
        title,
        amount,
        currency,
        selected,
        sku,
        bound,
        destination,
        shipping,
        bool(re.search(r"price includes VAT", text, re.IGNORECASE)),
        tuple(issues),
        quantity,
        (
            match[1].strip()
            if (match := re.search(r"(?:Ship|Deliver) to:\s*([^.;\n]{1,100})", text, re.IGNORECASE))
            else None
        ),
    )
