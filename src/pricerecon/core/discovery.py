"""Staged category acquisition through the shared executor connector lifecycle."""

import hashlib
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

from pricerecon.core.acquisition import acquire_sources
from pricerecon.db.discovery import save_capture
from pricerecon.models.discovery import (
    AcquisitionOutcome,
    DiscoveryAdmission,
    DiscoveryCandidate,
    DiscoveryCapture,
    DiscoveryOrigin,
    DiscoveryRequest,
    LeadEvidence,
)


async def execute_discovery(
    request: DiscoveryRequest,
    *,
    admission: DiscoveryAdmission | None = None,
) -> DiscoveryCapture:
    """Normal one-shot entry point. No scheduler, notifications or live activation path.

    Offline verification must explicitly name its policy, permission and activation
    receipts. The default records a denied attempt without constructing connectors.
    """
    admission = admission or DiscoveryAdmission()
    capture_id = str(uuid4())
    captured_at = datetime.now(UTC)
    candidates: list[DiscoveryCandidate] = []
    by_id: dict[str, DiscoveryCandidate] = {}
    if admission.admitted:
        result = await acquire_sources(
            request.sources,
            query=request.query,
            source_queries=request.source_queries,
            filters={},
            context_id=capture_id,
            purpose="discovery",
        )
        outcomes = result.outcomes
        for lead in result.leads:
            listing = lead.listing
            key = hashlib.sha256(
                f"{request.category}\0{lead.source}\0{listing.source_listing_id}".encode()
            ).hexdigest()
            # No normalized confidence, title, stock or total flag certifies any
            # watch dimension, offer binding, landed cost or image permission.
            try:
                parts = urlsplit(listing.url)
                url = listing.url if parts.scheme in {"http", "https"} and parts.hostname else None
            except ValueError:
                url = None
            price = listing.price
            if price is not None and (not price.is_finite() or price < 0):
                price = None
            fields: list[tuple[Literal["title", "advertised_item_price"], str]] = [
                ("title", listing.title_raw)
            ]
            if price is not None:
                fields.append(("advertised_item_price", str(price)))
            evidence = [
                LeadEvidence(
                    id=f"{capture_id}:{key}:{field}:{hashlib.sha256(value.encode()).hexdigest()}",
                    subject=key,
                    field=field,
                    value=value,
                    issuer=lead.source,
                    captured_at=captured_at,
                    source_observed_at=listing.timestamp_seen,
                    capture_id=capture_id,
                    pointer=url,
                    derived_from=[f"{capture_id}:{lead.source}:{listing.source_listing_id}"],
                )
                for field, value in fields
            ]
            candidate = DiscoveryCandidate(
                id=key,
                source=lead.source,
                reported_source=listing.source,
                source_listing_id=listing.source_listing_id,
                title=listing.title_raw,
                query=lead.query,
                url=url,
                capture_id=capture_id,
                captured_at=captured_at,
                evidence=evidence,
                advertised_item_price=price,
                reported_currency=listing.currency or None,
            )
            previous = by_id.get(key)
            if previous is None:
                by_id[key] = candidate
                candidates.append(candidate)
            else:
                # Duplicated extraction within one capture is not independent
                # confirmation. Retain differing claims without resolving them.
                known_claims = {(claim.field, claim.value) for claim in previous.evidence}
                extra_claims = [
                    claim for claim in evidence if (claim.field, claim.value) not in known_claims
                ]
                if extra_claims:
                    previous.evidence.extend(extra_claims)
                    if (
                        "conflicting connector reports for the same listing"
                        not in previous.missing_data
                    ):
                        previous.missing_data.append(
                            "conflicting connector reports for the same listing"
                        )
    else:
        outcomes = [
            AcquisitionOutcome(
                source=source.connector,
                state="not_attempted",
                reason="source_disabled" if not source.enabled else "collection_staged",
            )
            for source in request.sources
        ]
    capture = DiscoveryCapture(
        capture_id=capture_id,
        captured_at=captured_at,
        request=DiscoveryOrigin(
            category=request.category,
            query=request.query,
            source_queries=request.source_queries,
            sources=[source.connector for source in request.sources],
        ),
        admission=admission,
        outcomes=outcomes,
    )
    save_capture(capture, candidates)
    return capture
