"""Shared connector lifecycle from the Watch executor. No scheduling or notifications."""

import logging
from dataclasses import dataclass
from typing import Any, Literal

import httpx
from pydantic import ValidationError

from pricerecon.config import load_config
from pricerecon.connectors.browser_client import BrowserClient, BrowserSessionConfig
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus
from pricerecon.core.connector_health import upsert_connector_health
from pricerecon.models import NormalizedListing
from pricerecon.models.discovery import AcquisitionOutcome
from pricerecon.models.qualification import EvidenceSearchReport, MerchantEvidenceReport
from pricerecon.models.watches import SourceConfig

logger = logging.getLogger(__name__)


def _non_empty_error_message(exc: Exception) -> str:
    return str(exc).strip() or exc.__class__.__name__


@dataclass
class AcquiredLead:
    source: str
    query: str
    listing: NormalizedListing
    evidence_report: MerchantEvidenceReport | None = None


@dataclass
class AcquisitionResult:
    listings: list[NormalizedListing]
    failed_sources: set[str]
    outcomes: list[AcquisitionOutcome]
    leads: list[AcquiredLead]


async def acquire_sources(
    sources: list[SourceConfig],
    *,
    query: str,
    source_queries: dict[str, str],
    filters: dict[str, Any],
    context_id: int | str,
    purpose: Literal["watch", "discovery"] = "watch",
) -> AcquisitionResult:
    """Use the existing registry, config, health, lifecycle and search boundary."""
    runtime_config = load_config()
    connector_defaults = (
        runtime_config.get("connectors", {}) if isinstance(runtime_config, dict) else {}
    )

    all_listings: list[NormalizedListing] = []
    leads: list[AcquiredLead] = []
    outcomes: list[AcquisitionOutcome] = []
    failed_sources: set[str] = set()

    for source in sources:
        if not source.enabled:
            outcomes.append(
                AcquisitionOutcome(
                    source=source.connector, state="not_attempted", reason="source_disabled"
                )
            )
            continue
        from pricerecon.connectors import canonical_connector_id

        connector_id = canonical_connector_id(source.connector)
        if not connector_id:
            continue

        # Failed/skipped acquisition is not evidence of disappearance. Only a
        # completed search (including an empty result) replaces this snapshot.
        failed_sources.add(connector_id)

        # Check health state: skip connectors with fresh auth_failed errors
        from pricerecon.core.connector_health import is_health_stale, list_connector_health

        health_state = list_connector_health().get(connector_id, {})
        if health_state.get("status") == "auth_failed":
            if not is_health_stale(connector_id):
                logger.warning(
                    f"{purpose}_connector_skipped_fresh_auth_failed",
                    extra={f"{purpose}_id": context_id, "connector": connector_id},
                )
                outcomes.append(
                    AcquisitionOutcome(
                        source=connector_id, state="blocked", reason="fresh_auth_failed"
                    )
                )
                continue
            logger.info(
                f"{purpose}_connector_retrying_stale_auth_failed",
                extra={f"{purpose}_id": context_id, "connector": connector_id},
            )

        connector = None
        try:
            logger.info(
                f"{purpose}_connector_start",
                extra={f"{purpose}_id": context_id, "connector": connector_id},
            )
            # Use entry-point registry to resolve connector_id -> class
            from pricerecon.connectors import discover_connectors

            all_connectors = discover_connectors()
            connector_class = all_connectors.get(connector_id)
            if connector_class is None:
                raise AttributeError(
                    f"Connector '{connector_id}' not found in registry. "
                    f"Available: {sorted(all_connectors.keys())}"
                )
            # Build connector kwargs: merge config-file defaults, env-level credentials,
            # and per-watch config. Per-watch config takes precedence.
            config_defaults = dict(connector_defaults.get(connector_id, {}) or {})
            connector_kwargs: dict[str, Any] = {**config_defaults, **dict(source.config or {})}
            if connector_id == "ebay":
                import os

                # A persisted config may contain a null app_id (for example, when
                # a watch was created before credentials were configured). Treat
                # null/empty values as unset so the deployed environment remains
                # the source of truth for the OAuth client id.
                if not connector_kwargs.get("app_id"):
                    connector_kwargs["app_id"] = os.environ.get("EBAY_APP_ID", "")
                connector_kwargs.setdefault("cert_id", os.environ.get("EBAY_CERT_ID"))
            elif connector_id == "dell_uk":
                import os

                # Dell requires serialized HTML; prefer the shared
                # FlareSolverr/Byparr-compatible endpoint over Camofox's a11y
                # snapshot backend. Per-watch config still takes precedence.
                if not connector_kwargs.get("flaresolverr_url"):
                    connector_kwargs["flaresolverr_url"] = runtime_config.get(
                        "flaresolverr_url"
                    ) or os.environ.get("PRICERECON_FLARESOLVERR_URL")
            elif connector_id == "aliexpress":
                import os

                cfg = {**config_defaults, **dict(source.config or {})}
                cfg.setdefault("app_key", os.environ.get("ALIEXPRESS_APP_KEY"))
                cfg.setdefault("app_secret", os.environ.get("ALIEXPRESS_APP_SECRET"))
                cfg.setdefault("ds_app_key", os.environ.get("ALIEXPRESS_DS_APP_KEY"))
                cfg.setdefault("ds_app_secret", os.environ.get("ALIEXPRESS_DS_APP_SECRET"))
                cfg.setdefault("ds_access_token", os.environ.get("ALIEXPRESS_DS_ACCESS_TOKEN"))
                cfg.setdefault("ds_refresh_token", os.environ.get("ALIEXPRESS_DS_REFRESH_TOKEN"))
                browser_client = None
                camofox_url = (
                    cfg.get("camofox_url")
                    or os.environ.get("ALIEXPRESS_CAMOFOX_URL")
                    or os.environ.get("CAMOFOX_URL")
                )
                cfg.setdefault("camofox_url", camofox_url)
                if camofox_url:
                    browser_client = BrowserClient(
                        config=BrowserSessionConfig(
                            camofox_url=str(camofox_url),
                            camofox_user_id=str(
                                cfg.get("camofox_user_id") or f"pricerecon_{context_id}"
                            ),
                            camofox_session_key=str(
                                cfg.get("camofox_session_key") or f"{purpose}_{context_id}"
                            ),
                            camofox_api_key=os.environ.get("CAMOFOX_API_KEY"),
                            camofox_access_key=os.environ.get("CAMOFOX_ACCESS_KEY"),
                        )
                    )
                connector_kwargs = {"config": cfg}
                if browser_client is not None:
                    connector_kwargs["browser_client"] = browser_client
            elif connector_id == "hotukdeals":
                import os

                cfg = {**config_defaults, **dict(source.config or {})}
                browser_client = None
                camofox_url = cfg.get("camofox_url") or os.environ.get("CAMOFOX_URL")
                cfg.setdefault("camofox_url", camofox_url)
                if camofox_url:
                    browser_client = BrowserClient(
                        config=BrowserSessionConfig(
                            camofox_url=str(camofox_url),
                            camofox_user_id=str(
                                cfg.get("camofox_user_id") or f"pricerecon_{context_id}"
                            ),
                            camofox_session_key=str(
                                cfg.get("camofox_session_key") or f"{purpose}_{context_id}"
                            ),
                            camofox_api_key=os.environ.get("CAMOFOX_API_KEY"),
                            camofox_access_key=os.environ.get("CAMOFOX_ACCESS_KEY"),
                        )
                    )
                connector_kwargs = {"config": cfg}
                if browser_client is not None:
                    connector_kwargs["browser_client"] = browser_client
            try:
                from pricerecon.connectors.factory import validate_and_create_connector

                connector = validate_and_create_connector(
                    connector_class, connector_id, connector_kwargs
                )
                # This is deliberately post-construction: every BaseConnector
                # can receive the shared named-backend selection without
                # expanding its public constructor or changing its direct/API
                # default. The structural guard keeps existing plugin/test
                # doubles compatible with the executor contract.
                configure_browser = getattr(connector, "configure_external_browser", None)
                if callable(configure_browser):
                    configure_browser(runtime_config, config_defaults | dict(source.config or {}))
            except Exception as exc:
                raise ConnectorDegradedError(
                    status=ConnectorStatus.unknown_error,
                    message=f"Failed to create connector '{connector_id}': {exc}",
                    connector_id=connector_id,
                    detail={"error": str(exc), "error_type": exc.__class__.__name__},
                ) from exc
            await connector.initialize()
            connector_filters = {}
            connector_filters.update(filters)
            # Use per-connector query if available, otherwise fall back to watch.query
            effective_query = source_queries.get(connector_id, query)
            evidence_reports: list[MerchantEvidenceReport] = []
            inspect = getattr(connector, "search_with_evidence", None)
            if purpose == "discovery" and callable(inspect):
                try:
                    report = await inspect(effective_query, connector_filters)
                except ValidationError:
                    raise ConnectorDegradedError(
                        status=ConnectorStatus.parse_error,
                        message="Invalid typed evidence report",
                        connector_id=connector_id,
                    ) from None
                if not isinstance(report, EvidenceSearchReport):
                    raise ConnectorDegradedError(
                        status=ConnectorStatus.parse_error,
                        message="Expected a typed evidence report",
                        connector_id=connector_id,
                    )
                try:
                    # Revalidate nested models as adapters may have constructed
                    # or mutated them without normal Pydantic validation.
                    report = EvidenceSearchReport.model_validate_json(report.model_dump_json())
                except ValidationError:
                    raise ConnectorDegradedError(
                        status=ConnectorStatus.parse_error,
                        message="Invalid typed evidence report",
                        connector_id=connector_id,
                    ) from None
                listings = report.listings
                evidence_reports = report.evidence
            else:
                listings = await connector.search(effective_query, connector_filters)
            all_listings.extend(listings)
            for listing in listings:
                matching: dict[
                    tuple[str | None, str | None, str | None], MerchantEvidenceReport
                ] = {}
                for report in evidence_reports:
                    if report.source_listing_id != listing.source_listing_id:
                        continue
                    locator = (report.merchant_key, report.product_id, report.variation_id)
                    if locator not in matching:
                        matching[locator] = report.model_copy(deep=True)
                    else:
                        retained = matching[locator]
                        known = {claim.model_dump_json() for claim in retained.claims}
                        retained.claims.extend(
                            claim for claim in report.claims if claim.model_dump_json() not in known
                        )
                for retained in matching.values():
                    known = {claim.model_dump_json() for claim in retained.claims}
                    for related in matching.values():
                        # Missing subject keys do not establish a shared
                        # manufacturer definition across selected variations.
                        if (
                            not retained.configuration_key
                            or retained.configuration_key != related.configuration_key
                        ):
                            continue
                        retained.claims.extend(
                            claim
                            for claim in related.claims
                            if claim.subject == "configuration"
                            and claim.model_dump_json() not in known
                        )
                        known = {claim.model_dump_json() for claim in retained.claims}
                if matching:
                    leads.extend(
                        AcquiredLead(connector_id, effective_query, listing, report)
                        for report in matching.values()
                    )
                else:
                    leads.append(AcquiredLead(connector_id, effective_query, listing))
            failed_sources.discard(connector_id)
            outcomes.append(
                AcquisitionOutcome(
                    source=connector_id,
                    state="success" if listings else "success_empty",
                    listing_count=len(listings),
                )
            )
            logger.info(
                f"{purpose}_connector_result",
                extra={
                    f"{purpose}_id": context_id,
                    "connector": connector_id,
                    "listing_count": len(listings),
                },
            )
            upsert_connector_health(
                connector_id,
                "ok",
                details={"listing_count": len(listings), "inference_source": purpose},
            )
        except ConnectorDegradedError as exc:
            outcomes.append(
                AcquisitionOutcome(
                    source=connector_id,
                    state=(
                        "capped"
                        if (exc.detail or {}).get("capped")
                        else "blocked"
                        if exc.status
                        in {
                            ConnectorStatus.bot_blocked,
                            ConnectorStatus.auth_failed,
                            ConnectorStatus.rate_limited,
                            ConnectorStatus.disabled,
                        }
                        else "failed"
                    ),
                    reason=exc.status.value,
                )
            )
            logger.warning(
                f"{purpose}_connector_degraded",
                extra={
                    f"{purpose}_id": context_id,
                    "connector": connector_id,
                    "status": exc.status.value,
                    "error": exc.message,
                    "detail": exc.detail,
                },
            )
            last_error = exc.message.strip() if exc.message else exc.status.value
            details = dict(exc.detail) if exc.detail else {}
            details["inference_source"] = purpose
            upsert_connector_health(
                connector_id, exc.status.value, last_error=last_error, details=details
            )
            continue
        except httpx.TimeoutException as exc:
            outcomes.append(
                AcquisitionOutcome(source=connector_id, state="failed", reason="timeout")
            )
            message = _non_empty_error_message(exc)
            upsert_connector_health(
                connector_id,
                "timeout",
                last_error=message,
                details={
                    "error": message,
                    "error_type": exc.__class__.__name__,
                    "inference_source": purpose,
                },
            )
            continue
        except Exception as exc:
            outcomes.append(
                AcquisitionOutcome(source=connector_id, state="failed", reason="connector_error")
            )
            message = _non_empty_error_message(exc)
            upsert_connector_health(
                connector_id,
                "unknown_error",
                last_error=message,
                details={
                    "error": message,
                    "error_type": exc.__class__.__name__,
                    "inference_source": purpose,
                },
            )
            logger.exception(
                f"{purpose}_connector_error",
                extra={f"{purpose}_id": context_id, "connector": connector_id},
            )
        finally:
            if connector is not None:
                try:
                    await connector.cleanup()
                except Exception:
                    logger.exception("connector_cleanup_failed", extra={"connector": connector_id})

    return AcquisitionResult(all_listings, failed_sources, outcomes, leads)
