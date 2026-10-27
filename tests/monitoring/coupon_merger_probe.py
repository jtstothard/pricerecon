"""Guarded application probe for ticket09 receipt provenance and shipping.

Run in a fresh process. Also exercised by the collected coupon regression.
The original intentionally failing merger receipt is retained separately.
"""

import asyncio
import json
import sys
from decimal import Decimal
from pathlib import Path

from .cost_workflows import read_capture
from .coupon_workflows import reproduced_report
from .harness import MonitoringHarness
from .workflows import get


async def probe(output: Path) -> None:
    with MonitoringHarness() as harness:
        reports = []
        names = ("compatibility-as-receipt", "eligibility-as-receipt", "shipping-recalculated")
        for revision, name in enumerate(names, 1):
            report = reproduced_report(harness, name)
            coupon = report.coupons[0]
            application = coupon.application
            application.expected_configuration_revision = revision
            if name == "shipping-recalculated":
                # A new complete checkout quote charges GBP 4.20 shipping.
                # Reusing the base's GBP 2.10 would produce the wrong payable.
                application.payable.components[1].amount = Decimal("4.20")
                application.quoted_total = Decimal("47.20")
                # The typed direct source quote must independently observe the
                # changed shipping and bind this configuration revision.
                observed = application.receipt.observation
                observed.expected_configuration_revision = revision
                observed.after.components[1].amount = Decimal("4.20")
                observed.quoted_total = Decimal("47.20")
            else:
                claims = (
                    coupon.terms.compatibility_evidence
                    if name == "compatibility-as-receipt"
                    else coupon.eligibility.evidence
                )
                # Preserve the exact terms/applicability IDs, locators and roots.
                # There is no original checkout evidence left in these inputs.
                application.evidence = [claim.model_copy(deep=True) for claim in claims]
                application.payable.context_evidence = [
                    claim.model_copy(deep=True) for claim in claims
                ]
                for component in application.payable.components:
                    component.evidence = [claim.model_copy(deep=True) for claim in claims]
                for line in application.lines:
                    line.evidence = [claim.model_copy(deep=True) for claim in claims]
                # Remove the new typed receipt too: this remains the ENTIRE
                # provenance substitution, with no checkout source left behind.
                application.receipt = None
            reports.append(report)

        originals = {
            report.source_listing_id: report.coupons[0].model_dump(mode="json")
            for report in reports
        }

        async with harness.session() as (client, _):
            feed = await read_capture(harness, client, reports)
            cases = {}
            for candidate in feed["candidates"]:
                offer = candidate["offers"][0]
                coupon = offer["coupons"][0]
                history = await get(client, f"/api/discovery/offers/{offer['id']}/coupons")
                assert history["assessments"] == [coupon]
                original = originals[candidate["source_listing_id"]]
                for field in ("opportunity_evidence", "terms", "eligibility", "application"):
                    assert coupon[field] == original[field]
                result = coupon["resulting_cost"]
                cases[candidate["source_listing_id"]] = {
                    "state": coupon["state"],
                    "issues": coupon["issues"],
                    "payable": result["total"] if result else None,
                    "merchant_payable": result["merchant_payable"] if result else None,
                    "application_evidence": coupon["application"]["evidence"],
                    "public_no_coupon": candidate["public_delivered_total"]["amount"],
                    "history_matches_feed": True,
                    "alert_eligible": candidate["alert_eligible"],
                    "savings": candidate["savings"],
                }
            receipt = {
                "fixture": "ticket09-merger-receipt-provenance",
                "expected": "Compatibility/eligibility alone cannot support reproduced payable",
                "cases": cases,
                "collection_state": feed["collection_state"],
                "temporary_storage": True,
                "blocked_edges": harness.blocked_edges,
                "notifications_sent": len(harness.deliveries),
            }
            output.write_text(json.dumps(receipt, indent=2) + "\n")
            assert harness.deliveries == harness.blocked_edges == []
            assert all(case["public_no_coupon"] == "50.10" for case in cases.values())
            assert cases["shipping-recalculated"]["payable"] == {
                "amount": "47.20",
                "currency": "GBP",
            }
            assert cases["shipping-recalculated"]["merchant_payable"] == {"GBP": "47.20"}
            for name in names[:2]:
                assert cases[name]["state"] == "applicable_not_reproduced"
                assert "application_receipt_missing" in cases[name]["issues"]
            unsupported = [name for name in names[:2] if cases[name]["payable"] is not None]
            assert not unsupported, f"Non-application evidence accepted as receipt: {unsupported}"


if __name__ == "__main__":
    asyncio.run(probe(Path(sys.argv[1]).resolve()))
