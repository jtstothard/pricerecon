"""Watch preferences are buyer definitions, never facts inferred from a lead title."""

from datetime import datetime

from pricerecon.models.discovery import PreferenceFit, PreferenceInterpretation, WatchPreferences
from pricerecon.models.qualification import Configuration, MerchantEvidenceReport, SelectionBinding


def interpret(preferences: WatchPreferences) -> list[PreferenceInterpretation]:
    return [
        PreferenceInterpretation(
            field="compact",
            strength=(
                preferences.compact_strength
                if preferences.compact_max_width_mm is not None
                else "unset"
            ),
            meaning=(
                f"Compact means case width at most {preferences.compact_max_width_mm} mm."
                if preferences.compact_max_width_mm is not None
                else "Compact is unset; choose a maximum case width."
            ),
        ),
        PreferenceInterpretation(
            field="colourful",
            strength=(preferences.colourful_strength if preferences.colourful_dials else "unset"),
            meaning=(
                "Colourful means one of these dial colours: "
                + ", ".join(preferences.colourful_dials)
                + "."
                if preferences.colourful_dials
                else "Colourful is unset; choose the dial colours you want."
            ),
        ),
        PreferenceInterpretation(
            field="budget",
            strength=(
                preferences.budget_strength if preferences.budget_gbp is not None else "unset"
            ),
            meaning=(
                f"Budget means public UK delivered total at most £{preferences.budget_gbp}; item price alone is insufficient."
                if preferences.budget_gbp is not None
                else "Budget is unset; choose a public UK delivered budget."
            ),
        ),
    ]


def lead_preference_fit(preferences: WatchPreferences) -> list[PreferenceFit]:
    reasons = {
        "compact": "Case width unknown; compact fit needs checking.",
        "colourful": "Dial colour unknown; title words and illustrations do not confirm colour.",
        "budget": "Delivered total unknown; an item price cannot satisfy this budget.",
    }
    return [
        PreferenceFit(
            field=rule.field,
            strength=rule.strength,
            state="unset" if rule.strength == "unset" else "unknown",
            reason="No preference set." if rule.strength == "unset" else reasons[rule.field],
        )
        for rule in interpret(preferences)
    ]


# Category policy owns the dimensions and exact comparisons, including suffix,
# date/no-date and case-width axis. No family-specific product catalogue is inferred.
IDENTITY_FIELDS = (
    "product_kind",
    "maker",
    "reference",
    "generation",
    "movement",
    "case_width_mm",
    "dial",
    "strap",
    "date_display",
)


def resolve_watch(
    report: MerchantEvidenceReport,
    captured_at: datetime,
    fallback_id: str,
    source: str,
) -> tuple[Configuration, SelectionBinding]:
    """Manufacturer identity and merchant binding are independent resolutions."""
    from decimal import Decimal

    from pricerecon.core.qualification import canonical_decimal, identity_key, resolve_fields
    from pricerecon.models.qualification import Configuration, ResolutionIssue, SelectionBinding

    identity = resolve_fields(
        report,
        IDENTITY_FIELDS,
        subject="configuration",
        captured_at=captured_at,
        not_applicable_fields=("generation",),
    )
    if identity.values.get("product_kind") in {"accessory", "component"}:
        identity.state = "rejected"
        identity.issues.append(ResolutionIssue(field="product_kind", code="not_complete_watch"))
    if identity.state == "supported":
        config_id = identity_key(
            "watches",
            *(
                (
                    canonical_decimal(identity.values[field])
                    if field == "case_width_mm"
                    else identity.values[field].strip().casefold()
                )
                for field in IDENTITY_FIELDS
            ),
        )
    elif report.configuration_key:
        # An unresolved ID identifies the retained definition subject, never an
        # exact product inferred from incomplete dimensions. Separate subjects
        # remain separate even when their currently known attributes coincide.
        config_id = identity_key("watches", "definition-subject", source, report.configuration_key)
    else:
        config_id = identity_key(
            "watches",
            "unresolved-selection",
            source,
            report.merchant_key or "",
            report.product_id or fallback_id,
            report.variation_id or "unresolved",
        )
    configuration = Configuration(id=config_id, **identity.model_dump())
    selection = resolve_fields(
        report,
        IDENTITY_FIELDS,
        subject="selection",
        captured_at=captured_at,
        not_applicable_fields=("generation",),
    )
    if selection.values.get("product_kind") in {"accessory", "component"}:
        selection.state = "rejected"
        selection.issues.append(ResolutionIssue(field="product_kind", code="not_complete_watch"))
    for field, value in selection.values.items():
        expected = configuration.values.get(field)
        equal = (
            (Decimal(value) == Decimal(expected))
            if expected and field == "case_width_mm"
            else (expected is not None and value.strip().casefold() == expected.strip().casefold())
        )
        if expected is not None and not equal:
            selection.state = "rejected"
            selection.issues.append(
                ResolutionIssue(
                    field=field,
                    code="configuration_mismatch",
                    evidence_ids=[c.id for c in report.claims if c.field == field],
                )
            )
    if configuration.state != "supported":
        selection.issues.append(
            ResolutionIssue(field="configuration", code="configuration_not_supported")
        )
        if selection.state == "supported":
            selection.state = "unresolved"
    if not all((report.merchant_key, report.product_id, report.variation_id)):
        selection.issues.append(
            ResolutionIssue(field="variation_id", code="selected_variation_id_missing")
        )
        if selection.state == "supported":
            selection.state = "unresolved"
    price_binding = resolve_fields(
        report,
        ("item_price", "currency", "availability", "quantity", "destination"),
        subject="offer",
        captured_at=captured_at,
    )
    selection.evidence_ids.extend(price_binding.evidence_ids)
    selection.issues.extend(price_binding.issues)
    if price_binding.state != "supported" and selection.state == "supported":
        selection.state = price_binding.state
    binding = SelectionBinding(
        id=identity_key(
            "watches",
            source,
            report.merchant_key or "",
            report.product_id or fallback_id,
            report.variation_id or "unresolved",
            "binding",
        ),
        configuration_id=config_id,
        merchant_key=report.merchant_key,
        product_id=report.product_id,
        variation_id=report.variation_id,
        resolution=selection,
    )
    return configuration, binding


def configuration_preference_fit(
    preferences: WatchPreferences,
    configurations: list[Configuration],
) -> list[PreferenceFit]:
    from decimal import Decimal

    fits = lead_preference_fit(preferences)
    known: dict[str, str] = {}
    for field in ("case_width_mm", "dial"):
        values = [
            config.values.get(field)
            if config.state != "rejected" and config.values.get("product_kind") == "complete_watch"
            else None
            for config in configurations
        ]
        if values and all(value is not None for value in values) and len(set(values)) == 1:
            value = values[0]
            if value is not None:
                known[field] = value
    # Known individual manufacturer dimensions may support a preference even
    # when another mandatory dimension is missing. Conflicted fields are absent.
    for fit in fits:
        if fit.strength == "unset":
            continue
        if fit.field == "compact" and "case_width_mm" in known:
            width = Decimal(known["case_width_mm"])
            if preferences.compact_max_width_mm is not None:
                fit.state = "fits" if width <= preferences.compact_max_width_mm else "outside"
                fit.reason = (
                    f"Manufacturer-declared case width {width} mm: {fit.state} compact preference."
                )
        elif fit.field == "colourful" and "dial" in known:
            dial = known["dial"].casefold()
            fit.state = "fits" if dial in preferences.colourful_dials else "outside"
            fit.reason = f"Manufacturer-declared dial {dial}: {fit.state} colourful preference."
    return fits
