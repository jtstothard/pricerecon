#!/usr/bin/env python3
"""Bounded, read-only benchmark of PriceRecon Reddit acquisition lanes.

The same subreddit, query, and limit are used for every configured lane.  This
script does not write PriceRecon configuration, watches, or database state.
It prints JSON only; credentials and endpoint values are never emitted.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from pricerecon.config import load_config
from pricerecon.connectors.external_browser import ExternalBrowserAdapter
from pricerecon.connectors.reddit import (
    RedditHardwareSwapUKConnector,
    _parse_browser_posts,
)
from pricerecon.connectors.rss import TemplateConnector
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus

SECRET = re.compile(r"cookie|authorization|token|secret|password|session|api.?key|credential", re.IGNORECASE)


def safe_detail(value: Any) -> Any:
    """Keep diagnostic taxonomy while preventing accidental secret output."""
    if isinstance(value, dict):
        return {str(k): "[redacted]" if SECRET.search(str(k)) else safe_detail(v)
                for k, v in value.items() if not SECRET.search(str(k))}
    if isinstance(value, (list, tuple)):
        return [safe_detail(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value if not isinstance(value, str) else re.sub(
            r"(?i)(bearer\s+|https?://)[^\s]+", lambda m: "[redacted]" if m.group(0).lower().startswith("bearer") else m.group(0).split("?")[0], value
        )[:300]
    return str(type(value).__name__)


def query_terms(query: str) -> list[str]:
    return [x for x in re.split(r"[^a-z0-9]+", query.lower()) if x]


def hermes_env_value(name: str) -> str:
    """Read one non-secret routing value from Hermes' env file, if present."""
    path = Path.home() / ".hermes" / ".env"
    try:
        for line in path.read_text().splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip().strip("\"'")
    except OSError:
        pass
    return ""


def camofox_endpoint(config: dict[str, Any]) -> str:
    backends = config.get("browser_backends") or {}
    conn = (config.get("connectors") or {}).get("reddit_hardwareswapuk") or {}
    selection = conn.get("browser_backend") or config.get("browser_default")
    names = [selection] if isinstance(selection, str) else (selection or [])
    for name in names:
        value = backends.get(name) if isinstance(backends, dict) else None
        if isinstance(value, dict) and str(value.get("type", "")).lower() == "camofox":
            return str(value.get("endpoint") or "")
    return os.environ.get("CAMOFOX_URL") or os.environ.get("PRICERECON_CAMOFOX_URL") or hermes_env_value("CAMOFOX_URL")


def relevance(listings: list[Any], query: str) -> dict[str, Any]:
    terms = query_terms(query)
    matched = 0
    for listing in listings:
        variant = getattr(listing, "variant_normalized", None) or {}
        haystack = " ".join(str(x).lower() for x in (
            getattr(listing, "title_raw", ""), getattr(listing, "url", ""),
            variant.get("item_description"), variant.get("query"),
        ) if x)
        matched += int(all(term in haystack for term in terms))
    count = len(listings)
    return {"matched_count": matched, "returned_count": count,
            "match_rate": round(matched / count, 4) if count else None,
            "terms": terms}


