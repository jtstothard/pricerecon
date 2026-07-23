from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from pricerecon.connectors.reddit import (
    RedditHardwareSwapUKConnector,
    _parse_browser_posts,
)
from pricerecon.connectors.rss import TemplateConnector
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus


@pytest.mark.asyncio
async def test_reddit_api_fallback_preserves_normalization(monkeypatch: Any) -> None:
    connector = RedditHardwareSwapUKConnector()
    rss_error = ConnectorDegradedError(
        ConnectorStatus.bot_blocked,
        "RSS blocked",
        connector.connector_id,
        {"status_code": 403},
    )

    async def blocked(*args: Any, **kwargs: Any) -> list[Any]:
        raise rss_error

    async def api(*args: Any, **kwargs: Any) -> list[Any]:
        return [
            connector._api_post_to_listing(
                {
                    "id": "abc",
                    "title": "[H] RTX 4090 [W] £900",
                    "selftext": "Great condition",
                    "permalink": "/r/hardwareswapuk/comments/abc/post/",
                    "created_utc": 1_700_000_000,
                    "author": "seller",
                }
            )
        ]

    monkeypatch.setattr(TemplateConnector, "search", blocked)
    monkeypatch.setenv("PRICERECON_REDDIT_API_ENABLED", "true")
    monkeypatch.setenv("REDDIT_CLIENT_ID", "id")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
    monkeypatch.setenv("REDDIT_USER_AGENT", "PriceRecon/test")
    monkeypatch.setattr(connector, "_search_api", api)

    listings = await connector.search("RTX 4090")
    assert len(listings) == 1
    assert listings[0].title_raw == "[H] RTX 4090 [W] £900"
    assert listings[0].price == 900
    assert listings[0].url.endswith("/comments/abc/post/")
    assert listings[0].timestamp_seen == datetime.fromtimestamp(1_700_000_000, tz=timezone.utc)


@pytest.mark.asyncio
async def test_reddit_block_is_not_silently_converted_to_empty(monkeypatch: Any) -> None:
    connector = RedditHardwareSwapUKConnector()

    async def blocked(*args: Any, **kwargs: Any) -> list[Any]:
        raise ConnectorDegradedError(ConnectorStatus.rate_limited, "RSS limited", connector.connector_id, {"status_code": 429})

    monkeypatch.setattr(TemplateConnector, "search", blocked)
    with pytest.raises(ConnectorDegradedError) as raised:
        await connector.search("RTX")
    assert raised.value.status is ConnectorStatus.rate_limited
    assert raised.value.detail == {"status_code": 429, "fallbacks_attempted": False}


def test_browser_snapshot_parser_normalizes_post_identity() -> None:
    entries = _parse_browser_posts(
        '<article><a href="/r/hardwareswapuk/comments/abc/post/">[H] RTX 4090 [W] £900</a></article>',
        "hardwareswapuk",
        25,
    )
    assert len(entries) == 1
    assert entries[0].id
    assert entries[0].link == "https://www.reddit.com/r/hardwareswapuk/comments/abc/post/"
    assert entries[0].title == "[H] RTX 4090 [W] £900"
