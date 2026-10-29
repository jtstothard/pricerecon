"""Synthetic coupon receipts are original test data, never live coupon proof."""

import asyncio
import sys

from .cost_workflows import cost_report, read_capture
from .harness import MonitoringHarness
from .workflows import get


def advertised_report(harness, listing_id="coupon"):
    from pricerecon.models.qualification import MerchantEvidenceReport

    report = cost_report(harness, listing_id)
    payload = report.model_dump(mode="json")
    payload["coupons"] = [
        {
            "key": "synthetic-public",
            "label": "Synthetic TEN opportunity",
            "category": "public",
            "context": payload["cost_scenarios"][0]["context"],
            "opportunity_evidence": payload["cost_scenarios"][0]["context_evidence"],
        }
    ]
    return MerchantEvidenceReport.model_validate(payload)


async def advertised():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            feed = await read_capture(harness, client, [advertised_report(harness)])
            candidate = feed["candidates"][0]
            offer = candidate["offers"][0]
            assert candidate["public_delivered_total"]["amount"] == "50.10"
            coupon = offer["coupons"][0]
            assert coupon["state"] == "unverified_opportunity"
            assert coupon["resulting_cost"] is None
            assert "terms_missing" in coupon["issues"]
            history = await get(client, f"/api/discovery/offers/{offer['id']}/coupons")
            assert history["assessments"] == offer["coupons"]
            assert history["coverage"] == "supplied_acquisition_evidence_only"
            assert (
                await client.post(f"/api/discovery/offers/{offer['id']}/coupons", json={})
            ).status_code == 405


def applicable_report(harness, listing_id="coupon"):
    from pricerecon.models.qualification import MerchantEvidenceReport

    payload = advertised_report(harness, listing_id).model_dump(mode="json")
    coupon = payload["coupons"][0]
    evidence = {
        **coupon["opportunity_evidence"][0],
        "acquisition_capture_id": coupon["opportunity_evidence"][0]["capture_id"],
    }
    coupon["terms"] = {
        "literal": "Synthetic TEN: one selected watch, GBP 40 item minimum incl VAT, web, no account restriction; no other promotions; 12:00 inclusive to 13:00 exclusive UTC.",
        "codes": ["TEN"],
        "starts_at": "2026-10-27T12:00:00Z",
        "ends_at": "2026-10-27T13:00:00Z",
        "start_inclusive": True,
        "end_inclusive": False,
        "time_zone_literal": "UTC",
        "minimum_spend": "40.00",
        "minimum_currency": "GBP",
        "minimum_inclusive": True,
        "minimum_basis": "selected item including VAT; excludes shipping; before coupon",
        "min_quantity": 1,
        "max_quantity": 1,
        "channel": "web",
        "new_customer": "not_required",
        "membership": "not_required",
        "redemption": "public_no_activation",
        "compatibility": "supported",
        "combination_rule": "Only TEN; no other automatic discounts or codes present",
        "evidence": [
            {
                **evidence,
                "id": "synthetic:terms",
                "locator": "$.terms",
                "derived_from": ["synthetic-original:terms"],
            }
        ],
        "compatibility_evidence": [
            {
                **evidence,
                "id": "synthetic:stack",
                "locator": "$.terms.stack",
                "derived_from": ["synthetic-original:stack"],
            }
        ],
    }
    coupon["eligibility"] = {
        "channel": "web",
        "new_customer": "not_required",
        "membership": "not_required",
        "eligible_base": "48.00",
        "currency": "GBP",
        "terms_satisfied": True,
        "reason": "Synthetic exact selected line eligible, no exclusions or quota restrictions",
        "eligible_members": [f"{listing_id}:1"],
        "excluded_members": [],
        "evidence": [
            {
                **evidence,
                "id": "synthetic:eligibility",
                "locator": "$.eligibility",
                "derived_from": ["synthetic-original:eligibility"],
            }
        ],
    }
    return MerchantEvidenceReport.model_validate(payload)


async def applicable():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            feed = await read_capture(harness, client, [applicable_report(harness)])
            candidate = feed["candidates"][0]
            coupon = candidate["offers"][0]["coupons"][0]
            assert coupon["state"] == "applicable_not_reproduced"
            assert coupon["applicability"] == "supported"
            assert coupon["resulting_cost"] is None
            assert candidate["public_delivered_total"]["amount"] == "50.10"


