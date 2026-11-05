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
    # Which selected options were read out of the seller-authored h1 title
    # rather than off a displayed control. The evidence lane claims these as
    # seller statements, never as visible observations (see aliexpress.py).
    title_derived: frozenset[str] = field(default_factory=frozenset)

    @property
    def total_landed_cost(self) -> None:
        # No checkout/import-liability proof exists in this read-only protocol.
        return None

    def qualification_issues(self, requested: dict[str, str]) -> list[str]:
        """Fatal issues: the offer must not enter price comparison."""
        issues = list(self.issues)
        if self.selected_sku and not self.price_bound_to_sku:
            # A page that exposes a selected SKU must bind the price to it;
            # an unbound price on such a page is a misbinding risk.
            issues.append("selected_sku_price_unverified")
        for name in ("movement", "dial", "strap", "size"):
            actual, expected = self.selected_options.get(name), requested.get(name)
            if not expected:
                continue  # nothing requested for this dimension: nothing to fail on
            if not actual:
                issues.append(f"{name}_unverified")
            elif actual.casefold().strip() != expected.casefold().strip():
                issues.append(f"{name}_mismatch")
        if requested.get("sku") and requested["sku"] != self.selected_sku:
            issues.append("sku_mismatch")
        if self.currency != "GBP" or self.displayed_price is None:
            issues.append("gbp_item_price_unverified")
        if self.quantity is not None and self.quantity != 1:
            # An explicit multi-unit quantity makes the displayed price misleading.
            issues.append("unit_quantity_conflict")
        return issues

    def verification_warnings(self, requested: dict[str, str]) -> list[str]:
        """Non-fatal verification gaps, recorded on the listing but not gating."""
        warnings: list[str] = []
        if not self.selected_sku:
            warnings.append("selected_sku_unverified")
        for name in ("movement", "dial", "strap", "size"):
            if not requested.get(name) and name not in self.selected_options:
                warnings.append(f"{name}_unverified")
        if self.destination != "GB":
            warnings.append("uk_destination_unverified")
        if self.quantity is None:
            warnings.append("unit_quantity_unverified")
        return warnings

    def summary(self) -> dict[str, object]:
        return {
            "pid": self.pid,
            "title": self.title,
            "displayed_price": (
                str(self.displayed_price) if self.displayed_price is not None else None
            ),
            "currency": self.currency,
            "selected_options": self.selected_options,
            "title_derived": sorted(self.title_derived),
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


# A PDP title is marketing prose: a bare number may be a calibre, a marketing
# counter ("New 2024 515 Style") or a piece count ("2824 pieces"). A number
# sitting against one of these words counts styles or pieces, never a
# movement, so it is not a calibre.
_MARKETING_NEIGHBOURS = frozenset(
    {
        "style",
        "styles",
        "piece",
        "pieces",
        "pcs",
        "design",
        "designs",
        "pattern",
        "patterns",
        "pack",
        "packs",
        "lot",
        "lots",
    }
)
_TITLE_CALIBRE = re.compile(
    r"\b(?:NH3[4-9]|7S26|7S36|4R35|4R36|VK6[34]|PT5000|9015|9039|2824|2892|"
    r"HZ64\d{2}|VH3[15]|VH65|2035|515|MIYOTA\s*\d{4})\b",
    re.IGNORECASE,
)


def calibre_from_title(title: str) -> str | None:
    """The first title token that is a calibre, not a marketing number.

    ``"New 2024 515 Style"`` must not yield ``515`` and ``"39mm watch 2824
    pieces"`` must not yield ``2824``: those numbers are qualified by a
    marketing word and count styles or pieces. A real calibre is not written
    that way ("San Martin 39mm NH34 Automatic ..."), so only the words
    immediately around the token are examined.
    """
    for match in _TITLE_CALIBRE.finditer(title):
        before = title[: match.start()].casefold().split()
        after = title[match.end() :].casefold().split()
        neighbours = set()
        if before:
            neighbours.add(before[-1].strip(".,-/"))
        if after:
            neighbours.add(after[0].strip(".,-/"))
        if neighbours & _MARKETING_NEIGHBOURS:
            continue
        return match.group(0)
    return None


# Case diameter is an identity dimension; a strap or band width is a different
# measurement of the same watch, and both read as "NNmm" in one title.
_DIMENSION_TOKEN = re.compile(
    r"\b(\d{2,3}(?:[.,]\d+)?)\s?mm\b"
    r"|\b(case|cases|strap|straps|band|bands|bracelet|bracelets|lugs?|bezel)\b",
    re.IGNORECASE,
)
_STRAP_WORDS = frozenset(
    {"strap", "straps", "band", "bands", "bracelet", "bracelets", "lug", "lugs"}
)
_CASE_WORDS = frozenset({"case", "cases"})
_THICKNESS_WORDS = frozenset({"thick", "thickness"})


def _integer_digits(value: str) -> int:
    return len(value.split(".", 1)[0])


def _plain_gap(text: str) -> bool:
    """Immediate adjacency: whitespace/colon/dash only, no comma, no words."""
    return re.fullmatch(r"[\s:\-]*", text) is not None


def _lead_gap(text: str) -> bool:
    """Gap between a case word and the figure it leads: no comma; whitespace,
    colon or dash, optionally with a single qualifier word (``Case Diameter
    40mm``). A comma means the case word is a noun, not a size label."""
    if "," in text:
        return False
    return _plain_gap(text) or re.fullmatch(r"[\s:\-]*[A-Za-z]+[\s:\-]+", text) is not None


def size_from_title(title: str) -> str | None:
    """The case size stated in a PDP title, never the strap width.

    The anchor is directional. A figure is the case size when a ``case`` word
    *introduces* it (``Case 40mm``, ``Case: 40mm``, ``Case Diameter 40mm``) or
    *immediately follows* it (``38.5mm Case``, ``105mm case``). A single
    ``case`` word sitting between two figures is adjacent to both, so a
    non-directional anchor is ambiguous exactly when it matters most.

    Fail-open guards:

    * When a figure immediately precedes the case word, that case word is a
      trailing label for the preceding figure; a strap-trailed leading figure
      is then the strap, not the case, so it is rejected (``40mm case 20mm
      strap`` -> ``40mm``, never ``20mm``).
    * A figure immediately followed by a thickness word is a case thickness,
      not a diameter, so it is rejected (``Case 12mm thick 40mm diameter`` ->
      ``None``).
    * When the anchored set is ambiguous, return ``None`` rather than falling
      through to a positional first-figure rule.

    Only when the title carries no case word at all does the watch-title
    convention apply: the first two-digit figure that is not a strap width.
    The two-digit bound keeps a ``105mm`` box or shipping dimension out.
    """
    figures: list[tuple[int, int, str]] = []
    case_words: list[tuple[int, int]] = []
    strap_words: list[tuple[int, int]] = []
    for match in _DIMENSION_TOKEN.finditer(title):
        if match[1] is not None:
            figures.append((match.start(), match.end(), match[1]))
        else:
            word = match[2].casefold()
            if word in _CASE_WORDS:
                case_words.append((match.start(), match.end()))
            elif word in _STRAP_WORDS:
                strap_words.append((match.start(), match.end()))

    def followed_by_thickness(figure: tuple[int, int, str]) -> bool:
        after = title[figure[1] :].casefold().split()
        return bool(after) and after[0].strip(".,:-") in _THICKNESS_WORDS

    def strap_trails(figure: tuple[int, int, str]) -> bool:
        return any(
            figure[1] <= start and _plain_gap(title[figure[1] : start])
            for start, _end in strap_words
        )

    def strap_leads(figure: tuple[int, int, str]) -> bool:
        return any(
            end <= figure[0] and _plain_gap(title[end : figure[0]]) for _start, end in strap_words
        )

    def figure_immediately_precedes(pos: int) -> bool:
        return any(end <= pos and _plain_gap(title[end:pos]) for _start, end, _v in figures)

    if case_words:
        # Tier 1: leading anchor — the figure a case word introduces.
        accepted: list[tuple[int, int, str]] = []
        for case_start, case_end in case_words:
            for figure in figures:
                if figure[0] >= case_end and _lead_gap(title[case_end : figure[0]]):
                    if followed_by_thickness(figure):
                        break
                    if figure_immediately_precedes(case_start) and strap_trails(figure):
                        break
                    accepted.append(figure)
                    break
        distinct = {figure[2] for figure in accepted}
        if len(distinct) == 1:
            return accepted[0][2].replace(",", ".") + "mm"
        if len(distinct) > 1:
            return None
        # Tier 2: trailing anchor — the figure a case word immediately follows.
        trails = [
            figure
            for figure in figures
            for case_start, _case_end in case_words
            if figure[1] <= case_start and _plain_gap(title[figure[1] : case_start])
        ]
        distinct = {figure[2] for figure in trails}
        if len(distinct) == 1:
            return trails[0][2].replace(",", ".") + "mm"
        return None

    # No case word: watch titles state the case size first. First two-digit
    # figure that is not a strap width.
    for figure in figures:
        if _integer_digits(figure[2]) == 2 and not strap_leads(figure):
            return figure[2].replace(",", ".") + "mm"
    return None


def parse_offer(pid: str, result: ExternalBrowserResult) -> BrowserOfferEvidence:
    title: str | None = None
    selected: dict[str, str] = {}
    title_derived: set[str] = set()
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
                # Only an explicit SKU label counts; an arbitrary number in the
                # accessibility tree is never a selected SKU.
                if match := re.fullmatch(r"SKU(?: ID)?:\s*(\d{6,30})", label, re.IGNORECASE):
                    sku = match[1]
        text = " ".join(lines)
        joined = "\n".join(lines)
        quantity_match = re.search(r'spinbutton "quantity"[^\n]*:\s*"?(\d+)', joined)
        if not quantity_match:
            # Observed live (2026-11-04): the quantity spinner is a labelled
            # textbox, e.g. "- text: Quantity" followed by '- textbox [e22]: "1"'.
            quantity_match = re.search(
                r"-\s*text:\s*Quantity[^\n]*\n(?:\s*-\s*img[^\n]*\n)*"
                r'\s*-\s*(?:textbox|spinbutton)[^\n]*:\s*"?(\d+)"?',
                joined,
            )
        quantity = int(quantity_match[1]) if quantity_match else None
    if not title:
        issues.append("product_title_unresolved")
    amount, currency = money(price_text)
    if amount is not None and (not amount.is_finite() or amount <= 0):
        amount = None
        issues.append("invalid_display_price")
    # A quantity pack row ("Color: 1 piece") is a bundle size, never a dial:
    # recording it would masquerade as verified dial evidence (observed live).
    if re.fullmatch(r"\d+\s?pieces?", selected.get("dial", ""), re.IGNORECASE):
        selected.pop("dial")
    # A selected color label can itself expose a movement conflict. Never use
    # a VH31 title to overwrite an explicit 2035 label (observed live).
    movement = re.search(r"\b(VH31|VH65|2035|515)\b", " ".join(selected.values()), re.IGNORECASE)
    if movement and "movement" not in selected:
        selected["movement"] = movement[1].upper()
    if "movement" not in selected and title:
        # PDP titles assert calibres ("San Martin 39mm NH34 ..."). Only used
        # when no explicit selected label carries a movement; an explicit
        # label always wins (same doctrine as the VH31/2035 rule above).
        caliber = calibre_from_title(title)
        if caliber:
            selected["movement"] = caliber.upper()
            title_derived.add("movement")
    if "size" not in selected and title:
        # PDP titles state case size ("... 39mm ..."); PDP-level evidence, and
        # only recorded when the seller's own SKU properties did not.
        size = size_from_title(title)
        if size:
            selected["size"] = size
            title_derived.add("size")
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
        frozenset(title_derived),
    )
