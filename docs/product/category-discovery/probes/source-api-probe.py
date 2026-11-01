"""Single approved source-access probe; no retries, fallback, token store or app runs.

Run only inside the deployed environment with explicit credential-use authority.
Output is an allowlist of operational receipts, never raw responses or secrets.
"""

import asyncio
import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

from pricerecon.connectors.aliexpress import AliExpressConnector


def emit(**record):
    print(json.dumps({"utc": datetime.now(timezone.utc).isoformat(), **record}), flush=True)


def code(value):
    text = str(value)
    return text if re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", text) else "withheld"


def present(value):
    return value is not None and value != "" and value != [] and value != {}


def fingerprint(value):
    return hashlib.sha256(str(value).encode()).hexdigest()


class BudgetTransport(httpx.AsyncBaseTransport):
    def __init__(self):
        self.inner = httpx.AsyncHTTPTransport(retries=0)
        self.calls = []

    async def handle_async_request(self, request):
        host, path = request.url.host, request.url.path
        allowed = (
            host == "api.ebay.com"
            and (path == "/identity/v1/oauth2/token" or path.startswith("/buy/browse/v1/"))
        ) or (host == "api-sg.aliexpress.com" and path == "/sync")
        if not allowed or len(self.calls) >= 5:
            raise RuntimeError("Probe request boundary reached")
        self.calls.append({"host": host, "path": path.split("/item/")[0], "method": request.method})
        return await self.inner.handle_async_request(request)

    async def aclose(self):
        await self.inner.aclose()


def ebay_fields(item):
    return {
        key: present(item.get(key))
        for key in (
            "itemId",
            "title",
            "price",
            "condition",
            "buyingOptions",
            "seller",
            "shippingOptions",
            "shipToLocations",
            "estimatedAvailabilities",
            "localizedAspects",
            "taxes",
            "itemWebUrl",
            "primaryItemGroup",
        )
    }


async def ebay(client):
    app, secret = os.getenv("EBAY_APP_ID"), os.getenv("EBAY_CERT_ID")
    if not app or not secret:
        emit(provider="ebay", step="preflight", result="credentials_missing")
        return
    r = await client.post(
        "https://api.ebay.com/identity/v1/oauth2/token",
        auth=httpx.BasicAuth(app, secret),
        data={"grant_type": "client_credentials", "scope": "https://api.ebay.com/oauth/api_scope"},
    )
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    token = body.get("access_token")
    emit(
        provider="ebay",
        step="token",
        http=r.status_code,
        token_received=isinstance(token, str) and bool(token),
        error_code=code(body["error"]) if body.get("error") else None,
    )
    if r.status_code != 200 or not isinstance(token, str) or not token:
        return
    headers = {"Authorization": "Bearer " + token, "X-EBAY-C-MARKETPLACE-ID": "EBAY_GB"}
    r = await client.get(
        "https://api.ebay.com/buy/browse/v1/item_summary/search",
        headers=headers,
        params={"q": "Casio MTP-B145D", "limit": "5", "filter": "deliveryCountry:GB"},
    )
    body = r.json()
    items = body.get("itemSummaries", [])
    if not isinstance(items, list):
        items = []
    emit(
        provider="ebay",
        step="search",
        http=r.status_code,
        query="Casio MTP-B145D",
        marketplace="EBAY_GB",
        requested_delivery_country="GB",
        page_limit=5,
        returned_items=len(items),
        next_page_present=bool(body.get("next")),
        error_codes=[code(x.get("errorId")) for x in body.get("errors", []) if isinstance(x, dict)],
    )
    if r.status_code != 200 or body.get("errors"):
        return
    selected = next(
        (
            x
            for x in items
            if isinstance(x, dict)
            and x.get("itemId")
            and re.search(r"MTP[\s-]*B145D", str(x.get("title", "")), re.I)
        ),
        None,
    )
    if selected is None:
        emit(provider="ebay", step="detail", result="not_attempted_no_query_candidate")
        return
    item_id = str(selected["itemId"])
    r = await client.get(
        "https://api.ebay.com/buy/browse/v1/item/" + quote(item_id, safe=""), headers=headers
    )
    body = r.json()
    emit(
        provider="ebay",
        step="detail",
        http=r.status_code,
        candidate_digest=fingerprint(item_id),
        fields=ebay_fields(body),
        query_reference_in_title=bool(
            re.search(r"MTP[\s-]*B145D", str(body.get("title", "")), re.I)
        ),
        error_codes=[code(x.get("errorId")) for x in body.get("errors", []) if isinstance(x, dict)],
    )