def reproduced_report(harness, listing_id="coupon", revision=1):
    import hashlib

    from pricerecon.models.qualification import MerchantEvidenceReport

    report = applicable_report(harness, listing_id)
    payload = report.model_dump(mode="json")
    coupon = payload["coupons"][0]
    receipt = {
        **coupon["opportunity_evidence"][0],
        "id": "synthetic:application",
        "locator": "$.checkout.receipt",
        "derived_from": ["synthetic-original:checkout"],
        "acquisition_capture_id": coupon["opportunity_evidence"][0]["capture_id"],
    }
    after = payload["cost_scenarios"][0].copy()
    import copy

    after = copy.deepcopy(after)
    after["key"] = "coupon:TEN"
    after["context_evidence"] = [receipt]
    for part in after["components"]:
        part["evidence"] = [
            {
                **receipt,
                "id": f"synthetic:application:{part['kind']}",
                "locator": f"$.checkout.{part['kind']}",
            }
        ]
        if part["kind"] == "item":
            part["amount"] = "43.00"
        if part["kind"] == "merchant_tax":
            part["amount"] = "7.00"
    coupon["application"] = {
        "terms_fingerprint": hashlib.sha256(
            report.coupons[0].terms.model_dump_json().encode()
        ).hexdigest(),
        "expected_coupon_revision": revision,
        "expected_offer_revision": revision,
        "expected_binding_revision": revision,
        "expected_configuration_revision": revision,
        "expected_base_revision": revision,
        "base_key": "public",
        "before_total": "50.10",
        "expected_identity_policy": "watch-identity-v1",
        "expected_selection_policy": "watch-selection-v1",
        "expected_cost_policy": "exact-scenario-cost-v1",
        "expected_coupon_policy": "exact-coupon-v1",
        "applied_codes": ["TEN"],
        "other_promotions": [],
        "selected_item_price": "43.00",
        "quoted_total": "45.10",
        "currency": "GBP",
        "result": "applied",
        "evidence": [receipt],
        "payable": after,
        "selected_member": f"{listing_id}:1",
        "lines": [
            {
                "member": f"{listing_id}:1",
                "quantity": 1,
                "before_item_total": "48.00",
                "after_item_total": "43.00",
                "currency": "GBP",
                "eligible": True,
                "applied_codes": ["TEN"],
                "evidence": [receipt],
            }
        ],
    }
    # A separate synthetic source quote, retained independently of the proposed
    # application. Later mutations must not silently rewrite this observation.
    coupon["application"]["receipt"] = {
        **copy.deepcopy(receipt),
        "role": "checkout_application_receipt",
        "observation": {
            **{
                key: value
                for key, value in coupon["application"].items()
                if key.startswith("expected_") or key in {"terms_fingerprint", "base_key"}
            },
            "applied_codes": ["TEN"],
            "other_promotions": [],
            "result": "applied",
            "eligibility": copy.deepcopy(coupon["eligibility"]),
            "selected_member": f"{listing_id}:1",
            "selected_item_price": "43.00",
            "before_total": "50.10",
            "quoted_total": "45.10",
            "currency": "GBP",
            "before": copy.deepcopy(payload["cost_scenarios"][0]),
            "after": copy.deepcopy(after),
            "lines": copy.deepcopy(coupon["application"]["lines"]),
        },
    }
    return MerchantEvidenceReport.model_validate(payload)


async def reproduced():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            report = reproduced_report(harness)
            report.coupons.append(report.coupons[0].model_copy(deep=True))
            feed = await read_capture(harness, client, [report])
            candidate = feed["candidates"][0]
            offer = candidate["offers"][0]
            assert len(offer["coupons"]) == 1
            coupon = offer["coupons"][0]
            assert coupon["state"] == "reproduced_at_observation", coupon
            result = coupon["resulting_cost"]
            assert result["kind"] == "public_coupon"
            assert result["total"] == {"amount": "45.10", "currency": "GBP"}
            assert result["merchant_payable"] == {"GBP": "45.10"}
            assert result["known_subtotal"] == {"GBP": "45.10"}
            assert result["offer_revision"] == offer["revision"] == 1
            assert candidate["public_delivered_total"]["amount"] == "50.10"
            assert candidate["alert_eligible"] is False and candidate["savings"] is None
            assert len(offer["cost_scenarios"]) == 1
            assert (await get(client, f"/api/discovery/offers/{offer['id']}/coupons"))[
                "assessments"
            ] == [coupon]


