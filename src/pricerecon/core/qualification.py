"""Resolve attributable fields; never use lead scores or count claims as votes."""

import hashlib
import json
from datetime import datetime
from decimal import Decimal

from pricerecon.models.qualification import (
    FieldEvidence,
    MerchantEvidenceReport,
    MerchantOffer,
    Resolution,
    ResolutionIssue,
    SelectionBinding,
    safe_pointer,
)


def canonical_decimal(value: str) -> str:
    rendered = format(Decimal(value), "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def identity_key(*parts: str) -> str:
    return hashlib.sha256(json.dumps(parts, ensure_ascii=True).encode()).hexdigest()


def resolve_fields(
    report: MerchantEvidenceReport,
    fields: tuple[str, ...],
    *,
    subject: str,
    captured_at: datetime,
    not_applicable_fields: tuple[str, ...] = (),
) -> Resolution:
    result = Resolution()
    for field in fields:
        accepted: dict[str | Decimal, list[FieldEvidence]] = {}
        for claim in report.claims:
            if claim.subject != subject or claim.field != field:
                continue
            reason = rejection_reason(claim, report, subject, captured_at)
            if claim.assertion_state == "unknown" or claim.value.strip().casefold() in {
                "unknown",
                "unspecified",
                "not known",
                "missing",
                "n/a",
                "none",
                "?",
            }:
                reason = "unknown_assertion"
            if (
                claim.assertion_state == "not_applicable"
                and claim.field not in not_applicable_fields
            ):
                reason = "required_dimension_not_applicable"
            if (
                claim.value.strip().casefold() == "not_applicable"
                and claim.assertion_state != "not_applicable"
            ):
                reason = "applicability_not_evidenced"
            if reason:
                result.issues.append(
                    ResolutionIssue(field=field, code=reason, evidence_ids=[claim.id])
                )
                continue
            # Case and surrounding whitespace are the only text normalization.
            # Never strip reference suffixes or guess aliases/units from titles.
            value: str | Decimal = (
                Decimal(claim.value)
                if field in {"case_width_mm", "quantity", "item_price"}
                else claim.value.strip().casefold()
            )
            if claim.assertion_state == "not_applicable":
                value = "not_applicable"
            accepted.setdefault(value, []).append(claim)
        if len(accepted) > 1:
            result.issues.append(
                ResolutionIssue(
                    field=field,
                    code="conflicting_claims",
                    evidence_ids=[claim.id for claims in accepted.values() for claim in claims],
                )
            )
        elif accepted:
            value, claims = next(iter(accepted.items()))
            # Preserve issuer spelling for display and ISO currency/country codes.
            original = (
                "not_applicable"
                if claims[0].assertion_state == "not_applicable"
                else claims[0].value.strip()
            )
            result.values[field] = str(int(Decimal(original))) if field == "quantity" else original
            result.evidence_ids.extend(claim.id for claim in claims)
        else:
            result.issues.append(ResolutionIssue(field=field, code="missing_evidence"))
    result.state = (
        "conflicting"
        if any(i.code == "conflicting_claims" for i in result.issues)
        else "supported"
        if len(result.values) == len(fields)
        else "unresolved"
    )
    return result


def rejection_reason(
    claim: FieldEvidence,
    report: MerchantEvidenceReport,
    subject: str,
    captured_at: datetime,
) -> str | None:
    if safe_pointer(claim.pointer) is None:
        return "invalid_evidence_pointer"
    if claim.observed_at is None:
        return "observation_time_unknown"
    if claim.observed_at > claim.retrieved_at or claim.retrieved_at > captured_at:
        return "invalid_evidence_time"
    if claim.extractor_kind in {"ai", "human"} or claim.issuer_kind in {
        "ai_inference",
        "human_correction",
        "search_lead",
    }:
        return "derived_claim_not_independent_support"
    if claim.input_claim_ids:
        return "derived_claim_not_independent_support"
    if subject == "configuration":
        if claim.issuer_kind != "manufacturer":
            return "manufacturer_definition_missing"
        if (
            not report.configuration_key
            or claim.context.configuration_key != report.configuration_key
        ):
            return "configuration_context_mismatch"
        if claim.context.scope != "configuration":
            return "configuration_context_mismatch"
    else:
        if claim.issuer_kind != "seller":
            return "selected_merchant_claim_missing"
        context = claim.context
        if not all((report.merchant_key, report.product_id, report.variation_id)):
            return "selected_variation_id_missing"
        if context.scope != "selected_variation" or (
            context.merchant_key,
            context.product_id,
            context.variation_id,
        ) != (report.merchant_key, report.product_id, report.variation_id):
            return "selection_context_mismatch"
        if not report.destination or report.quantity is None or not report.currency:
            return "purchase_context_missing"
        if (context.destination, context.quantity, context.currency) != (
            report.destination,
            report.quantity,
            report.currency,
        ):
            return "purchase_context_mismatch"
        if not context.destination or context.quantity is None:
            return "purchase_context_missing"
    return None


OFFER_FIELDS = (
    "seller",
    "condition",
    "quantity",
    "availability",
    "purchase_mode",
    "item_price",
    "currency",
    "destination",
)


def qualify_offer(
    source: str,
    report: MerchantEvidenceReport,
    binding: SelectionBinding,
    captured_at: datetime,
) -> MerchantOffer:
    result = resolve_fields(report, OFFER_FIELDS, subject="offer", captured_at=captured_at)
    values = result.values
    for claim in report.claims:
        if claim.id not in result.evidence_ids:
            continue
        if str(claim.context.quantity) != values.get(
            "quantity"
        ) or claim.context.destination != values.get("destination"):
            result.issues.append(
                ResolutionIssue(
                    field=claim.field, code="purchase_context_mismatch", evidence_ids=[claim.id]
                )
            )
            result.state = "conflicting"
    if binding.resolution.state != "supported":
        result.issues.append(ResolutionIssue(field="binding", code="selection_not_supported"))
        result.state = "unresolved" if result.state == "supported" else result.state
    if values.get("availability") == "out_of_stock":
        result.issues.append(ResolutionIssue(field="availability", code="unavailable"))
        result.state = "rejected"
    offer = MerchantOffer(
        id=identity_key(
            source,
            report.merchant_key or "",
            report.product_id or report.source_listing_id,
            report.variation_id or "unresolved",
            "offer",
        ),
        binding_id=binding.id,
        source=source,
        source_listing_id=report.source_listing_id,
        qualification=result,
        seller=values.get("seller"),
        condition=values.get("condition"),
        quantity=int(values["quantity"]) if "quantity" in values else None,
        availability=values.get("availability"),
        purchase_mode=values.get("purchase_mode"),
        item_price=(
            Decimal(values["item_price"]) if Decimal(values["item_price"]) != 0 else Decimal(0)
        )
        if "item_price" in values
        else None,
        currency=values.get("currency"),
        destination=values.get("destination"),
        evidence=[c.model_copy(update={"pointer": safe_pointer(c.pointer)}) for c in report.claims],
    )
    for field in ("condition_description", "visible_condition"):
        optional = resolve_fields(report, (field,), subject="offer", captured_at=captured_at)
        if any(c.subject == "offer" and c.field == field for c in report.claims):
            result.issues.extend(optional.issues)
        if field == "condition_description":
            offer.condition_description = optional.values.get(field)
        else:
            offer.visible_condition = optional.values.get(field)
    issues = [
        ResolutionIssue(field="cost", code="uk_cost_unknown"),
        ResolutionIssue(field="freshness", code="freshness_unvalidated"),
    ]
    if result.state != "supported":
        issues.append(ResolutionIssue(field="offer", code="offer_not_supported"))
    if values.get("purchase_mode") != "buy_now":
        issues.append(ResolutionIssue(field="purchase_mode", code="not_fixed_purchase_price"))
    if values.get("destination") != "GB":
        issues.append(ResolutionIssue(field="destination", code="uk_delivery_unproven"))
    if offer.condition in {"used", "refurbished"} and not offer.condition_description:
        issues.append(ResolutionIssue(field="condition", code="item_condition_details_missing"))
    excluded = (
        result.state == "rejected"
        or binding.resolution.state == "rejected"
        or offer.purchase_mode in {"auction", "best_offer"}
        or (offer.destination is not None and offer.destination != "GB")
    )
    offer.comparison = Resolution(state="rejected" if excluded else "unresolved", issues=issues)
    if binding.resolution.state == "supported" and offer.condition and offer.purchase_mode:
        # A prospective grouping key, never a qualified comparison. Used item
        # details, quantity and destination cannot collapse into a new-goods group.
        detail = identity_key(offer.condition_description or "condition-details-unknown")
        offer.comparison_cohort = (
            f"{binding.configuration_id}:{offer.destination}:{offer.currency}:{offer.quantity}:"
            f"{detail}:{offer.condition}:{offer.purchase_mode}"
        )
    return offer
