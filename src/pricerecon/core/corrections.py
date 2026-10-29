"""Project withdrawals without rewriting original evidence or historical facts."""

import sqlite3

from pricerecon.db.corrections import correction_binding_ids, is_withdrawn, read_corrections
from pricerecon.models.corrections import CorrectionHistory
from pricerecon.models.costs import CostEvidence, CostScenario
from pricerecon.models.discovery import DiscoveryCandidate
from pricerecon.models.qualification import FieldEvidence, Resolution, ResolutionIssue


def project_cost(connection: sqlite3.Connection, cost: CostScenario) -> CostScenario:
    if is_withdrawn(connection, "cost", cost.id, cost.revision):
        cost.withdrawn = True
        cost.historical_total, cost.total = cost.total, None
        cost.state = "unknown"
        cost.issues = list(dict.fromkeys([*cost.issues, "identity_correction_withdrawn"]))
    return cost


def project_candidate(connection: sqlite3.Connection, candidate: DiscoveryCandidate) -> None:
    candidate.corrections = [
        read_corrections(connection, candidate.id, row[0])
        for row in connection.execute(
            "SELECT DISTINCT configuration_id FROM discovery_corrections WHERE candidate_id=?",
            (candidate.id,),
        )
    ]
    withdrawn = Resolution(
        state="unresolved",
        issues=[
            ResolutionIssue(field="identity", code="identity_correction_requires_requalification")
        ],
    )
    disputed_bindings = {
        identity
        for correction in candidate.corrections
        if correction.state == "disputed"
        for identity in correction_binding_ids(connection, correction)
    }
    for configuration in candidate.configurations:
        if is_withdrawn(connection, "configuration", configuration.id, configuration.revision):
            configuration.state = (
                "conflicting"
                if any(
                    b.id in disputed_bindings and b.configuration_id == configuration.id
                    for b in candidate.bindings
                )
                else "unresolved"
            )
            configuration.issues.extend(withdrawn.issues)
    for binding in candidate.bindings:
        if is_withdrawn(connection, "binding", binding.id, binding.revision):
            binding.resolution = withdrawn.model_copy(deep=True)
    for offer in candidate.offers:
        if is_withdrawn(connection, "offer", offer.id, offer.revision):
            offer.qualification = withdrawn.model_copy(deep=True)
            offer.comparison = withdrawn.model_copy(deep=True)
            offer.comparison_cohort = None
        offer.cost_scenarios = [project_cost(connection, cost) for cost in offer.cost_scenarios]
    if any(
        is_withdrawn(connection, "configuration", c.id, c.revision)
        for c in candidate.configurations
    ):
        candidate.identity_state = (
            "conflicting"
            if any(c.state == "conflicting" for c in candidate.configurations)
            else "unresolved"
        )


def compatible_fresh_candidate(
    candidate: DiscoveryCandidate, correction: "CorrectionHistory"
) -> bool:
    """Check one scoped dependency path; intent never supplies merchant proof."""
    from pricerecon.categories.watches import configuration_matches_values

    if correction.state == "disputed" or not correction.lineage:
        return False
    boundary = correction.lineage[-1].recorded_at
    fields = {entry.field for entry in correction.lineage}
    if not candidate.configurations or not candidate.offers:
        return False
    for configuration in candidate.configurations:
        if configuration.state != "supported" or not configuration_matches_values(
            configuration.values, correction.values
        ):
            return False
    for binding in candidate.bindings:
        if binding.resolution.state != "supported":
            return False
    for offer in candidate.offers:
        if offer.qualification.state != "supported":
            return False
        # Reusing old corrected-field claims does not resolve a dispute, even
        # if their string values happen to equal the newly requested intent.
        for subject in ("configuration", "selection"):
            for field in fields:
                identity_claims = [
                    e for e in offer.evidence if e.subject == subject and e.field == field
                ]
                if not identity_claims or any(
                    e.observed_at is None or e.observed_at <= boundary for e in identity_claims
                ):
                    return False
        temporal = [
            e
            for e in offer.evidence
            if e.subject == "offer" and e.field in {"item_price", "availability"}
        ]
        costs = [cost for cost in offer.cost_scenarios if cost.kind == "public_no_coupon"]
        if not costs or not temporal:
            return False
        for cost in costs:
            if cost.state != "verified_at_observation":
                return False
            cost_claims = [
                *cost.context_evidence,
                *(e for part in cost.components for e in part.evidence),
                *(e for fx in cost.fx_quotes for e in fx.evidence),
            ]
            if not cost_claims:
                return False
            evidence: list[FieldEvidence | CostEvidence] = [*temporal, *cost_claims]
            for claim in evidence:
                if (
                    claim.observed_at is None
                    or claim.observed_at <= boundary
                    or claim.acquisition_capture_id != claim.capture_id
                ):
                    return False
    return True