async def eligibility_boundaries():
    from datetime import timedelta

    with MonitoringHarness() as harness:
        cases = [
            ("at-start", {}, "applicable_not_reproduced", None),
            ("exclusive-start", {"start_inclusive": False}, "rejected", "not_started"),
            (
                "before-start",
                {"starts_at": harness.clock.now + timedelta(seconds=1)},
                "rejected",
                "not_started",
            ),
            ("at-exclusive-end", {"ends_at": harness.clock.now}, "rejected", "expired"),
            (
                "at-inclusive-end",
                {"ends_at": harness.clock.now, "end_inclusive": True},
                "applicable_not_reproduced",
                None,
            ),
            (
                "after-inclusive-end",
                {
                    "ends_at": harness.clock.now - timedelta(seconds=1),
                    "starts_at": harness.clock.now - timedelta(hours=1),
                    "end_inclusive": True,
                },
                "rejected",
                "expired",
            ),
            (
                "timezone-unknown",
                {"time_zone_literal": None},
                "unverified_opportunity",
                "validity_unknown",
            ),
            ("minimum-inclusive", {"minimum_spend": "48.00"}, "applicable_not_reproduced", None),
            (
                "minimum-exclusive",
                {"minimum_spend": "48.00", "minimum_inclusive": False},
                "rejected",
                "minimum_spend_not_met",
            ),
            ("minimum-high", {"minimum_spend": "49.00"}, "rejected", "minimum_spend_not_met"),
            (
                "minimum-currency",
                {"minimum_currency": "USD"},
                "unverified_opportunity",
                "minimum_currency_mismatch",
            ),
            (
                "quantity-min",
                {"min_quantity": 2, "max_quantity": 3},
                "rejected",
                "quantity_ineligible",
            ),
            ("stack-forbidden", {"compatibility": "forbidden"}, "rejected", "stack_forbidden"),
            (
                "stack-silent",
                {"compatibility": "unknown"},
                "unverified_opportunity",
                "stack_unknown",
            ),
            (
                "stack-conditional",
                {"compatibility": "conditional"},
                "unverified_opportunity",
                "stack_conditional",
            ),
            (
                "stack-no-proof",
                {"compatibility_evidence": []},
                "unverified_opportunity",
                "compatibility:missing_evidence",
            ),
            (
                "app-required",
                {"channel": "app"},
                "unverified_opportunity",
                "channel_ineligible_or_unknown",
            ),
            (
                "new-customer",
                {"new_customer": "required"},
                "conditional_eligibility",
                "new_customer_ineligible_or_unknown",
            ),
            (
                "membership",
                {"membership": "required"},
                "conditional_eligibility",
                "membership_ineligible_or_unknown",
            ),
            (
                "redemption",
                {"redemption": "conditional"},
                "unverified_opportunity",
                "redemption_conditional_or_unknown",
            ),
        ]
        reports = []
        for name, changes, _, _ in cases:
            report = applicable_report(harness, name)
            report.coupons[0].terms = report.coupons[0].terms.model_copy(update=changes)
            reports.append(report)
        for category in ("personal", "payment", "cashback"):
            report = applicable_report(harness, category)
            report.coupons[0].category = category
            reports.append(report)
        async with harness.session() as (client, _):
            feed = await read_capture(harness, client, reports)
            by_id = {c["source_listing_id"]: c for c in feed["candidates"]}
            for name, _, state, issue in cases:
                candidate = by_id[name]
                coupon = candidate["offers"][0]["coupons"][0]
                assert coupon["state"] == state, (name, coupon)
                assert coupon["resulting_cost"] is None
                if issue:
                    assert issue in coupon["issues"], (name, coupon)
                assert candidate["public_delivered_total"]["amount"] == "50.10"
            for category in ("personal", "payment", "cashback"):
                coupon = by_id[category]["offers"][0]["coupons"][0]
                assert coupon["state"] == "conditional_eligibility"
                assert coupon["category"] == category and coupon["resulting_cost"] is None


async def proof_boundaries():
    from decimal import Decimal

    with MonitoringHarness() as harness:
        reports, expected = [], {}

        def case(name, issue):
            report = reproduced_report(harness, name)
            # Each report has the same exact watch configuration; acquisition
            # appends its shared configuration revision in report order.
            report.coupons[0].application.expected_configuration_revision = len(reports) + 1
            reports.append(report)
            expected[name] = issue
            return report.coupons[0]

        case("terms-changed", "application_lineage_changed").terms.literal = "Changed exact terms"
        case("stale-offer", "application_lineage_changed").application.expected_offer_revision = 2
        case(
            "stale-binding", "application_lineage_changed"
        ).application.expected_binding_revision = 2
        case(
            "stale-config", "application_lineage_changed"
        ).application.expected_configuration_revision = 999
        case("stale-coupon", "application_lineage_changed").application.expected_coupon_revision = 2
        case(
            "stale-base", "no_coupon_base_changed_or_unverified"
        ).application.expected_base_revision = 2
        case("before-total", "no_coupon_base_changed_or_unverified").application.before_total = (
            Decimal("49.00")
        )
        case("bare-discount", "basket_item_allocation_mismatch").application.payable.components = []
        case("wrong-total", "quoted_payable_does_not_reconcile").application.quoted_total = Decimal(
            "40.10"
        )
        case(
            "shipping-changed", "quoted_payable_does_not_reconcile"
        ).application.payable.components[1].amount = Decimal("4.20")
        case("missing-shipping", "reproduced_payable_unverified").application.payable.components[
            1
        ].state = "unknown"
        case("extra-code", "whole_stack_not_proven").application.other_promotions = ["AUTOMATIC"]
        case("different-codes", "whole_stack_not_proven").application.applied_codes = [
            "TEN",
            "TWENTY",
        ]
        case("rejected", "application_rejected").application.result = "rejected"
        case(
            "quantity-changed", "application_context_or_benefit_mismatch"
        ).application.payable.context.quantity = 2
        case(
            "basket-changed", "application_context_or_benefit_mismatch"
        ).application.payable.context.basket_members = ["other:1"]
        case(
            "destination-changed", "application_context_or_benefit_mismatch"
        ).application.payable.context.destination_region = "other-region"
        case(
            "selection-changed", "application_context_or_benefit_mismatch"
        ).application.payable.context.variation_id = "other-sku"
        coupon = case("terms-as-receipt", "advertisement_is_not_application_receipt")
        coupon.application.evidence = coupon.terms.evidence
        coupon = case("old-component", "payable_not_bound_to_application_receipt")
        coupon.application.payable.components[0].evidence = coupon.opportunity_evidence
        coupon = case("unsafe-link", "application:invalid_evidence_pointer")
        coupon.application.evidence[0].pointer = "https://user:secret@synthetic.invalid/"
        coupon = case("personal-proof", "separate_conditional_benefit")
        coupon.category = "personal"
        coupon = case("unresolved-identity", "exact_offer_not_supported")
        reports[-1].claims = []
        async with harness.session() as (client, _):
            feed = await read_capture(harness, client, reports)
            for candidate in feed["candidates"]:
                coupon = candidate["offers"][0]["coupons"][0]
                assert coupon["resulting_cost"] is None, (candidate["source_listing_id"], coupon)
                assert expected[candidate["source_listing_id"]] in coupon["issues"], (
                    candidate["source_listing_id"],
                    coupon,
                )