def ali_products(body):
    if not isinstance(body, dict):
        return []
    found = []
    for key, value in body.items():
        if isinstance(value, dict):
            found.extend(ali_products(value))
        elif isinstance(value, list):
            found.extend(
                x
                for x in value
                if isinstance(x, dict) and (x.get("product_id") or x.get("productId"))
            )
    return found


def ali_error(body):
    if "code" in body and str(body["code"]) not in {"0", "200"}:
        return code(body["code"])
    if isinstance(body.get("error_response"), dict):
        return code(body["error_response"].get("code", "unknown"))
    for value in body.values():
        if isinstance(value, dict):
            nested = value.get("resp_result", value)
            if isinstance(nested, dict) and "resp_code" in nested:
                if str(nested["resp_code"]) not in {"0", "200"}:
                    return code(nested["resp_code"])
    return None


async def aliexpress(client):
    key, secret = os.getenv("ALIEXPRESS_APP_KEY"), os.getenv("ALIEXPRESS_APP_SECRET")
    if not key or not secret:
        emit(provider="aliexpress", step="preflight", result="credentials_missing")
        return
    connector = AliExpressConnector(
        config={"app_key": key, "app_secret": secret}, http_client=client
    )
    r = await connector._top_post(
        "aliexpress.affiliate.product.query",
        {
            "keywords": "Militado ML05",
            "target_currency": "GBP",
            "ship_to_country": "GB",
            "page_no": 1,
            "page_size": 5,
        },
    )
    body = r.json()
    error = ali_error(body)
    items = ali_products(body)
    emit(
        provider="aliexpress",
        step="query",
        http=r.status_code,
        query="Militado ML05",
        requested_currency="GBP",
        requested_delivery_country="GB",
        page=1,
        page_size=5,
        returned_items=len(items),
        error_code=error,
    )
    if r.status_code != 200 or error:
        return
    selected = next(
        (
            x
            for x in items
            if "militado" in str(x.get("product_title", x.get("title", ""))).lower()
            and "ml05" in str(x.get("product_title", x.get("title", ""))).lower()
        ),
        None,
    )
    if selected is None:
        emit(provider="aliexpress", step="detail", result="not_attempted_no_query_candidate")
        return
    pid = str(selected.get("product_id") or selected.get("productId"))
    if not pid.isdigit():
        emit(provider="aliexpress", step="detail", result="not_attempted_invalid_product_id")
        return
    r = await connector._top_post(
        "aliexpress.affiliate.productdetail.get",
        {
            "product_ids": pid,
            "target_currency": "GBP",
            "target_language": "EN",
        },
    )
    body = r.json()
    items = ali_products(body)
    item = next((x for x in items if str(x.get("product_id") or x.get("productId")) == pid), {})
    groups = {
        "id": ("product_id", "productId"),
        "title": ("product_title", "title"),
        "target_price": ("target_sale_price", "targetSalePrice"),
        "target_currency": ("target_sale_price_currency", "target_currency"),
        "merchant": ("shop_name", "shopName"),
        "product_url": ("product_detail_url", "productDetailUrl"),
        "shipping_cost": ("shipping_cost", "shippingCost"),
        "tax": ("tax", "taxes", "vat"),
        "stock": ("in_stock", "inStock", "sku_available_stock"),
        "selected_sku": ("sku_id", "skuId", "selectedSkuId"),
    }
    emit(
        provider="aliexpress",
        step="detail",
        http=r.status_code,
        candidate_digest=fingerprint(pid),
        error_code=ali_error(body),
        returned_product_match=bool(item),
        fields={name: any(present(item.get(k)) for k in keys) for name, keys in groups.items()},
        uk_destination_in_detail_request=False,
    )


async def main():
    logging.disable(logging.CRITICAL)
    transport = BudgetTransport()
    async with httpx.AsyncClient(transport=transport, timeout=25, follow_redirects=False) as client:
        for name, probe in (("ebay", ebay), ("aliexpress", aliexpress)):
            try:
                await probe(client)
            except Exception as exc:
                emit(provider=name, result="stopped", error_type=type(exc).__name__)
        emit(
            summary=True,
            provider_requests=len(transport.calls),
            maximum=5,
            retries=0,
            redirects_followed=0,
            requests=transport.calls,
        )


if __name__ == "__main__":
    asyncio.run(main())
