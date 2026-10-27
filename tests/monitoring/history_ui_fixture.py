"""Additional synthetic history for the existing guarded UI fixture."""

from .history_workflows import priced_report
from .workflows import listing


async def populate_history(harness):
    from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus
    from pricerecon.core.discovery import execute_discovery
    from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest
    from pricerecon.models.qualification import EvidenceSearchReport

    request = DiscoveryRequest(query="wristwatch", sources=[{"connector": "cex"}])
    admission = DiscoveryAdmission(
        mode="offline_verification",
        policy_reference="synthetic-history-no-cadence",
        permission_reference="original-test-data",
        activation_reference="offline-ui-harness",
    )
    for price in ("48.00", "58.00", "38.00"):
        harness.clock.advance()
        report = priced_report(harness, price, "fixture-1")
        harness.reports["cex"] = [report]
        harness.outcomes["cex"] = [
            listing(harness, "cex", "fixture-1", "Addiesdive AD2066 mint", price)
        ]
        await execute_discovery(request, admission=admission)
    harness.clock.advance()
    await execute_discovery(request, admission=admission)  # same underlying capture
    harness.clock.advance()
    harness.report_overrides["cex"] = EvidenceSearchReport(
        listings=harness.outcomes["cex"],
        evidence=[report],
        acquisition_state="cache_reuse",
        acquisition_reason="Synthetic cached fallback; original observation time retained",
        reused_capture_id=report.claims[0].capture_id,
    )
    await execute_discovery(request, admission=admission)
    harness.clock.advance()
    harness.report_overrides["cex"] = EvidenceSearchReport(
        listings=harness.outcomes["cex"],
        evidence=[priced_report(harness, "38.00", "fixture-1")],
        acquisition_state="partial",
        acquisition_reason="Synthetic partial page; coverage incomplete",
        completeness="partial",
    )
    await execute_discovery(request, admission=admission)
    del harness.report_overrides["cex"]
    harness.clock.advance()
    harness.outcomes["cex"] = RuntimeError("Synthetic source failure")
    await execute_discovery(request, admission=admission)
    harness.clock.advance()
    harness.outcomes["cex"] = ConnectorDegradedError(
        status=ConnectorStatus.rate_limited,
        message="Synthetic cap",
        connector_id="cex",
        detail={"capped": True},
    )
    await execute_discovery(request, admission=admission)
    harness.clock.advance()
    harness.outcomes["cex"] = []
    harness.reports["cex"] = []
    await execute_discovery(request, admission=admission)
    harness.clock.advance(hours=24)