async def persistence_before():
    import json
    from pathlib import Path

    with MonitoringHarness(storage_root=Path(sys.argv[2])) as harness:
        async with harness.session() as (client, _):
            feed = await read_capture(harness, client, [reproduced_report(harness)])
            offer = feed["candidates"][0]["offers"][0]
            original = await get(client, f"/api/discovery/offers/{offer['id']}/coupons")
            assert original["assessments"][0]["state"] == "reproduced_at_observation"
            harness.root.joinpath("coupon-original.json").write_text(json.dumps(original))
            harness.root.joinpath("coupon-offer-id").write_text(offer["id"])


async def persistence_after():
    import json
    from pathlib import Path

    with MonitoringHarness(storage_root=Path(sys.argv[2])) as harness:
        async with harness.session() as (client, _):
            offer_id = harness.root.joinpath("coupon-offer-id").read_text()
            original = json.loads(harness.root.joinpath("coupon-original.json").read_text())
            assert await get(client, f"/api/discovery/offers/{offer_id}/coupons") == original
            report = reproduced_report(harness)
            report.coupons[0].terms.literal = "Synthetic changed terms; old receipt retained"
            feed = await read_capture(harness, client, [report])
            coupon = feed["candidates"][0]["offers"][0]["coupons"][0]
            assert coupon["state"] == "invalidated" and coupon["resulting_cost"] is None
            assert "application_lineage_changed" in coupon["issues"]
            history = await get(client, f"/api/discovery/offers/{offer_id}/coupons")
            assert len(history["assessments"]) == 2
            retired = history["assessments"][0]
            assert retired["lineage"] == "superseded"
            assert retired["state"] == "invalidated" and retired["resulting_cost"] is None
            assert retired["historical_resulting_cost"]["total"] == {
                "amount": "45.10",
                "currency": "GBP",
            }
            assert retired["application"] == original["assessments"][0]["application"]
            # Freshly acquired evidence must explicitly bind the new revisions.
            harness.clock.advance(hours=0)
            feed = await read_capture(harness, client, [reproduced_report(harness, revision=3)])
            assert (
                feed["candidates"][0]["offers"][0]["coupons"][0]["state"]
                == "reproduced_at_observation"
            )
            # Removing the coupon in a later acquisition does not replay a prior
            # success; ordinary no-coupon costs remain usable.
            feed = await read_capture(harness, client, [cost_report(harness, "coupon")])
            candidate = feed["candidates"][0]
            assert candidate["offers"][0]["coupons"] == []
            assert candidate["public_delivered_total"]["amount"] == "50.10"
            history = await get(client, f"/api/discovery/offers/{offer_id}/coupons")
            assert all(
                c["lineage"] == "superseded" and c["resulting_cost"] is None
                for c in history["assessments"]
            )


