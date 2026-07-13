"""AliExpress connector with affiliate, DS, manual PID, and browser PDP lanes."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

from pricerecon.connectors.base import BaseConnector
from pricerecon.connectors.browser_client import BrowserClient
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus
from pricerecon.models import NormalizedListing, SourceType

logger = logging.getLogger(__name__)

_DEFAULT_TOP_ENDPOINT = "https://api-sg.aliexpress.com/sync"

_SHORT_LINK_HOSTS = {"a.aliexpress.com", "s.click.aliexpress.com"}
_PID_RE = re.compile(r"\b(\d{10,20})\b")
_PRICE_RE = re.compile(r"(?P<currency>GBP|£|\$|USD|EUR|€)?\s*(?P<amount>\d+(?:\.\d{1,2})?)")


class AliExpressConnector(BaseConnector):
    """AliExpress connector with layered acquisition and enrichment."""

    CONNECTOR_ID = "aliexpress"

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        *,
        browser_client: BrowserClient | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = config or {}
        self._client = http_client or httpx.AsyncClient(timeout=30.0)
        self._owns_client = http_client is None
        self._browser_client = browser_client
        self._ds_access_token = self.config.get("ds_access_token")
        self._ds_refresh_token = self.config.get("ds_refresh_token")
        self._ds_expires_at = self._parse_datetime(self.config.get("ds_expires_at"))
        self._affiliate_endpoint = self.config.get("affiliate_api_endpoint", _DEFAULT_TOP_ENDPOINT)
        self._ds_refresh_endpoint = self.config.get("ds_refresh_endpoint", _DEFAULT_TOP_ENDPOINT)
        self._ds_product_endpoint = self.config.get("ds_product_endpoint", _DEFAULT_TOP_ENDPOINT)
        self._affiliate_currency = str(self.config.get("affiliate_currency", "GBP")).upper()
        self._manual_pids = self._normalize_pid_list(self.config.get("manual_pids", []))
        self._manual_links = list(self.config.get("manual_links", []))
        self._browser_enrich_default = bool(self.config.get("browser_enrich", False))
        self._enrich_with_ds_default = bool(self.config.get("enrich_with_ds", False))
        self._brave_discovery_default = bool(self.config.get("brave_discovery", True))
        self._brave_max_pids = int(self.config.get("brave_max_pids", 25))

    @property
    def source_role(self) -> SourceType:
        return SourceType.MARKETPLACE

    async def cleanup(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def search(self, query: str, filters: dict[str, Any] | None = None) -> list[NormalizedListing]:
        filters = filters or {}
        listings: list[NormalizedListing] = []

        affiliate_query = self._is_affiliate_search_enabled(filters)
        if affiliate_query:
            listings.extend(await self._affiliate_search(query, filters))

        brave_query = self._is_brave_search_enabled(filters)
        if brave_query:
            listings.extend(await self._brave_search(query, filters))

        manual_targets = self._resolve_manual_targets(query, filters)
        if manual_targets:
            listings.extend(await self._manual_pid_search(manual_targets, filters))

        listings = self._dedupe_listings(listings)

        if self._should_enrich_with_ds(filters):
            listings = await self._apply_ds_enrichment(listings)

        if self._should_enrich_with_browser(filters):
            listings = await self._apply_browser_enrichment(listings, filters)

        return listings

    def _is_affiliate_search_enabled(self, filters: dict[str, Any]) -> bool:
        if filters.get("affiliate_only") is False:
            return False
        return True

    def _is_brave_search_enabled(self, filters: dict[str, Any]) -> bool:
        if filters.get("brave_discovery") is not None:
            return bool(filters.get("brave_discovery"))
        return self._brave_discovery_default

    def _should_enrich_with_ds(self, filters: dict[str, Any]) -> bool:
        if filters.get("enrich_with_ds") is not None:
            return bool(filters.get("enrich_with_ds"))
        return self._enrich_with_ds_default or self._has_ds_credentials()

    def _should_enrich_with_browser(self, filters: dict[str, Any]) -> bool:
        if filters.get("browser_enrich") is not None:
            return bool(filters.get("browser_enrich"))
        return self._browser_enrich_default or self._browser_client is not None

    def _has_ds_credentials(self) -> bool:
        return bool(
            self._ds_access_token
            or self._ds_refresh_token
            or self.config.get("ds_app_key")
            or self.config.get("ds_app_secret")
        )

    def _parse_datetime(self, value: Any) -> datetime | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)
            except ValueError:
                return None
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
        return None

    def _normalize_pid_list(self, values: Any) -> list[str]:
        if not values:
            return []
        if isinstance(values, str):
            values = [values]
        result: list[str] = []
        for value in values:
            pid = self._normalize_pid(value)
            if pid:
                result.append(pid)
        return result

    def _normalize_pid(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        if text.isdigit() and 10 <= len(text) <= 20:
            return text
        pid = self._extract_pid(text)
        if pid:
            return pid
        return None

    def _extract_pid(self, text: str) -> str | None:
        match = _PID_RE.search(text)
        if match:
            return match.group(1)
        return None

    def _extract_pid_from_url(self, url: str) -> str | None:
        parsed = urlparse(url)
        if parsed.netloc and parsed.netloc.lower() in _SHORT_LINK_HOSTS:
            query_pid = parse_qs(parsed.query).get("pid") or parse_qs(parsed.query).get("productId")
            if query_pid:
                normalized = self._normalize_pid(query_pid[0])
                if normalized:
                    return normalized
        pid = self._extract_pid(parsed.path)
        if pid:
            return pid
        pid = self._extract_pid(url)
        if pid:
            return pid
        return None

    def _resolve_short_link(self, url: str) -> str | None:
        parsed = urlparse(url)
        if not parsed.netloc or parsed.netloc.lower() not in _SHORT_LINK_HOSTS:
            return None
        try:
            response = httpx.get(url, follow_redirects=True, timeout=10.0, headers={"User-Agent": "Mozilla/5.0"})
        except Exception:
            return None
        final_url = str(response.url)
        return self._extract_pid_from_url(final_url) or self._extract_pid(final_url)

    def _resolve_manual_targets(self, query: str, filters: dict[str, Any]) -> list[str]:
        targets: list[str] = []
        query_pid = self._normalize_pid(query)
        if query_pid:
            targets.append(query_pid)

        for raw in filters.get("manual_pids", []):
            pid = self._normalize_pid(raw)
            if pid:
                targets.append(pid)

        for raw in self._manual_pids:
            targets.append(raw)

        for raw in filters.get("manual_links", []):
            pid = self._extract_pid_from_url(str(raw))
            if pid:
                targets.append(pid)

        for raw in self._manual_links:
            pid = self._extract_pid_from_url(str(raw))
            if pid:
                targets.append(pid)

        # If the query is a short-link, resolve it to a PID.
        if query and not query_pid:
            pid = self._extract_pid_from_url(query) or self._resolve_short_link(query)
            if pid:
                targets.append(pid)

        return list(dict.fromkeys(targets))

    async def _affiliate_search(self, query: str, filters: dict[str, Any]) -> list[NormalizedListing]:
        payload: dict[str, Any] = {
            "query": query,
            "currency": filters.get("currency", self._affiliate_currency),
            "page": int(filters.get("page", 1)),
            "page_size": int(filters.get("page_size", 50)),
        }
        if "price_max" in filters:
            payload["max_price"] = str(filters["price_max"])

        try:
            response = await self._top_post("aliexpress.affiliate.product.query", payload)
            self._raise_for_top_response(response, "AliExpress affiliate search failed")
        except Exception as exc:
            text = str(exc).lower()
            if "auth" in text or "401" in text or "403" in text:
                raise ConnectorDegradedError(
                    status=ConnectorStatus.auth_failed,
                    message="AliExpress affiliate API auth failed",
                    connector_id=self.connector_id,
                    detail={"error": str(exc)},
                ) from exc
            raise ConnectorDegradedError(
                status=ConnectorStatus.unknown_error,
                message="AliExpress affiliate search failed",
                connector_id=self.connector_id,
                detail={"error": str(exc)},
            ) from exc

        data = self._extract_response_list(self._extract_top_response_payload(response.json()))
        return [self._listing_from_affiliate_item(item, query) for item in data]

    async def _brave_search(self, query: str, filters: dict[str, Any]) -> list[NormalizedListing]:
        """Discover PIDs via Brave Search for non-enrolled listings."""
        from urllib.parse import quote

        max_pids = int(filters.get("brave_max_pids", self._brave_max_pids))
        listings: list[NormalizedListing] = []

        # Rate limiting before Brave request
        await self._rate_limit_brave()

        # Query Brave Search for AliExpress product pages
        brave_query = f'site:aliexpress.com/item/ "{query}"'
        url = f"https://search.brave.com/search?q={quote(brave_query)}"

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "text/html",
            }
            response = await self._client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            html = response.text
        except Exception as exc:
            logger.warning(f"Brave Search failed: {exc}")
            return listings

        # Extract unique PIDs
        pids = list(dict.fromkeys(re.findall(r'aliexpress\.com/item/(\d{10,})', html)))
        pids = pids[:max_pids]

        if not pids:
            return listings

        # Create minimal listings for each PID (enrichment happens downstream)
        currency = filters.get("currency", self._affiliate_currency)
        for pid in pids:
            listing = NormalizedListing.model_validate(
                {
                    "source": self.connector_id,
                    "source_type": self.source_role,
                    "source_listing_id": pid,
                    "title_raw": f"AliExpress {pid}",
                    "price": Decimal("0"),
                    "currency": currency,
                    "url": f"https://www.aliexpress.com/item/{pid}.html",
                    "in_stock": None,
                    "variant_normalized": {
                        "aliexpress_product_id": pid,
                        "aliexpress_watch_mode": "brave_discovery",
                    },
                }
            )
            listings.append(listing)

        return listings

    async def _rate_limit_brave(self) -> None:
        """Rate limit Brave Search requests to avoid hitting limits."""
        delay = 1.5
        await asyncio.sleep(delay)

    async def _manual_pid_search(self, pids: list[str], filters: dict[str, Any]) -> list[NormalizedListing]:
        listings: list[NormalizedListing] = []
        for pid in pids:
            listing = self._manual_listing(pid, filters)
            listings.append(listing)
        return listings

    def _manual_listing(self, pid: str, filters: dict[str, Any]) -> NormalizedListing:
        url = f"https://www.aliexpress.com/item/{pid}.html"
        listing = NormalizedListing.model_validate(
            {
                "source": self.connector_id,
                "source_type": self.source_role,
                "source_listing_id": pid,
                "title_raw": filters.get("manual_title") or pid,
                "price": Decimal(str(filters.get("manual_price", "0"))),
                "currency": filters.get("currency", self._affiliate_currency),
                "url": url,
                "in_stock": None,
                "variant_normalized": {
                    "aliexpress_product_id": pid,
                    "aliexpress_watch_mode": "manual_pid",
                },
            }
        )
        return listing

    def _extract_response_list(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, dict):
            for key in ("data", "items", "results", "productList", "products"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
                if isinstance(value, dict):
                    nested = self._extract_response_list(value)
                    if nested:
                        return nested
            for value in payload.values():
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        return []

    def _listing_from_affiliate_item(self, item: dict[str, Any], query: str) -> NormalizedListing:
        pid = self._first_text(item, "productId", "product_id", "itemId", "item_id", "id")
        if not pid:
            pid = hashlib.sha1(repr(sorted(item.items())).encode()).hexdigest()[:16]
        title = self._first_text(item, "title", "productTitle", "product_title", "itemTitle") or query
        display_price = self._first_decimal(item, "displayPrice", "display_price", "salePrice", "sale_price", "price")
        original_price = self._first_decimal(item, "originalPrice", "original_price", "msrpPrice", "old_price")
        shipping_cost = self._first_decimal(item, "shippingCost", "shipping_cost")
        seller = self._first_text(item, "shopName", "storeName", "sellerName", "shop_name")
        rating = self._first_decimal(item, "evaluateRate", "rating", "storeRating", "score")
        sales = self._first_text(item, "orders", "sales", "salesCount", "sold")
        stock = self._first_bool(item, "inStock", "in_stock", "available")
        url = self._first_text(item, "url", "itemUrl", "item_url") or f"https://www.aliexpress.com/item/{pid}.html"
        currency = self._first_text(item, "currency", "priceCurrency") or self._affiliate_currency
        currency = currency.upper()

        enrichment = self._build_enrichment_payload(
            pid=pid,
            title=title,
            display_price=display_price,
            original_price=original_price,
            shipping_cost=shipping_cost,
            seller=seller,
            rating=rating,
            sales=sales,
            stock=stock,
            source="affiliate",
        )
        listing = NormalizedListing.model_validate(
            {
                "source": self.connector_id,
                "source_type": self.source_role,
                "source_listing_id": pid,
                "title_raw": title,
                "price": display_price or Decimal("0"),
                "currency": currency,
                "url": url,
                "seller_or_store": seller,
                "shipping_cost": shipping_cost,
                "total_landed_cost": (display_price + shipping_cost) if display_price and shipping_cost else display_price,
                "in_stock": stock,
                "variant_normalized": enrichment,
                "image_url": self._first_text(item, "imageUrl", "image_url", "image"),
            }
        )
        return listing

    def _build_enrichment_payload(
        self,
        *,
        pid: str,
        title: str,
        display_price: Decimal | None,
        original_price: Decimal | None,
        shipping_cost: Decimal | None,
        seller: str | None,
        rating: Decimal | None,
        sales: Any,
        stock: bool | None,
        source: str,
    ) -> dict[str, Any]:
        effective_price = display_price
        if effective_price is not None and shipping_cost is not None:
            effective_price = effective_price + shipping_cost
        return {
            "aliexpress_product_id": pid,
            "aliexpress_title": title,
            "aliexpress_display_price": self._decimal_to_str(display_price),
            "aliexpress_original_price": self._decimal_to_str(original_price),
            "aliexpress_effective_price": self._decimal_to_str(effective_price),
            "aliexpress_shipping_cost": self._decimal_to_str(shipping_cost),
            "aliexpress_seller": seller,
            "aliexpress_rating": self._decimal_to_str(rating),
            "aliexpress_sales": sales,
            "aliexpress_stock": stock,
            "aliexpress_source_lane": source,
            "aliexpress_coupon_layers": [],
        }

    async def _apply_ds_enrichment(self, listings: list[NormalizedListing]) -> list[NormalizedListing]:
        if not self._has_ds_credentials():
            return listings
        enriched: list[NormalizedListing] = []
        for listing in listings:
            pid = self._normalize_pid(listing.source_listing_id) or self._extract_pid(listing.url) or listing.source_listing_id
            if not pid:
                enriched.append(listing)
                continue
            try:
                detail = await self._fetch_ds_detail(pid)
            except ConnectorDegradedError:
                raise
            except Exception as exc:
                raise ConnectorDegradedError(
                    status=ConnectorStatus.unknown_error,
                    message="AliExpress DS enrichment failed",
                    connector_id=self.connector_id,
                    detail={"error": str(exc), "product_id": pid},
                ) from exc
            enriched.append(self._merge_listing_with_detail(listing, detail, pid))
        return enriched

    async def _fetch_ds_detail(self, pid: str) -> dict[str, Any]:
        token = await self._ensure_ds_access_token()
        payload = {
            "product_id": pid,
            "ship_to_country": self.config.get("ds_ship_to_country", "GB"),
            "target_currency": self._affiliate_currency,
            "access_token": token,
        }
        try:
            response = await self._top_post("aliexpress.ds.product.get", payload)
            self._raise_for_top_response(response, "AliExpress DS product lookup failed")
        except ConnectorDegradedError:
            raise
        except Exception as exc:
            text = str(exc).lower()
            if "auth" in text or "401" in text or "403" in text:
                raise ConnectorDegradedError(
                    status=ConnectorStatus.auth_failed,
                    message="AliExpress DS auth failed",
                    connector_id=self.connector_id,
                    detail={"error": str(exc), "product_id": pid},
                ) from exc
            raise ConnectorDegradedError(
                status=ConnectorStatus.unknown_error,
                message="AliExpress DS product lookup failed",
                connector_id=self.connector_id,
                detail={"error": str(exc), "product_id": pid},
            ) from exc

        payload = self._extract_top_response_payload(response.json())
        if isinstance(payload, dict) and payload.get("error"):
            raise ConnectorDegradedError(
                status=ConnectorStatus.auth_failed,
                message="AliExpress DS auth failed",
                connector_id=self.connector_id,
                detail={"error": payload.get("error"), "product_id": pid},
            )
        return payload if isinstance(payload, dict) else {"raw": payload}

    async def _ensure_ds_access_token(self) -> str:
        if self._ds_access_token and not self._is_ds_token_expired():
            return self._ds_access_token
        return await self._refresh_ds_token(force=False)

    def _is_ds_token_expired(self) -> bool:
        if self._ds_expires_at is None:
            return False
        return datetime.now(timezone.utc) >= self._ds_expires_at - timedelta(minutes=5)

    async def _refresh_ds_token(self, *, force: bool) -> str:
        if not self._ds_refresh_token:
            raise ConnectorDegradedError(
                status=ConnectorStatus.auth_failed,
                message="AliExpress DS credentials are incomplete",
                connector_id=self.connector_id,
                detail={"missing": ["ds_refresh_token"]},
            )
        if not force and self._ds_access_token and not self._is_ds_token_expired():
            return self._ds_access_token

        app_key = self.config.get("ds_app_key")
        app_secret = self.config.get("ds_app_secret")
        if not app_key or not app_secret:
            raise ConnectorDegradedError(
                status=ConnectorStatus.auth_failed,
                message="AliExpress DS credentials are incomplete",
                connector_id=self.connector_id,
                detail={"missing": [name for name, value in (("ds_app_key", app_key), ("ds_app_secret", app_secret)) if not value]},
            )

        payload = {
            "refresh_token": self._ds_refresh_token,
        }
        try:
            response = await self._top_post("aliexpress.ds.auth.token.refresh", payload, app_key=str(app_key), app_secret=str(app_secret))
            self._raise_for_top_response(response, "AliExpress DS token refresh failed")
        except Exception as exc:
            raise ConnectorDegradedError(
                status=ConnectorStatus.auth_failed,
                message="AliExpress DS token refresh failed",
                connector_id=self.connector_id,
                detail={"error": str(exc)},
            ) from exc

        data = self._extract_top_response_payload(response.json())
        if not isinstance(data, dict):
            raise ConnectorDegradedError(
                status=ConnectorStatus.auth_failed,
                message="AliExpress DS token refresh failed",
                connector_id=self.connector_id,
                detail={"error": "unexpected token response"},
            )

        access_token = str(data.get("access_token") or data.get("accessToken") or "").strip()
        if not access_token:
            raise ConnectorDegradedError(
                status=ConnectorStatus.auth_failed,
                message="AliExpress DS token refresh failed",
                connector_id=self.connector_id,
                detail={"error": "missing access token"},
            )

        self._ds_access_token = access_token
        self._ds_refresh_token = str(data.get("refresh_token") or data.get("refreshToken") or self._ds_refresh_token)
        expires_in = data.get("expires_in") or data.get("expire_in") or 3600
        try:
            expires_in_int = int(expires_in)
        except Exception:
            expires_in_int = 3600
        self._ds_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_int)
        return access_token

    async def _top_post(
        self,
        method: str,
        params: dict[str, Any],
        *,
        app_key: str | None = None,
        app_secret: str | None = None,
    ) -> httpx.Response:
        signed = self._build_top_request(method, params, app_key=app_key, app_secret=app_secret)
        return await self._client.post(self._affiliate_endpoint, data=signed)

    def _build_top_request(
        self,
        method: str,
        params: dict[str, Any],
        *,
        app_key: str | None = None,
        app_secret: str | None = None,
    ) -> dict[str, str]:
        key = str(app_key or self.config.get("ds_app_key") or self.config.get("app_key") or "").strip()
        secret = str(app_secret or self.config.get("ds_app_secret") or self.config.get("app_secret") or "").strip()
        if not key or not secret:
            raise ConnectorDegradedError(
                status=ConnectorStatus.auth_failed,
                message="AliExpress Open Platform credentials are incomplete",
                connector_id=self.connector_id,
                detail={"missing": [name for name, value in (("app_key", key), ("app_secret", secret)) if not value]},
            )

        request_params: dict[str, str] = {
            "app_key": key,
            "method": method,
            "sign_method": "md5",
            "timestamp": self._top_timestamp(),
            "v": "2.0",
            "format": "json",
        }
        for name, value in params.items():
            if value is None:
                continue
            request_params[name] = self._top_value(value)
        request_params["sign"] = self._top_sign(request_params, secret)
        return request_params

    def _top_timestamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    def _top_value(self, value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float, Decimal)):
            return str(value)
        if isinstance(value, (dict, list)):
            return json.dumps(value, separators=(",", ":"), ensure_ascii=False, sort_keys=True)
        return str(value)

    def _top_sign(self, params: dict[str, str], secret: str) -> str:
        pieces = [secret]
        for key in sorted(k for k in params if k != "sign"):
            pieces.append(key)
            pieces.append(params[key])
        pieces.append(secret)
        digest = hashlib.md5("".join(pieces).encode("utf-8")).hexdigest().upper()
        return digest

    def _extract_top_response_payload(self, payload: Any) -> Any:
        if isinstance(payload, dict):
            for key in ("aliexpress_affiliate_product_query_response", "aliexpress_ds_product_get_response", "aliexpress_ds_auth_token_refresh_response"):
                value = payload.get(key)
                if isinstance(value, dict):
                    return value.get("result") or value.get("resp_result") or value.get("data") or value
            for key in ("result", "resp_result", "data", "response"):
                value = payload.get(key)
                if isinstance(value, dict):
                    return value
        return payload

    def _raise_for_top_response(self, response: httpx.Response, message: str) -> None:
        if response.status_code >= 400:
            response.raise_for_status()
        if response.status_code in {301, 302, 303, 307, 308}:
            location = response.headers.get("location", "")
            detail = {"status_code": response.status_code, "location": location}
            if "maintain.html" in location:
                detail["redirect"] = "maintain.html"
            raise ConnectorDegradedError(
                status=ConnectorStatus.unknown_error,
                message=message,
                connector_id=self.connector_id,
                detail=detail,
            )

    def _merge_listing_with_detail(self, listing: NormalizedListing, detail: dict[str, Any], pid: str) -> NormalizedListing:
        data = self._extract_ds_detail(detail)
        display_price = self._first_decimal(data, "displayPrice", "display_price", "price", "salePrice", "sale_price")
        original_price = self._first_decimal(data, "originalPrice", "original_price")
        shipping_cost = self._first_decimal(data, "shippingCost", "shipping_cost")
        seller = self._first_text(data, "shopName", "storeName", "sellerName", "seller_name")
        rating = self._first_decimal(data, "rating", "evaluateRate", "storeRating")
        sales = self._first_text(data, "sales", "salesCount", "orders", "sold")
        stock = self._first_bool(data, "inStock", "in_stock", "available")
        title = self._first_text(data, "title", "productTitle", "product_title") or listing.title_raw
        coupon_layers = self._extract_coupon_layers(data)

        enrichment = dict(listing.variant_normalized or {})
        enrichment.update(
            self._build_enrichment_payload(
                pid=pid,
                title=title,
                display_price=display_price or listing.price,
                original_price=original_price,
                shipping_cost=shipping_cost,
                seller=seller or listing.seller_or_store,
                rating=rating,
                sales=sales,
                stock=stock if stock is not None else listing.in_stock,
                source="ds",
            )
        )
        enrichment["aliexpress_coupon_layers"] = coupon_layers

        return listing.model_copy(
            update={
                "title_raw": title,
                "price": display_price or listing.price,
                "shipping_cost": shipping_cost if shipping_cost is not None else listing.shipping_cost,
                "total_landed_cost": (display_price + shipping_cost) if display_price and shipping_cost else listing.total_landed_cost,
                "seller_or_store": seller or listing.seller_or_store,
                "in_stock": stock if stock is not None else listing.in_stock,
                "variant_normalized": enrichment,
            }
        )

    def _extract_ds_detail(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = payload
        for key in ("data", "result", "item", "product", "productInfo"):
            value = data.get(key)
            if isinstance(value, dict):
                data = value
                break

        normalized = dict(data)

        # Real aliexpress.ds.product.get responses are heavily nested under
        # ae_item_* DTOs. Flatten the common fields we need so the existing
        # merge logic can treat DS and affiliate payloads consistently.
        base_info = data.get("ae_item_base_info_dto")
        if not isinstance(base_info, dict):
            base_info = {}

        sku_container = data.get("ae_item_sku_info_dtos")
        if not isinstance(sku_container, dict):
            sku_container = {}
        sku_list = sku_container.get("ae_item_sku_info_d_t_o") or sku_container.get("ae_item_sku_info_dto") or []
        first_sku = sku_list[0] if isinstance(sku_list, list) and sku_list and isinstance(sku_list[0], dict) else {}

        subject = self._first_text(base_info, "subject", "title", "productTitle", "product_title")
        if subject:
            normalized.setdefault("title", subject)

        display_price = self._first_text(first_sku, "offer_sale_price", "offerSalePrice", "displayPrice", "salePrice", "sale_price")
        if display_price:
            normalized.setdefault("displayPrice", display_price)

        original_price = self._first_text(first_sku, "sku_price", "skuPrice", "originalPrice", "price")
        if original_price:
            normalized.setdefault("originalPrice", original_price)

        sales = self._first_text(base_info, "sales_count", "salesCount", "sales", "orders", "sold")
        if sales:
            normalized.setdefault("sales", sales)

        rating = self._first_text(base_info, "avg_evaluation_rating", "avgEvaluationRating", "rating", "evaluateRate", "storeRating")
        if rating:
            normalized.setdefault("rating", rating)

        stock_count = first_sku.get("sku_available_stock")
        if stock_count is not None:
            try:
                normalized.setdefault("inStock", int(stock_count) > 0)
            except (TypeError, ValueError):
                pass

        currency = self._first_text(first_sku, "currency_code", "currencyCode", "currency")
        if currency:
            normalized.setdefault("currency", currency)

        return normalized

    def _extract_coupon_layers(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        coupons: list[dict[str, Any]] = []
        for key in ("coupons", "couponList", "discounts", "voucherList"):
            value = payload.get(key)
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        coupons.append(item)
        return coupons

    async def _apply_browser_enrichment(self, listings: list[NormalizedListing], filters: dict[str, Any]) -> list[NormalizedListing]:
        if self._browser_client is None:
            return listings
        enriched: list[NormalizedListing] = []
        for listing in listings:
            pid = self._normalize_pid(listing.source_listing_id) or self._extract_pid(listing.url)
            if not pid:
                enriched.append(listing)
                continue
            try:
                browser_detail = await self._fetch_browser_detail(pid)
            except ConnectorDegradedError:
                raise
            except Exception as exc:
                raise ConnectorDegradedError(
                    status=ConnectorStatus.unknown_error,
                    message="AliExpress browser enrichment failed",
                    connector_id=self.connector_id,
                    detail={"error": str(exc), "product_id": pid},
                ) from exc
            enriched.append(self._merge_listing_with_browser_detail(listing, browser_detail, pid))
        return enriched

    async def _fetch_browser_detail(self, pid: str) -> dict[str, Any]:
        url = f"https://www.aliexpress.com/item/{pid}.html"
        browser_client = self._browser_client
        assert browser_client is not None
        context = await browser_client.new_context()
        try:
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            html = await page.content()
        finally:
            await context.close()
        return self._parse_browser_html(html)

    def _parse_browser_html(self, html: str) -> dict[str, Any]:
        text = re.sub(r"\s+", " ", re.sub(r"<script.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE))
        return {
            "title": self._extract_first_pattern(
                html,
                [
                    r'<h1[^>]*>([^<]+)</h1>',
                    r'"title"\s*:\s*"([^"]+)"',
                    r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"',
                ],
            ),
            "display_price": self._extract_price(html),
            "original_price": self._extract_first_decimal_from_patterns(
                html,
                [
                    r'original[^\n]{0,80}?(?:£|GBP|\$|€)\s*([0-9]+(?:\.[0-9]{1,2})?)',
                    r'"originalPrice"\s*:\s*"?([0-9]+(?:\.[0-9]{1,2})?)"?',
                ],
            ),
            "effective_price": self._extract_first_decimal_from_patterns(
                html,
                [
                    r'effective[^\n]{0,80}?(?:£|GBP|\$|€)\s*([0-9]+(?:\.[0-9]{1,2})?)',
                ],
            ),
            "shipping_cost": self._extract_first_decimal_from_patterns(
                html,
                [
                    r'shipping[^\n]{0,80}?(?:£|GBP|\$|€)\s*([0-9]+(?:\.[0-9]{1,2})?)',
                ],
            ),
            "rating": self._extract_first_decimal_from_patterns(
                html,
                [r'([0-9]\.[0-9])\s*/\s*5', r'"ratingValue"\s*:\s*"?([0-9]\.[0-9])"?'],
            ),
            "sales": self._extract_first_pattern(
                text,
                [r'([0-9,]+)\s+(?:sold|orders)', r'([0-9,]+)\s+sales'],
            ),
            "coupons": self._extract_browser_coupons(text),
            "stock": None if not re.search(r"out of stock|sold out", text, re.IGNORECASE) else False,
        }

    def _extract_browser_coupons(self, text: str) -> list[dict[str, Any]]:
        coupons: list[dict[str, Any]] = []
        for match in re.finditer(r"(coupon|voucher|coins?|savings?)", text, re.IGNORECASE):
            start = max(0, match.start() - 40)
            end = min(len(text), match.end() + 80)
            coupons.append({"text": text[start:end].strip()})
        return coupons

    def _merge_listing_with_browser_detail(self, listing: NormalizedListing, detail: dict[str, Any], pid: str) -> NormalizedListing:
        display_price = self._to_decimal(detail.get("display_price")) or listing.price
        original_price = self._to_decimal(detail.get("original_price"))
        effective_price = self._to_decimal(detail.get("effective_price"))
        shipping_cost = self._to_decimal(detail.get("shipping_cost"))
        rating = self._to_decimal(detail.get("rating"))
        sales = detail.get("sales")
        title = detail.get("title") or listing.title_raw
        stock = detail.get("stock")
        coupons = detail.get("coupons") or []

        enrichment = dict(listing.variant_normalized or {})
        enrichment.update(
            self._build_enrichment_payload(
                pid=pid,
                title=title,
                display_price=display_price,
                original_price=original_price,
                shipping_cost=shipping_cost,
                seller=listing.seller_or_store,
                rating=rating,
                sales=sales,
                stock=stock if stock is not None else listing.in_stock,
                source="browser",
            )
        )
        if effective_price is not None:
            enrichment["aliexpress_effective_price"] = self._decimal_to_str(effective_price)
        enrichment["aliexpress_coupon_layers"] = coupons

        return listing.model_copy(
            update={
                "title_raw": title,
                "price": display_price,
                "shipping_cost": shipping_cost if shipping_cost is not None else listing.shipping_cost,
                "total_landed_cost": effective_price or (display_price + shipping_cost if display_price and shipping_cost else listing.total_landed_cost),
                "in_stock": stock if stock is not None else listing.in_stock,
                "variant_normalized": enrichment,
            }
        )

    def _dedupe_listings(self, listings: list[NormalizedListing]) -> list[NormalizedListing]:
        seen: set[tuple[str, str]] = set()
        deduped: list[NormalizedListing] = []
        for listing in listings:
            key = (listing.source, listing.source_listing_id)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(listing)
        return deduped

    def _extract_price(self, html: str) -> Decimal | None:
        for pattern in (
            r'"priceCurrency"\s*:\s*"[A-Z]{3}"\s*,\s*"price"\s*:\s*"?([0-9]+(?:\.[0-9]{1,2})?)"?',
            r'(?:£|GBP|\$|€)\s*([0-9]+(?:\.[0-9]{1,2})?)',
            r'"salePrice"\s*:\s*"?([0-9]+(?:\.[0-9]{1,2})?)"?',
        ):
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if match:
                return self._to_decimal(match.group(1))
        return None

    def _extract_first_decimal_from_patterns(self, text: str, patterns: list[str]) -> Decimal | None:
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                value = self._to_decimal(match.group(1))
                if value is not None:
                    return value
        return None

    def _extract_first_pattern(self, text: str, patterns: list[str]) -> str | None:
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        return None

    def _first_text(self, data: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = data.get(key)
            if value is None:
                continue
            if isinstance(value, str):
                text = value.strip()
                if text:
                    return text
            elif isinstance(value, (int, float, Decimal)):
                return str(value)
        return None

    def _first_decimal(self, data: dict[str, Any], *keys: str) -> Decimal | None:
        for key in keys:
            value = data.get(key)
            decimal = self._to_decimal(value)
            if decimal is not None:
                return decimal
        return None

    def _first_bool(self, data: dict[str, Any], *keys: str) -> bool | None:
        for key in keys:
            value = data.get(key)
            if value is None:
                continue
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"true", "yes", "y", "1", "in stock", "available"}:
                    return True
                if lowered in {"false", "no", "n", "0", "out of stock", "sold out"}:
                    return False
            if isinstance(value, (int, float)):
                return bool(value)
        return None

    def _to_decimal(self, value: Any) -> Decimal | None:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        text = str(value).strip()
        if not text:
            return None
        text = text.replace("£", "").replace("€", "").replace("GBP", "").replace("USD", "")
        text = text.replace(",", "")
        try:
            return Decimal(text)
        except InvalidOperation:
            return None

    def _decimal_to_str(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        normalized = value.normalize()
        return format(normalized, "f") if normalized == normalized.to_integral() else str(normalized)
