"""Resolve temporal offer evidence to retained direct captures, across routes.

Configuration/selection definitions are not temporal price or stock captures.
Extraction IDs and retrieval clocks never establish an acquisition origin.
"""

from dataclasses import dataclass, field
from datetime import datetime

from pricerecon.models.costs import CostEvidence
from pricerecon.models.discovery import DiscoveryCapture
from pricerecon.models.qualification import FieldEvidence, MerchantOffer

CaptureKey = tuple[str, str | None, str | None, str | None, str]


def temporal_claims(offer: MerchantOffer) -> list[FieldEvidence]:
    return [
        c
        for c in offer.evidence
        if c.subject == "offer" and c.field in {"item_price", "availability"}
    ]


def capture_key(claim: FieldEvidence, capture_id: str | None = None) -> CaptureKey:
    return (
        capture_id or claim.capture_id,
        claim.context.merchant_key,
        claim.context.product_id,
        claim.context.variation_id,
        claim.field,
    )


def lineage_claims(offer: MerchantOffer) -> list[tuple[CaptureKey, FieldEvidence | CostEvidence]]:
    claims: list[tuple[CaptureKey, FieldEvidence | CostEvidence]] = [
        (capture_key(c), c) for c in temporal_claims(offer)
    ]
    for scenario in offer.cost_scenarios:
        if scenario.kind != "public_no_coupon":
            continue
        groups = (
            [("context", scenario.context_evidence)]
            + [("component:" + c.kind, c.evidence) for c in scenario.components]
            + [("fx:" + fx.purpose, fx.evidence) for fx in scenario.fx_quotes]
        )
        for role, evidence in groups:
            for claim in evidence:
                context = claim.context
                claims.append(
                    (
                        (
                            claim.capture_id,
                            context.merchant_key,
                            context.product_id,
                            context.variation_id,
                            "cost:" + role + ":" + context.model_dump_json(),
                        ),
                        claim,
                    )
                )
    return claims


def origin_key(key: CaptureKey, origin: str) -> CaptureKey:
    return (origin, *key[1:])


@dataclass
class OfferLineage:
    owners: list[str] = field(default_factory=list)
    captures: set[str] = field(default_factory=set)
    observed_times: list[datetime] = field(default_factory=list)
    unknown: bool = False


class CaptureLineage:
    def __init__(self, retained: list[tuple[DiscoveryCapture, MerchantOffer]]) -> None:
        self.claims: dict[CaptureKey, FieldEvidence | CostEvidence] = {}
        self.owners: dict[CaptureKey, str] = {}
        self.by_id: dict[str, list[CaptureKey]] = {}
        self.application_captures: dict[CaptureKey, CaptureKey] = {}
        self.cached_origins: dict[CaptureKey, str] = {}
        for capture, offer in retained:
            for field_claim in offer.evidence:
                self.by_id.setdefault(field_claim.id, [])
            for key, claim in lineage_claims(offer):
                self.by_id.setdefault(claim.id, []).append(key)
                outcomes = [o for o in capture.outcomes if o.source == offer.source]
                if (
                    key not in self.claims
                    and len(outcomes) == 1
                    and outcomes[0].state == "cache_reuse"
                    and outcomes[0].reused_capture_id is not None
                ):
                    self.cached_origins[key] = outcomes[0].reused_capture_id
                # Later replays cannot rewrite the retained acquisition's origin.
                self.claims.setdefault(key, claim)
                self.application_captures[origin_key(key, capture.capture_id)] = key
                if (
                    claim.acquisition_capture_id == claim.capture_id
                    and len(outcomes) == 1
                    and outcomes[0].state in {"success", "partial"}
                    and capture.history_contract_version is not None
                ):
                    self.owners.setdefault(key, f"{capture.capture_id}:{offer.id}:{offer.revision}")

    def resolve(self, offer: MerchantOffer) -> OfferLineage:
        result = OfferLineage()
        claims = temporal_claims(offer)
        if {c.field for c in claims} != {"item_price", "availability"}:
            result.unknown = True
        # Iterative traversal keeps long retained extraction chains off the
        # Python call stack; active nodes expose cycles rather than invent roots.
        pending = [(key, False) for key, _ in lineage_claims(offer)]
        active: set[CaptureKey] = set()
        done: set[CaptureKey] = set()
        while pending:
            key, exiting = pending.pop()
            if exiting:
                active.remove(key)
                done.add(key)
                continue
            if key in active:
                result.unknown = True
                continue
            if key in done:
                continue
            result.captures.add(key[0])
            claim = self.claims.get(key)
            if claim is None:
                result.unknown = True
                done.add(key)
                continue
            result.captures.update(claim.derived_from)
            if claim.observed_at is not None:
                result.observed_times.append(claim.observed_at)
            parents = {
                origin_key(key, origin)
                for origin in claim.derived_from
                if origin != claim.capture_id and origin_key(key, origin) in self.claims
            }
            if claim.acquisition_capture_id not in {None, claim.capture_id}:
                parents.add(origin_key(key, claim.acquisition_capture_id))
            cached_origin = self.cached_origins.get(key)
            if cached_origin is not None:
                result.captures.add(cached_origin)
                parent = origin_key(key, cached_origin)
                parents.add(self.application_captures.get(parent, parent))
            for input_id in claim.input_claim_ids:
                inputs = self.by_id.get(input_id)
                if inputs is None:
                    result.unknown = True
                parents.update(parent for parent in inputs or [] if parent[1:] == key[1:])
            if not parents:
                owner = self.owners.get(key)
                if claim.acquisition_capture_id == claim.capture_id and owner is not None:
                    if key[4] in {"item_price", "availability"} and owner not in result.owners:
                        result.owners.append(owner)
                else:
                    result.unknown = True
                done.add(key)
            else:
                active.add(key)
                pending.append((key, True))
                pending.extend((parent, False) for parent in sorted(parents))
        return result