async def allocation_policy():
    from decimal import Decimal

    with MonitoringHarness() as harness:
        reports, expected = [], {}
        for name, issue in (
            ("missing-lines", "basket_allocation_incomplete"),
            ("line-total", "basket_item_allocation_mismatch"),
            ("line-quantity", "basket_selected_quantity_mismatch"),
            ("identity-policy", "application_policy_changed"),
            ("cost-policy", "application_policy_changed"),
            ("duplicate-lines", "basket_allocation_incomplete"),
            ("unallocated-reduction", "line_eligibility_or_codes_mismatch"),
        ):
            report = reproduced_report(harness, name)
            coupon = report.coupons[0]
            coupon.application.expected_configuration_revision = len(reports) + 1
            if name == "missing-lines":
                coupon.application.lines = []
            elif name == "line-total":
                coupon.application.lines[0].after_item_total = Decimal("42.00")
            elif name == "line-quantity":
                coupon.application.lines[0].quantity = 2
            elif name == "identity-policy":
                coupon.application.expected_identity_policy = "changed-policy"
            elif name == "cost-policy":
                coupon.application.expected_cost_policy = "changed-policy"
            elif name == "duplicate-lines":
                coupon.application.lines.append(coupon.application.lines[0].model_copy(deep=True))
            elif name == "unallocated-reduction":
                coupon.application.lines[0].applied_codes = []
            reports.append(report)
            expected[name] = issue
        async with harness.session() as (client, _):
            feed = await read_capture(harness, client, reports)
            for candidate in feed["candidates"]:
                coupon = candidate["offers"][0]["coupons"][0]
                assert coupon["resulting_cost"] is None
                assert expected[candidate["source_listing_id"]] in coupon["issues"], coupon[
                    "issues"
                ]


async def stack_and_basket():
    import copy
    import hashlib

    with MonitoringHarness() as harness:
        from pricerecon.models.qualification import MerchantEvidenceReport

        report = reproduced_report(harness, "stack")
        coupon = report.coupons[0]
        coupon.terms.codes = ["PRODUCT", "ORDER"]
        coupon.terms.literal = "Synthetic PRODUCT and ORDER whole-stack permission: selected watch, GBP 40 item minimum incl VAT; app; no account restrictions; 12:00 inclusive to 13:00 exclusive UTC. PRODUCT precedes ORDER on revised base. No other promotions."
        coupon.terms.channel = coupon.eligibility.channel = "app"
        coupon.terms.combination_rule = "Synthetic whole-set permission: PRODUCT then ORDER on revised base; no other promotions"
        coupon.application.applied_codes = ["PRODUCT", "ORDER"]
        coupon.application.lines[0].applied_codes = ["PRODUCT", "ORDER"]
        coupon.application.terms_fingerprint = hashlib.sha256(
            coupon.terms.model_dump_json().encode()
        ).hexdigest()
        observed = coupon.application.receipt.observation
        observed.applied_codes = ["PRODUCT", "ORDER"]
        observed.lines[0].applied_codes = ["PRODUCT", "ORDER"]
        observed.eligibility.channel = "app"
        observed.terms_fingerprint = coupon.application.terms_fingerprint
        async with harness.session() as (client, _):
            feed = await read_capture(harness, client, [report])
            assert (
                feed["candidates"][0]["offers"][0]["coupons"][0]["state"]
                == "reproduced_at_observation"
            )
            # Complete two-watch + strap commitment, never a standalone price.
            payload = cost_report(harness, "basket", quantity=2).model_dump(mode="json")
            payload["coupons"] = reproduced_report(harness, "basket").model_dump(mode="json")[
                "coupons"
            ]
            context = payload["cost_scenarios"][0]["context"]
            context.update(
                purchase_scope="whole_basket",
                basket_members=["basket:2", "strap:1"],
                consignment_members=["basket:2", "strap:1"],
            )

            def bind_context(value):
                if isinstance(value, dict):
                    if "destination_country" in value and "basket_members" in value:
                        value.update(copy.deepcopy(context))
                    else:
                        for child in value.values():
                            bind_context(child)
                elif isinstance(value, list):
                    for child in value:
                        bind_context(child)

            bind_context(payload)
            base = payload["cost_scenarios"][0]
            other = copy.deepcopy(base["components"][1])
            other.update(kind="basket_other_items", amount="10.00")
            base["components"].append(other)
            coupon = payload["coupons"][0]
            coupon["terms"]["max_quantity"] = 2
            coupon["terms"][
                "literal"
            ] = "Synthetic TEN: two selected watches, strap excluded; GBP 40 item minimum incl VAT; web; no account restrictions; no other promotions; 12:00 inclusive to 13:00 exclusive UTC."
            coupon["eligibility"].update(
                eligible_base="96.00", eligible_members=["basket:2"], excluded_members=["strap:1"]
            )
            application = coupon["application"]
            application.update(
                before_total="108.10",
                quoted_total="98.10",
                selected_member="basket:2",
                expected_configuration_revision=2,
            )
            application["lines"][0].update(
                member="basket:2", quantity=2, before_item_total="96.00", after_item_total="86.00"
            )
            application["lines"].append(
                {
                    **copy.deepcopy(application["lines"][0]),
                    "member": "strap:1",
                    "quantity": 1,
                    "before_item_total": "10.00",
                    "after_item_total": "10.00",
                    "eligible": False,
                    "applied_codes": [],
                }
            )
            other = copy.deepcopy(application["payable"]["components"][1])
            other.update(kind="basket_other_items", amount="10.00")
            application["payable"]["components"].append(other)
            report = MerchantEvidenceReport.model_validate(payload)
            report.coupons[0].application.terms_fingerprint = hashlib.sha256(
                report.coupons[0].terms.model_dump_json().encode()
            ).hexdigest()
            # This positive control supplies a new complete synthetic source
            # quote for the whole basket, separately from the proposed result.
            app = report.coupons[0].application
            observed = app.receipt.observation
            observed.expected_configuration_revision = 2
            observed.terms_fingerprint = app.terms_fingerprint
            observed.eligibility = report.coupons[0].eligibility.model_copy(deep=True)
            observed.before_total = "108.10"
            observed.quoted_total = "98.10"
            observed.selected_member = "basket:2"
            observed.before = report.cost_scenarios[0].model_copy(deep=True)
            observed.after = app.payable.model_copy(deep=True)
            observed.lines = [line.model_copy(deep=True) for line in app.lines]
            feed = await read_capture(harness, client, [report])
            candidate = next(c for c in feed["candidates"] if c["source_listing_id"] == "basket")
            coupon = candidate["offers"][0]["coupons"][0]
            assert coupon["state"] == "reproduced_at_observation", coupon["issues"]
            assert coupon["resulting_cost"]["total"] == {"amount": "98.10", "currency": "GBP"}
            assert coupon["resulting_cost"]["context"]["purchase_scope"] == "whole_basket"
            assert candidate["public_delivered_total"]["amount"] is None
            assert "whole-basket" in candidate["public_delivered_total"]["reason"]


