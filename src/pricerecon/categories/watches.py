"""Watch preferences are buyer definitions, never facts inferred from a lead title."""

from pricerecon.models.discovery import PreferenceFit, PreferenceInterpretation, WatchPreferences


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
