from decimal import Decimal
from typing import Any, cast

import httpx
import pytest

from pricerecon.connectors.aliexpress import AliExpressConnector


class Response:
    status_code = 200

    def __init__(self, payload: Any) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Any:
        return self.payload


class Client:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    async def get(self, url: str, **kwargs: Any) -> Any:
        self.calls.append({"url": url, **kwargs})
        if isinstance(self.response, Exception):
            raise self.response
        return self.response

    async def aclose(self) -> None:
        return None


def connector(client: Client) -> AliExpressConnector:
    return AliExpressConnector(
        {"searxng_url": "http://searxng.test:8080", "searxng_max_results": 2},
        http_client=cast(httpx.AsyncClient, client),
    )


@pytest.mark.asyncio
async def test_searxng_success_dedupes_and_limits_results() -> None:
    payload = {
        "results": [
            {"url": "https://www.aliexpress.com/item/1005001234567890.html", "title": "GPU", "content": "£19.99"},
            {"url": "https://www.aliexpress.com/item/1005001234567890.html?x=1", "title": "duplicate", "content": "£20.00"},
            {"url": "https://www.aliexpress.com/item/1005001234567891.html", "title": "GPU 2", "content": "£29.99"},
        ]
    }
    client = Client(Response(payload))
    results = await connector(client)._searxng_search("GPU", {})
    assert len(results) == 2
    assert results[0].price == Decimal("19.99")
    assert client.calls[0]["url"] == "http://searxng.test:8080/search"


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [{}, {"results": "bad"}, {"results": [{"title": "no url"}]}])
async def test_searxng_empty_or_malformed_response_is_safe(payload: Any) -> None:
    results = await connector(Client(Response(payload)))._searxng_search("GPU", {})
    assert results == []


@pytest.mark.asyncio
async def test_searxng_timeout_is_safe() -> None:
    client = Client(httpx.ReadTimeout("timed out"))
    assert await connector(client)._searxng_search("GPU", {}) == []


def test_searxng_url_environment_overrides_config(monkeypatch: Any) -> None:
    monkeypatch.setenv("SEARXNG_URL", "http://env.example:8080")
    conn = AliExpressConnector({"searxng_url": "http://config.example:8080"})
    assert conn._searxng_endpoint == "http://env.example:8080"


@pytest.mark.asyncio
async def test_search_uses_searxng_only_after_brave_is_empty(monkeypatch: Any) -> None:
    client = Client(Response({"results": []}))
    conn = connector(client)
    async def empty_affiliate(query: str, filters: dict[str, Any]) -> list[Any]:
        return []
    async def empty_brave(query: str, filters: dict[str, Any]) -> list[Any]:
        return []
    monkeypatch.setattr(conn, "_affiliate_search", empty_affiliate)
    monkeypatch.setattr(conn, "_brave_search", empty_brave)
    results = await conn.search("GPU", {"site_search_discovery": False})
    assert results == []
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_search_uses_searxng_when_brave_only_returns_placeholders(monkeypatch: Any) -> None:
    client = Client(Response({"results": [
        {"url": "https://www.aliexpress.com/item/1005001234567890.html", "title": "GPU", "content": "£19.99"}
    ]}))
    conn = connector(client)

    async def empty_affiliate(query: str, filters: dict[str, Any]) -> list[Any]:
        return []

    async def brave_placeholder(query: str, filters: dict[str, Any]) -> list[Any]:
        return [conn._manual_listing("1005001234567890", filters)]

    monkeypatch.setattr(conn, "_affiliate_search", empty_affiliate)
    monkeypatch.setattr(conn, "_brave_search", brave_placeholder)
    results = await conn.search("GPU", {"site_search_discovery": False})

    assert [listing.price for listing in results] == [Decimal("19.99")]
    await conn.cleanup()
    assert len(client.calls) == 1


def test_extract_pid_from_url_requires_https_aliexpress_product_url() -> None:
    conn = connector(Client(Response({})))
    assert conn._extract_pid_from_url("https://www.aliexpress.com/item/1005001234567890.html") == "1005001234567890"
    assert conn._extract_pid_from_url("http://www.aliexpress.com/item/1005001234567890.html") is None
    assert conn._extract_pid_from_url("https://example.com/item/1005001234567890.html") is None
    assert conn._extract_pid_from_url("https://www.aliexpress.com/search/1005001234567890") is None
    assert conn._extract_pid_from_url("https://www.aliexpress.com/item/1005001234567890.html.evil") is None
    assert conn._extract_pid_from_url("https://user@www.aliexpress.com/item/1005001234567890.html") is None
    assert conn._extract_pid_from_url("https://www.aliexpress.com:444/item/1005001234567890.html") is None
    assert conn._extract_pid_from_url("https://www.aliexpress.com:bad/item/1005001234567890.html") is None
    assert conn._extract_pid_from_url("https://[bad/item/1005001234567890.html") is None


def test_resolve_short_link_does_not_extract_pid_from_arbitrary_redirect(monkeypatch: Any) -> None:
    conn = connector(Client(Response({})))

    class RedirectResponse:
        url = "https://example.com/item/1005001234567890.html"

    monkeypatch.setattr("pricerecon.connectors.aliexpress.httpx.get", lambda *args, **kwargs: RedirectResponse())
    assert conn._resolve_short_link("https://a.aliexpress.com/_test") is None
    assert conn._resolve_short_link("http://a.aliexpress.com/_test") is None
    assert conn._resolve_short_link("https://user@a.aliexpress.com/_test") is None
    assert conn._resolve_short_link("https://a.aliexpress.com:444/_test") is None


def test_resolve_short_link_rejects_arbitrary_intermediate_redirect(monkeypatch: Any) -> None:
    conn = connector(Client(Response({})))
    calls: list[str] = []

    class RedirectResponse:
        is_redirect = True
        headers = {"location": "https://example.com/redirect"}
        url = "https://a.aliexpress.com/_test"

    def fake_get(url: str, **kwargs: Any) -> RedirectResponse:
        calls.append(url)
        return RedirectResponse()

    monkeypatch.setattr("pricerecon.connectors.aliexpress.httpx.get", fake_get)
    assert conn._resolve_short_link("https://a.aliexpress.com/_test") is None
    assert calls == ["https://a.aliexpress.com/_test"]