async def selection_replacement():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            feed = await read_capture(harness, client, [reproduced_report(harness)])
            original_id = feed["candidates"][0]["offers"][0]["id"]
            report = cost_report(harness, "coupon")
            report.variation_id = "corrected-salmon-sku"
            for claim in report.claims:
                if claim.subject != "configuration":
                    claim.context.variation_id = report.variation_id
                if claim.field == "dial":
                    claim.value = "salmon"
            feed = await read_capture(harness, client, [report])
            candidate = feed["candidates"][0]
            assert candidate["offers"][0]["id"] != original_id
            assert candidate["offers"][0]["coupons"] == []
            # Old selected context is retained as incompatible cost evidence;
            # the mint payable must not become a corrected salmon price.
            assert candidate["public_delivered_total"]["amount"] is None
            history = await get(client, f"/api/discovery/offers/{original_id}/coupons")
            coupon = history["assessments"][0]
            assert coupon["state"] == "invalidated" and coupon["lineage"] == "superseded"
            assert coupon["resulting_cost"] is None
            assert coupon["historical_resulting_cost"]["total"]["amount"] == "45.10"


async def conflicts_and_staging():
    from datetime import datetime
    from decimal import Decimal

    with MonitoringHarness() as harness:
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryRequest

        report = reproduced_report(harness)
        conflict = report.coupons[0].model_copy(deep=True)
        conflict.application.quoted_total = Decimal("1.00")
        conflict.application.payable.components[0].evidence[0].pointer = "javascript:alert(1)"
        report.coupons.append(conflict)
        bypass = report.cost_scenarios[0].model_copy(deep=True)
        bypass.key, bypass.kind = "bypass", "public_coupon"
        report.cost_scenarios.append(bypass)
        async with harness.session() as (client, _):
            feed = await read_capture(harness, client, [report])
            candidate = feed["candidates"][0]
            assert candidate["public_delivered_total"]["amount"] == "50.10"
            offer = candidate["offers"][0]
            coupon = offer["coupons"][0]
            assert coupon["state"] == "invalidated" and coupon["resulting_cost"] is None
            assert "conflicting_coupon_inputs" in coupon["issues"]
            assert len(coupon["source_conflicts"]) == 1
            assert (
                coupon["source_conflicts"][0]["application"]["payable"]["components"][0][
                    "evidence"
                ][0]["pointer"]
                is None
            )
            direct = next(c for c in offer["cost_scenarios"] if c["kind"] == "public_coupon")
            assert direct["total"] is None and direct["state"] == "unknown"
            assert "coupon_requires_separate_reproduced_application" in direct["issues"]
            malformed = reproduced_report(harness)
            malformed.coupons[0].terms.starts_at = datetime(2026, 10, 27, 12)
            feed = await read_capture(harness, client, [malformed])
            assert feed["captures"][0]["outcomes"][0]["reason"] == "parse_error"
            searches = len(harness.searches)
            await execute_discovery(
                DiscoveryRequest(query="coupon", sources=[{"connector": "cex"}])
            )
            assert len(harness.searches) == searches
            feed = await get(client, "/api/discovery/watches")
            assert feed["collection_state"] == "staged"
            assert feed["captures"][0]["outcomes"][0]["state"] == "not_attempted"
            assert harness.deliveries == harness.blocked_edges == []


