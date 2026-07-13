"""Reddit RSS connector templates."""

from __future__ import annotations

import re
from typing import Any, Optional

from returns.result import Success

from pricerecon.connectors.rss import (
    ConnectorTemplateConfig,
    TemplateConnector,
    load_template_configs_result,
)
from pricerecon.models import NormalizedListing, SourceType


def _load_template_or_default(
    connector_id: str,
    *,
    display_name: str,
    source_role: SourceType,
    endpoint_url: str,
) -> ConnectorTemplateConfig:
    loaded = load_template_configs_result()
    if isinstance(loaded, Success):
        template = loaded.unwrap().get(connector_id)
        if template is not None:
            return template  # type: ignore[no-any-return]
    return ConnectorTemplateConfig(
        source=connector_id,
        display_name=display_name,
        source_role=source_role,
        endpoint_url=endpoint_url,
        request_method="GET",
        request_headers={"User-Agent": "PriceRecon/0.1"},
    )


def _query_terms(query: str) -> list[str]:
    return [term for term in re.split(r"[^a-z0-9]+", query.lower()) if term]


def _filter_listings_by_query(
    listings: list[NormalizedListing], query: str
) -> list[NormalizedListing]:
    terms = _query_terms(query)
    if not terms:
        return listings

    filtered: list[NormalizedListing] = []
    for listing in listings:
        variant = listing.variant_normalized or {}
        haystack = " ".join(
            str(part).lower()
            for part in (
                listing.title_raw,
                listing.url,
                variant.get("item_description"),
                variant.get("query"),
            )
            if part
        )
        if all(term in haystack for term in terms):
            filtered.append(listing)
    return filtered


class RedditHardwareSwapUKConnector(TemplateConnector):
    CONNECTOR_ID = "reddit_hardwareswapuk"

    def __init__(self) -> None:
        super().__init__(
            _load_template_or_default(
                self.CONNECTOR_ID,
                display_name="Reddit hardwareswapuk",
                source_role=SourceType.MARKETPLACE,
                endpoint_url=(
                    "https://www.reddit.com/r/hardwareswapuk/new/.rss"
                    "?limit={limit}&restrict_sr=1"
                ),
            )
        )

    async def search(
        self, query: str, filters: Optional[dict[str, Any]] = None
    ) -> list[NormalizedListing]:
        listings = await super().search(query, filters)
        listings = _filter_listings_by_query(listings, query)
        for listing in listings:
            listing.in_stock = None
        return listings


class RedditBapcSalesUKConnector(TemplateConnector):
    CONNECTOR_ID = "reddit_bapcsalesuk"

    def __init__(self) -> None:
        super().__init__(
            _load_template_or_default(
                self.CONNECTOR_ID,
                display_name="Reddit bapcsalesuk",
                source_role=SourceType.MARKETPLACE,
                endpoint_url=(
                    "https://www.reddit.com/r/bapcsalesuk/new/.rss" "?limit={limit}&restrict_sr=1"
                ),
            )
        )

    async def search(
        self, query: str, filters: Optional[dict[str, Any]] = None
    ) -> list[NormalizedListing]:
        listings = await super().search(query, filters)
        listings = _filter_listings_by_query(listings, query)
        for listing in listings:
            listing.in_stock = None
        return listings


class HotUKDealsConnector(TemplateConnector):
    CONNECTOR_ID = "hotukdeals"

    def __init__(self) -> None:
        super().__init__(
            _load_template_or_default(
                self.CONNECTOR_ID,
                display_name="HotUKDeals",
                source_role=SourceType.SIGNAL,
                endpoint_url="https://www.hotukdeals.com/rss/new",
            )
        )

    async def search(
        self, query: str, filters: Optional[dict[str, Any]] = None
    ) -> list[NormalizedListing]:
        listings = await super().search(query, filters)
        listings = _filter_listings_by_query(listings, query)
        for listing in listings:
            listing.in_stock = None
        return listings
