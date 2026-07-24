"""Regression coverage for eBay startup-burst token coordination."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from pricerecon.connectors.ebay import _EBayTokenFetchCoordinator


@pytest.mark.asyncio
async def test_concurrent_startup_token_fetches_are_deduplicated() -> None:
    response = MagicMock(status_code=200)
    response.json.return_value = {
        "access_token": "startup-token",
        "token_type": "Bearer",
        "expires_in": 7200,
    }
    client = AsyncMock()
    client.post.return_value = response

    coordinator = _EBayTokenFetchCoordinator()
    tokens = await asyncio.gather(
        *(
            coordinator.fetch_token(
                app_id="startup-app",
                cert_id="startup-cert",
                client=client,
            )
            for _ in range(20)
        )
    )

    assert {token.access_token for token in tokens} == {"startup-token"}
    assert client.post.call_count == 1
