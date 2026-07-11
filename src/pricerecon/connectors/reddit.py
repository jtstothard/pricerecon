"""Reddit RSS connector templates."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from pricerecon.connectors.base import BaseConnector
from pricerecon.connectors.rss import FeedEntry, TemplateConnector, register_template_connectors
from pricerecon.models import NormalizedListing, SourceType


class RedditHardwareSwapUKConnector(TemplateConnector):
    CONNECTOR_ID = "reddit_hardwareswapuk"

    def __init__(self) -> None:
        template = register_template_connectors().get(self.CONNECTOR_ID)
        if template is None:
            from pricerecon.connectors.rss import ConnectorTemplateConfig

            template = ConnectorTemplateConfig(
                source=self.CONNECTOR_ID,
                display_name="Reddit hardwareswapuk",
                source_role=SourceType.MARKETPLACE,
                endpoint_url=(
                    "https://www.reddit.com/r/hardwareswapuk/search.rss"
                    "?q={query}&sort=new&limit={limit}&restrict_sr=1"
                ),
                request_method="GET",
                request_headers={"User-Agent": "PriceRecon/0.1"},
            )
        super().__init__(template)


class RedditBapcSalesUKConnector(TemplateConnector):
    CONNECTOR_ID = "reddit_bapcsalesuk"

    def __init__(self) -> None:
        template = register_template_connectors().get(self.CONNECTOR_ID)
        if template is None:
            from pricerecon.connectors.rss import ConnectorTemplateConfig

            template = ConnectorTemplateConfig(
                source=self.CONNECTOR_ID,
                display_name="Reddit bapcsalesuk",
                source_role=SourceType.SIGNAL,
                endpoint_url=(
                    "https://www.reddit.com/r/bapcsalesuk/search.rss"
                    "?q={query}&sort=new&limit={limit}&restrict_sr=1"
                ),
                request_method="GET",
                request_headers={"User-Agent": "PriceRecon/0.1"},
            )
        super().__init__(template)

    async def search(self, query: str, filters: Optional[dict[str, Any]] = None) -> list[NormalizedListing]:
        listings = await super().search(query, filters)
        for listing in listings:
            listing.in_stock = None
        return listings


class HotUKDealsConnector(TemplateConnector):
    CONNECTOR_ID = "hotukdeals"

    def __init__(self) -> None:
        template = register_template_connectors().get(self.CONNECTOR_ID)
        if template is None:
            from pricerecon.connectors.rss import ConnectorTemplateConfig

            template = ConnectorTemplateConfig(
                source=self.CONNECTOR_ID,
                display_name="HotUKDeals",
                source_role=SourceType.SIGNAL,
                endpoint_url="https://www.hotukdeals.com/rss",
                request_method="GET",
                request_headers={"User-Agent": "PriceRecon/0.1"},
            )
        super().__init__(template)

    async def search(self, query: str, filters: Optional[dict[str, Any]] = None) -> list[NormalizedListing]:
        listings = await super().search(query, filters)
        keyword = query.lower().strip()
        if keyword:
            listings = [listing for listing in listings if keyword in listing.title_raw.lower() or keyword in (listing.variant_normalized or {}).get("query", "").lower()]
        for listing in listings:
            listing.in_stock = None
        return listings