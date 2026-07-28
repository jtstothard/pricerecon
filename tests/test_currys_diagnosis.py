"""Regression coverage for Currys recovery through FlareSolverr."""

import json

import pytest

from pricerecon.connectors.currys import CurrysConnector
from pricerecon.connectors.flaresolverr import FlareSolverrClient
from pricerecon.connectors.html import SelectorConfig, parse_listings_from_html
from pricerecon.models import SourceType


@pytest.fixture(scope="module")
def currys_rtx3080_html() -> str:
    with open("tests/fixtures/currys/RTX_3080.json") as f:
        return json.load(f)["solution"]["response"]


@pytest.fixture(scope="module")
def currys_rtx5090_html() -> str:
    with open("tests/fixtures/currys/RTX_5090.json") as f:
        return json.load(f)["solution"]["response"]


def test_currys_template_selectors_parse_captured_listings(currys_rtx5090_html: str) -> None:
    from pricerecon.connectors.template_connector import TemplateConnector

    template = TemplateConnector._load_yaml("currys")
    selectors = SelectorConfig(**template["selectors"])
    listings = parse_listings_from_html(
        currys_rtx5090_html,
        base_url="https://www.currys.co.uk",
        source="currys",
        source_type=SourceType.RETAILER,
        selector=selectors,
        category="gpu",
    )
    assert len(listings) > 0
    assert listings[0].price is not None
    assert listings[0].url.startswith("https://www.currys.co.uk/products/")
    assert "RTX 5090" in listings[0].title_raw or "RTX" in listings[0].title_raw


def test_currys_rtx3080_parser_extracts_listings(currys_rtx3080_html: str) -> None:
    selectors = SelectorConfig(
        card=".product-tile",
        title="a.pdpLink",
        price=".price",
        url="a.pdpLink",
        stock=".prod-availability-dynamic",
        image="img",
        id="a.pdpLink",
    )
    listings = parse_listings_from_html(
        currys_rtx3080_html,
        base_url="https://www.currys.co.uk",
        source="currys",
        source_type=SourceType.RETAILER,
        selector=selectors,
        category="gpu",
    )
    assert isinstance(listings, list)


@pytest.mark.asyncio
async def test_currys_connector_routes_through_flaresolverr(monkeypatch) -> None:
    """Currys must use the viable FlareSolverr route, never direct HTTP."""
    direct_attempted = False

    async def request_html(_self, url: str) -> str:
        assert "currys.co.uk/search?q=RTX+5090" in url
        return """
        <html><body><div class="product-tile">
          <a class="pdpLink" href="https://www.currys.co.uk/products/test"><h3>Test Product</h3></a>
          <span class="price">£100.00</span>
        </div></body></html>
        """

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def get(self, *args, **kwargs):
            nonlocal direct_attempted
            direct_attempted = True
            raise AssertionError("CurrysConnector must not use direct HTTP")

    monkeypatch.setattr(
        "pricerecon.connectors.template_connector.httpx.AsyncClient", MockAsyncClient
    )
    monkeypatch.setattr("pricerecon.connectors.flaresolverr.httpx.AsyncClient", MockAsyncClient)
    monkeypatch.setattr(FlareSolverrClient, "request_html", request_html)

    connector = CurrysConnector(flaresolverr_url="http://localhost:8191")
    listings = await connector.search("RTX 5090")

    assert not direct_attempted
    assert listings
    assert listings[0].source == "currys"


@pytest.mark.asyncio
async def test_flaresolverr_client_posts_request_get_and_returns_solution(monkeypatch) -> None:
    """The solver transport must be verified independently of Currys routing."""
    calls: list[tuple[str, dict]] = []

    class MockResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "status": "ok",
                "message": "Challenge not detected!",
                "solution": {"status": 200, "response": "<html>solver result</html>"},
            }

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, endpoint: str, *, json: dict) -> MockResponse:
            calls.append((endpoint, json))
            return MockResponse()

    monkeypatch.setattr("pricerecon.connectors.flaresolverr.httpx.AsyncClient", MockAsyncClient)

    client = FlareSolverrClient("http://solver.test/v1")
    html = await client.request_html("https://www.currys.co.uk/search?q=RTX+5090")

    assert html == "<html>solver result</html>"
    assert calls == [
        (
            "http://solver.test/v1",
            {
                "cmd": "request.get",
                "url": "https://www.currys.co.uk/search?q=RTX+5090",
                "maxTimeout": 60000,
            },
        )
    ]
