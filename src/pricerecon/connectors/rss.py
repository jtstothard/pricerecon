"""Shared RSS/Atom parsing and YAML template connector support."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal, Optional
import re
import xml.etree.ElementTree as ET

import httpx
import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from pricerecon.connectors.base import BaseConnector
from pricerecon.connectors.price import extract_visible_gbp_price
from pricerecon.models import NormalizedListing, SourceType

ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
}


class FeedEntry(BaseModel):
    """Normalized RSS/Atom feed entry."""

    id: str
    title: str
    link: str
    content: str = ""
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    raw_xml: Optional[str] = None


class ResponseParserConfig(BaseModel):
    """Response parser configuration for a YAML template."""

    kind: Literal["rss", "atom"] = "atom"


class FieldMapping(BaseModel):
    """Target field mapping for connector templates."""

    source_listing_id: str = "id"
    title_raw: str = "title"
    url: str = "link"
    content: str = "content"
    author: str = "author"
    timestamp_seen: str = "published_at"


class ConnectorTemplateConfig(BaseModel):
    """YAML connector template definition."""

    source: str
    display_name: Optional[str] = None
    source_role: SourceType
    endpoint_url: str
    request_method: str = Field(default="GET")
    request_headers: dict[str, str] = Field(default_factory=dict)
    response_parser: ResponseParserConfig = Field(default_factory=ResponseParserConfig)
    field_mapping: FieldMapping = Field(default_factory=FieldMapping)
    item_css_selector: Optional[str] = None
    item_xpath: Optional[str] = None
    query_param_name: str = Field(default="query")

    @field_validator("request_method")
    @classmethod
    def normalize_method(cls, value: str) -> str:
        value = value.upper()
        if value not in {"GET", "POST"}:
            raise ValueError("request_method must be GET or POST")
        return value

    @model_validator(mode="after")
    def validate_template(self) -> "ConnectorTemplateConfig":
        if not self.source.strip():
            raise ValueError("source is required")
        if not self.endpoint_url.strip():
            raise ValueError("endpoint_url is required")
        return self


class TemplateConnector(BaseConnector):
    """Generic connector built from a YAML template."""

    def __init__(self, template: ConnectorTemplateConfig):
        self.template = template
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def source_role(self) -> SourceType:
        return self.template.source_role

    @property
    def connector_id(self) -> str:
        return self.template.source

    async def initialize(self) -> None:
        self._client = httpx.AsyncClient(timeout=30.0)

    async def cleanup(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def search(
        self,
        query: str,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[NormalizedListing]:
        filters = filters or {}
        url = self._render_url(query=query, filters=filters)
        entries = await self.fetch_entries(url)
        return [self._entry_to_listing(entry) for entry in entries]

    async def fetch_entries(self, url: str) -> list[FeedEntry]:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        response = await self._client.request(
            self.template.request_method,
            url,
            headers=self.template.request_headers or None,
        )
        response.raise_for_status()
        return parse_feed(response.text)

    def _render_url(self, *, query: str, filters: dict[str, Any]) -> str:
        limit = filters.get("limit") or 25
        return self.template.endpoint_url.format(query=query, limit=limit)

    def _entry_to_listing(self, entry: FeedEntry) -> NormalizedListing:
        if self.template.source == "reddit_hardwareswapuk":
            parsed = parse_hardwareswapuk_post(entry.title, entry.content, entry.author, entry.link)
            return NormalizedListing(
                schema_version="1.0",
                source=self.template.source,
                source_type=self.template.source_role,
                source_listing_id=parsed["source_listing_id"],
                title_raw=parsed["title_raw"],
                price=parsed["price"],
                currency="GBP",
                url=parsed["url"],
                timestamp_seen=entry.published_at or datetime.now(timezone.utc),
                product_normalized=None,
                variant_normalized=parsed.get("variant_normalized"),
                condition=None,
                condition_raw=parsed.get("condition_raw"),
                shipping_cost=None,
                total_landed_cost=None,
                seller_or_store=parsed.get("seller_or_store"),
                seller_feedback_score=None,
                seller_feedback_pct=None,
                location=parsed.get("location"),
                in_stock=True,
                stock_state=None,
                image_url=None,
                exact_variant_confirmed=None,
                variant_match_confidence=None,
                mismatch_flags=None,
                risk_flags=None,
                category=None,
            )

        price = _extract_price(entry.title, entry.content) or Decimal("0")
        retailer = _extract_retailer(entry.title, entry.content)
        source_listing_id = entry.id or entry.link or entry.title
        return NormalizedListing(
            schema_version="1.0",
            source=self.template.source,
            source_type=self.template.source_role,
            source_listing_id=source_listing_id,
            title_raw=entry.title,
            price=price,
            currency="GBP",
            url=entry.link,
            timestamp_seen=entry.published_at or datetime.now(timezone.utc),
            product_normalized=None,
            variant_normalized={"query": entry.title} if self.template.source_role == SourceType.SIGNAL else None,
            condition=None,
            condition_raw=None,
            shipping_cost=None,
            total_landed_cost=None,
            seller_or_store=retailer or entry.author,
            seller_feedback_score=None,
            seller_feedback_pct=None,
            location=None,
            in_stock=None if self.template.source_role == SourceType.SIGNAL else True,
            stock_state=None,
            image_url=None,
            exact_variant_confirmed=None,
            variant_match_confidence=None,
            mismatch_flags=None,
            risk_flags=None,
            category=None,
        )


@dataclass(slots=True)
class ParsedHardwareSwapPost:
    source_listing_id: str
    title_raw: str
    price: Decimal
    url: str
    seller_or_store: Optional[str]
    location: Optional[str]
    condition_raw: Optional[str]
    variant_normalized: dict[str, Any]


TEMPLATE_CONNECTORS: dict[str, ConnectorTemplateConfig] = {}


def load_template_configs(template_dir: Path | str | None = None) -> dict[str, ConnectorTemplateConfig]:
    """Load and validate RSS connector templates from YAML files.

    The template directory also contains HTML connector definitions, so we only
    validate files that declare the RSS connector contract.
    """

    if template_dir is None:
        template_dir = Path(__file__).resolve().parent / "templates"
    template_path = Path(template_dir)
    configs: dict[str, ConnectorTemplateConfig] = {}
    if not template_path.exists():
        return configs

    required_keys = {"source", "source_role", "endpoint_url"}
    for file_path in sorted(template_path.glob("*.y*ml")):
        raw = yaml.safe_load(file_path.read_text()) or {}
        if not isinstance(raw, dict) or not required_keys.issubset(raw):
            continue
        config = ConnectorTemplateConfig.model_validate(raw)
        configs[config.source] = config
    return configs


def register_template_connectors(template_dir: Path | str | None = None) -> dict[str, ConnectorTemplateConfig]:
    """Load templates into the module registry."""

    global TEMPLATE_CONNECTORS
    TEMPLATE_CONNECTORS = load_template_configs(template_dir)
    return TEMPLATE_CONNECTORS


def parse_feed(xml_text: str) -> list[FeedEntry]:
    """Parse an Atom or RSS feed, handling XML namespaces."""

    root = ET.fromstring(xml_text)
    tag = _strip_ns(root.tag)
    if tag == "feed":
        return _parse_atom_feed(root)
    if tag == "rss":
        return _parse_rss_feed(root)
    raise ValueError(f"Unsupported feed root: {root.tag}")


def parse_hardwareswapuk_post(
    title: str,
    content: str,
    author: str | None,
    link: str,
) -> dict[str, Any]:
    """Parse hardwareswapuk post format into a normalized marketplace listing."""

    full_text = " ".join(part for part in [title, content] if part)
    sale_match = re.search(
        r"\[H\](?P<header>.*?)\[W\](?P<price>[^\n\r\|]+)",
        full_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    buying_match = re.search(
        r"\[BG\](?P<item>.*?)(?:\[H\]|$)",
        full_text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    item_description = title
    condition_raw = None
    location = _extract_location(full_text)
    price = Decimal("0")

    if sale_match:
        header = sale_match.group("header").strip()
        price_text = sale_match.group("price").strip()
        item_description = _clean_swap_item_description(header)
        price = _parse_price_text(price_text)
        condition_raw = _extract_condition(full_text)
    elif buying_match:
        item_description = _clean_swap_item_description(buying_match.group("item").strip())
        condition_raw = "buying"
    else:
        fallback_price = extract_visible_gbp_price(full_text)
        if fallback_price is not None:
            price = fallback_price

    source_listing_id = link.rsplit("/", 1)[-1] or title
    return {
        "source_listing_id": source_listing_id,
        "title_raw": title,
        "price": price,
        "url": link,
        "seller_or_store": author,
        "location": location,
        "condition_raw": condition_raw,
        "variant_normalized": {
            "item_description": item_description,
            "post_type": "buying" if buying_match else "selling",
        },
    }


def _parse_atom_feed(root: ET.Element) -> list[FeedEntry]:
    entries: list[FeedEntry] = []
    for item in root.findall("atom:entry", ATOM_NS):
        title = (item.findtext("atom:title", default="", namespaces=ATOM_NS) or "").strip()
        link = _atom_link(item)
        author = item.findtext("atom:author/atom:name", default="", namespaces=ATOM_NS) or None
        content = _extract_content(item)
        published = _parse_timestamp(
            item.findtext("atom:published", default=None, namespaces=ATOM_NS)
            or item.findtext("atom:updated", default=None, namespaces=ATOM_NS)
        )
        entry_id = (item.findtext("atom:id", default="", namespaces=ATOM_NS) or link or title).strip()
        entries.append(
            FeedEntry(
                id=entry_id,
                title=title,
                link=link,
                content=content,
                author=author,
                published_at=published,
                raw_xml=ET.tostring(item, encoding="unicode"),
            )
        )
    return entries


def _parse_rss_feed(root: ET.Element) -> list[FeedEntry]:
    entries: list[FeedEntry] = []
    channel = root.find("channel")
    if channel is None:
        return entries
    for item in channel.findall("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        author = item.findtext("author") or item.findtext("dc:creator", namespaces=ATOM_NS)
        content = item.findtext("description") or item.findtext("content:encoded", namespaces=ATOM_NS) or ""
        published = _parse_timestamp(item.findtext("pubDate"))
        entry_id = (item.findtext("guid") or link or title).strip()
        entries.append(
            FeedEntry(
                id=entry_id,
                title=title,
                link=link,
                content=content,
                author=author,
                published_at=published,
                raw_xml=ET.tostring(item, encoding="unicode"),
            )
        )
    return entries


def _atom_link(item: ET.Element) -> str:
    for link in item.findall("atom:link", ATOM_NS):
        rel = link.attrib.get("rel", "alternate")
        href = link.attrib.get("href", "").strip()
        if rel == "alternate" and href:
            return href
    return ""


def _extract_content(item: ET.Element) -> str:
    content = item.findtext("content:encoded", default="", namespaces=ATOM_NS)
    if content:
        return content
    content_elem = item.find("atom:content", ATOM_NS)
    if content_elem is not None and content_elem.text:
        return content_elem.text
    summary = item.findtext("atom:summary", default="", namespaces=ATOM_NS)
    return summary or ""


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    for parser in (
        lambda v: datetime.fromisoformat(v.replace("Z", "+00:00")),
        lambda v: datetime.strptime(v, "%a, %d %b %Y %H:%M:%S %z"),
    ):
        try:
            dt = parser(value)
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None


def _strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _parse_price_text(value: str) -> Decimal:
    price = extract_visible_gbp_price(value)
    return price if price is not None else Decimal("0")


def _extract_retailer(title: str, content: str) -> Optional[str]:
    combined = f"{title} {content}"
    retailer_patterns = [
        r"\b(?:amazon|scan|ebuyer|cex|currys|overclockers|box|argos)\b",
        r"\b(?:hotukdeals|hukd|bapcsalesuk)\b",
    ]
    for pattern in retailer_patterns:
        match = re.search(pattern, combined, flags=re.IGNORECASE)
        if match:
            return match.group(0)
    return None


def _extract_location(text: str) -> Optional[str]:
    match = re.search(r"\b(?:location|loc)\s*[:\-]\s*([^\n\r\|]+)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _extract_condition(text: str) -> Optional[str]:
    match = re.search(r"\b(?:condition|cond)\s*[:\-]\s*([^\n\r\|]+)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _clean_swap_item_description(text: str) -> str:
    cleaned = re.sub(r"\[/?(?:H|W|BG|WTB|WTS|FS|FT)\]", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" -|\n\r\t") or text.strip()