def safe_listing_items(listings: list[Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for listing in listings:
        published = getattr(listing, "published_at", None)
        created_at = published.isoformat() if published is not None and hasattr(published, "isoformat") else published
        items.append({
            "id": getattr(listing, "id", None),
            "title": getattr(listing, "title_raw", None),
            "permalink": getattr(listing, "url", None),
            "created_at": created_at,
        })
    return items


def safe_rapi_posts(value: Any, limit: int) -> list[dict[str, Any]]:
    """Project browser-JS output to non-sensitive Reddit listing fields."""
    if not isinstance(value, list):
        raise TypeError("rAPI result was not a list")
    posts: list[dict[str, Any]] = []
    for raw in value[:limit]:
        if not isinstance(raw, dict):
            continue
        posts.append({key: raw.get(key) for key in ("id", "title", "permalink", "created_utc")})
    return posts


def rapi_expression(bundle: str, query: str, limit: int) -> str:
    """Load rAPI and perform one GET-only listing read in the page context."""
    bundle_literal = json.dumps(bundle)
    query_literal = json.dumps(query)
    return (
        "(async()=>{eval(" + bundle_literal + ");const out=[];"
        "for await(const p of rAPI.listing.feed(" + json.dumps("hardwareswapuk")
        + "," + json.dumps("new") + ",{" + "q:" + query_literal
        + ",restrict_sr:1,limit:" + str(limit) + "}))"
        "{const d=p&&p.data||{};out.push({id:d.id,title:d.title,permalink:d.permalink,created_utc:d.created_utc});}"
        "return out.slice(0," + str(limit) + ");})()"
    )


def load_rapi_bundle(path: str) -> str:
    bundle = Path(path).read_text()
    if not bundle.strip():
        raise ValueError("rAPI bundle is empty")
    return bundle


def configured_lanes(config: dict[str, Any]) -> dict[str, Any]:
    env = os.environ
    api_creds = bool((env.get("REDDIT_CLIENT_ID") and env.get("REDDIT_CLIENT_SECRET") and env.get("REDDIT_USER_AGENT")) or env.get("REDDIT_CREDENTIAL_FILE"))
    backends = config.get("browser_backends") or {}
    conn = (config.get("connectors") or {}).get("reddit_hardwareswapuk") or {}
    selection = conn.get("browser_backend") or config.get("browser_default")
    selected = [selection] if isinstance(selection, str) else (selection or [])
    if not selected and (env.get("CAMOFOX_URL") or env.get("PRICERECON_CAMOFOX_URL")):
        selected = ["__env_camofox__"]
    camofox = bool(camofox_endpoint(config))
    cloak_names = [name for name, value in backends.items() if isinstance(value, dict) and str(value.get("type", "")).lower() == "cloakbrowser"]
    return {"rss": True, "official_oauth": False, "official_oauth_credentials_present": api_creds,
            "rapi_browser_session": False, "camofox_snapshot": camofox,
            "camofox_profile_name": next((name for name in selected if name in backends and str(backends[name].get("type", "")).lower() == "camofox"), None) or ("reddit_auth" if camofox else None),
            "cloakbrowser": bool(cloak_names), "cloakbrowser_profile_names": cloak_names}


def base_record(lane: str, query: str, limit: int) -> dict[str, Any]:
    return {"lane": lane, "query": query, "subreddit": "hardwareswapuk", "limit": limit,
            "started_at": datetime.now(UTC).isoformat(), "latency_ms": None,
            "status": "not_run", "count": None, "relevance": None, "failure_taxonomy": None,
            "detail": {}}


async def run_lane(lane: str, connector: RedditHardwareSwapUKConnector, query: str, limit: int, config: dict[str, Any], rapi_bundle: str | None = None) -> dict[str, Any]:
    rec = base_record(lane, query, limit)
    started = time.perf_counter()
    try:
        listings: list[Any]
        if lane == "rss":
            raw = await TemplateConnector.search(connector, query, {"limit": limit})
            listings = connector._finalize(raw, query)
        elif lane == "rapi_browser_session":
            endpoint = camofox_endpoint(config)
            connector._external_browser = ExternalBrowserAdapter.from_config(
                {"browser_backends": {"reddit_auth": {"type": "camofox", "endpoint": endpoint,
                    "options": {"user_id": os.environ.get("PRICERECON_REDDIT_CAMOFOX_USER_ID") or "reddit_auth",
                                "session_key": os.environ.get("PRICERECON_REDDIT_CAMOFOX_SESSION_KEY") or "reddit_auth",
                                "api_key": os.environ.get("CAMOFOX_API_KEY", "")}}},
                 "browser_default": "reddit_auth"})
            raw = await connector._external_browser.evaluate_readonly(
                f"https://www.reddit.com/r/hardwareswapuk/new/?q={query.replace(' ', '+')}&restrict_sr=1",
                rapi_expression(rapi_bundle or "", query, limit),
            )
            posts = safe_rapi_posts(raw, limit)
            rec.update(status="ok" if posts else "healthy_empty", count=len(posts),
                       relevance={"matched_count": sum(query.lower() in str(p.get("title", "")).lower() for p in posts),
                                  "returned_count": len(posts), "match_rate": (1.0 if posts else None), "terms": query_terms(query)},
                       items=posts)
            return rec
        elif lane == "official_oauth":
            raise ConnectorDegradedError(ConnectorStatus.auth_failed, "official Reddit OAuth unavailable", connector.connector_id)
        elif lane == "camofox_snapshot":
            # The requested persistent profile is named reddit_auth. Only the
            # endpoint is read from the local runtime environment; no secret is
            # loaded or printed. Explicit PriceRecon env identifiers still win.
            endpoint = camofox_endpoint(config)
            user_id = os.environ.get("PRICERECON_REDDIT_CAMOFOX_USER_ID") or "reddit_auth"
            session_key = os.environ.get("PRICERECON_REDDIT_CAMOFOX_SESSION_KEY") or "reddit_auth"
            connector._external_browser = ExternalBrowserAdapter.from_config(
                {"browser_backends": {"reddit_auth": {"type": "camofox", "endpoint": endpoint,
                    "options": {"user_id": user_id, "session_key": session_key,
                                "api_key": os.environ.get("CAMOFOX_API_KEY", "")}}},
                 "browser_default": "reddit_auth"}
            )
            listings = connector._finalize(await connector._search_camofox(query, {"limit": limit}), query)
        elif lane == "cloakbrowser":
            name = (configured_lanes(config)["cloakbrowser_profile_names"] or [None])[0]
            backend = (config.get("browser_backends") or {}).get(name, {})
            adapter = ExternalBrowserAdapter.from_config({"browser_backends": {name: backend}, "browser_default": name})
            url = f"https://www.reddit.com/r/hardwareswapuk/new/?q={query.replace(' ', '+')}&restrict_sr=1"
            result = await adapter.navigate(url)
            if result.degraded:
                raise ConnectorDegradedError(ConnectorStatus.unknown_error, "CloakBrowser degraded", connector.connector_id, {"degradation": result.degradation.value, "attempts": [a.degradation.value for a in result.attempts]})
            content = result.rendered.html or result.rendered.snapshot
            entries = _parse_browser_posts(content, "hardwareswapuk", limit, query=query)
            listings = connector._finalize([connector._entry_to_listing(e) for e in entries], query)
        else:
            raise ValueError(f"unknown lane {lane}")
        rec.update(status="ok" if listings else "healthy_empty", count=len(listings), relevance=relevance(listings, query), items=safe_listing_items(listings))
    except ConnectorDegradedError as exc:
        rec.update(status="failed", failure_taxonomy=exc.status.value, detail=safe_detail(exc.detail or {}))
    except TimeoutError as exc:
        rec.update(status="failed", failure_taxonomy="timeout", detail={"error_type": type(exc).__name__})
    except Exception as exc:  # noqa: BLE001 - benchmark must classify unexpected lane failures
        taxonomy = "transport_error" if exc.__class__.__module__.startswith("httpx") else "unknown_error"
        detail: dict[str, Any] = {"error_type": type(exc).__name__}
        if isinstance(exc, httpx.HTTPStatusError):
            detail["status_code"] = exc.response.status_code
            taxonomy = "browser_http_error"
        else:
            detail["error"] = safe_detail(str(exc))
        rec.update(status="failed", failure_taxonomy=taxonomy, detail=detail)
    finally:
        rec["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return rec


async def main(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    availability = configured_lanes(config)
    connector = RedditHardwareSwapUKConnector()
    records: list[dict[str, Any]] = []
    rapi_bundle = None
    if args.rapi_bundle:
        try:
            rapi_bundle = load_rapi_bundle(args.rapi_bundle)
        except OSError:
            pass
    availability["official_oauth"] = False
    availability["rapi_browser_session"] = bool(rapi_bundle and availability.get("camofox_snapshot"))
    availability["camofox_snapshot"] = availability.get("camofox_snapshot", False)
    for lane in ("rss", "official_oauth", "rapi_browser_session", "camofox_snapshot", "cloakbrowser"):
        if not availability.get(lane):
            rec = base_record(lane, args.query, args.limit)
            rec.update(status="unavailable", failure_taxonomy="configuration_gap", detail={"reason": "lane not configured"})
            records.append(rec)
        else:
            records.append(await run_lane(lane, connector, args.query, args.limit, config, rapi_bundle))
    await connector.cleanup()
    output = {"schema_version": "1.1", "generated_at": datetime.now(UTC).isoformat(),
              "method": {"fixed_query": args.query, "fixed_limit": args.limit, "order": ["rss", "official_oauth", "rapi_browser_session", "camofox_snapshot", "cloakbrowser"], "sequential": True},
              "availability": availability, "results": records}
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default="RTX")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--config", default="config.yml")
    parser.add_argument("--rapi-bundle", default="", help="built rAPI IIFE bundle (e.g. /tmp/rapi-src/dist/main.global.js)")
    asyncio.run(main(parser.parse_args()))