async def receipt_provenance():
    from pathlib import Path
    from tempfile import TemporaryDirectory

    from .coupon_merger_probe import probe

    with TemporaryDirectory(prefix="pricerecon-coupon-provenance-") as root:
        await probe(Path(root) / "receipt.json")


async def receipt_boundary_controls():
    import json
    from decimal import Decimal
    from pathlib import Path

    with MonitoringHarness() as harness:
        from pricerecon.models.coupons import CheckoutReceipt

        reports, expected, originals = [], {}, {}

        def case(name, issue):
            report = reproduced_report(harness, name)
            app = report.coupons[0].application
            app.expected_configuration_revision = len(reports) + 1
            app.receipt.observation.expected_configuration_revision = len(reports) + 1
            reports.append(report)
            expected[name] = issue
            return report.coupons[0]

        def replace_provenance(app, claim):
            app.evidence = [claim.model_copy(deep=True)]
            app.payable.context_evidence = [claim.model_copy(deep=True)]
            for part in app.payable.components:
                part.evidence = [claim.model_copy(deep=True)]
            for line in app.lines:
                line.evidence = [claim.model_copy(deep=True)]

        for role in ("compatibility", "eligibility"):
            coupon = case(f"relabeled-{role}", "non_application_evidence_is_not_receipt")
            claim = (
                coupon.terms.compatibility_evidence
                if role == "compatibility"
                else coupon.eligibility.evidence
            )[0]
            app = coupon.application
            # Giving the same claim a typed role AND matching structured values
            # must still fail: its retained provenance belongs to another role.
            app.receipt = CheckoutReceipt.model_validate(
                {
                    **claim.model_dump(),
                    "role": "checkout_application_receipt",
                    "observation": app.receipt.observation.model_dump(),
                }
            )
            replace_provenance(app, claim)

        coupon = case("renamed-compatibility", "non_application_evidence_is_not_receipt")
        coupon.application.receipt.id = "arbitrary-renamed-id"
        coupon.application.receipt.locator = "arbitrary-opaque-locator"
        coupon.application.receipt.derived_from = coupon.terms.compatibility_evidence[
            0
        ].derived_from
        coupon = case("reidentified-compatibility", "non_application_evidence_is_not_receipt")
        claim = coupon.terms.compatibility_evidence[0].model_copy(deep=True)
        claim.id = "new-id-for-same-source-field"
        claim.derived_from = ["new-root-for-same-source-field"]
        app = coupon.application
        app.receipt = CheckoutReceipt.model_validate(
            {
                **claim.model_dump(),
                "role": "checkout_application_receipt",
                "observation": app.receipt.observation.model_dump(),
            }
        )
        replace_provenance(app, claim)
        case(
            "receipt-origin-missing", "application_receipt_not_direct"
        ).application.receipt.acquisition_capture_id = None
        case(
            "receipt-origin-reused", "application_receipt_not_direct"
        ).application.receipt.acquisition_capture_id = "older-acquisition"
        case(
            "claim-origin-reused", "application_claims_not_bound_to_direct_receipt"
        ).application.payable.components[0].evidence[0].acquisition_capture_id = "older-acquisition"
        coupon = case("copied-receipt", "receipt:derived_claim_not_independent_support")
        coupon.application.receipt.input_claim_ids = [coupon.application.receipt.id]
        coupon.application.receipt.capture_id = "re-extracted-capture"
        coupon.application.receipt.derived_from = ["re-extracted-original"]
        coupon = case("generic-claims", "application_claims_not_bound_to_direct_receipt")
        replace_provenance(coupon.application, coupon.eligibility.evidence[0])
        case(
            "receipt-destination", "receipt:cost_context_mismatch"
        ).application.receipt.context.destination_region = "other-region"
        case(
            "receipt-basket", "receipt:cost_context_mismatch"
        ).application.receipt.context.basket_members = ["other:1"]
        case(
            "receipt-selection", "receipt:cost_context_mismatch"
        ).application.receipt.context.variation_id = "other-sku"
        case(
            "receipt-before", "receipt_before_scenario_mismatch"
        ).application.receipt.observation.before.components[0].amount = Decimal("49.00")
        case(
            "receipt-after", "receipt_after_scenario_mismatch"
        ).application.receipt.observation.after.components[1].amount = Decimal("4.20")
        case(
            "receipt-allocation", "receipt_allocations_mismatch"
        ).application.receipt.observation.lines[0].after_item_total = Decimal("42.00")
        case(
            "receipt-codes", "receipt_application_values_mismatch"
        ).application.receipt.observation.applied_codes = ["OTHER", "TEN"]
        case(
            "receipt-eligibility", "receipt_eligibility_mismatch"
        ).application.receipt.observation.eligibility.channel = "app"
        case(
            "receipt-lineage", "receipt_lineage_mismatch"
        ).application.receipt.observation.expected_offer_revision = 99
        case(
            "receipt-terms", "receipt_lineage_mismatch"
        ).application.receipt.observation.terms_fingerprint = ("0" * 64)
        case(
            "receipt-derived", "receipt:derived_claim_not_independent_support"
        ).application.receipt.extractor_kind = "ai"
        case("receipt-source", "application_receipt_not_direct").application.receipt.issuer_kind = (
            "carrier"
        )
        # Opaque evidence coordinates, with no magic checkout substrings, still
        # support a complete direct quote. Names cannot confer or remove role.
        coupon = case("opaque-positive", None)
        coupon.application.receipt.id = "opaque-17"
        coupon.application.receipt.locator = "opaque-23"
        for claim in coupon.application.evidence:
            claim.id, claim.locator = "opaque-19", "opaque-29"

        for report in reports:
            originals[report.source_listing_id] = report.coupons[0].application.model_dump(
                mode="json"
            )
        results = {}
        async with harness.session() as (client, _):
            feed = await read_capture(harness, client, reports)
            for candidate in feed["candidates"]:
                name = candidate["source_listing_id"]
                offer = candidate["offers"][0]
                coupon = offer["coupons"][0]
                assert coupon["application"] == originals[name], name
                assert coupon["applicability"] == "supported"
                if expected[name]:
                    assert coupon["resulting_cost"] is None, (name, coupon)
                    assert coupon["state"] == "applicable_not_reproduced"
                    assert expected[name] in coupon["issues"], (name, coupon["issues"])
                else:
                    assert coupon["state"] == "reproduced_at_observation", coupon["issues"]
                    assert coupon["resulting_cost"]["total"] == {
                        "amount": "45.10",
                        "currency": "GBP",
                    }
                    assert coupon["application"]["receipt"]["retention"] == "synthetic"
                history = await get(client, f"/api/discovery/offers/{offer['id']}/coupons")
                assert history["assessments"] == [coupon]
                assert candidate["public_delivered_total"]["amount"] == "50.10"
                assert candidate["savings"] is None and candidate["alert_eligible"] is False
                results[name] = {
                    "state": coupon["state"],
                    "issues": coupon["issues"],
                    "expected_issue": expected[name],
                    "payable": (
                        coupon["resulting_cost"]["total"] if coupon["resulting_cost"] else None
                    ),
                    "original_application_retained": coupon["application"] == originals[name],
                    "history_matches_feed": history["assessments"] == [coupon],
                    "no_coupon": candidate["public_delivered_total"]["amount"],
                }

            # Replay the old exact receipt, even while rebinding the proposed
            # application to the next acquisition's revisions. Its own lineage
            # must remain independently checked, and the rejected quote retained.
            replay = reproduced_report(harness, "opaque-positive", revision=2)
            replay.coupons[0].application.receipt = (
                reports[-1].coupons[0].application.receipt.model_copy(deep=True)
            )
            replay.coupons[0].application.expected_configuration_revision = len(reports) + 1
            feed = await read_capture(harness, client, [replay])
            candidate = next(
                c for c in feed["candidates"] if c["source_listing_id"] == "opaque-positive"
            )
            coupon = candidate["offers"][0]["coupons"][0]
            assert coupon["resulting_cost"] is None
            assert "receipt_lineage_mismatch" in coupon["issues"]
            assert coupon["application"]["receipt"] == originals["opaque-positive"]["receipt"]
            history = await get(client, f"/api/discovery/offers/{coupon['offer_id']}/coupons")
            assert (
                history["assessments"][0]["historical_resulting_cost"]["total"]["amount"] == "45.10"
            )
            assert history["assessments"][0]["resulting_cost"] is None
            assert history["assessments"][-1] == coupon
            assert harness.deliveries == harness.blocked_edges == []
            results["replay"] = {
                "state": coupon["state"],
                "issues": coupon["issues"],
                "payable": coupon["resulting_cost"],
                "original_receipt_retained": coupon["application"]["receipt"]
                == originals["opaque-positive"]["receipt"],
                "prior_payable_historical_only": True,
            }
            if len(sys.argv) > 2:
                Path(sys.argv[2]).write_text(
                    json.dumps(
                        {
                            "fixture": "original-synthetic-ticket09-receipt-controls",
                            "cases": results,
                            "collection_state": feed["collection_state"],
                            "temporary_storage": True,
                            "blocked_edges": harness.blocked_edges,
                            "notifications_sent": len(harness.deliveries),
                        },
                        indent=2,
                    )
                    + "\n"
                )


if __name__ == "__main__":
    asyncio.run(globals()[sys.argv[1]]())
