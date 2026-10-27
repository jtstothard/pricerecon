"""Ticket04 synthetic API/execution workflows; no legal or live-offer evidence."""

import asyncio
import sys

from .harness import MonitoringHarness
from .qualification_workflows import acquire, synthetic_report
from .workflows import get, listing


def cost_report(harness, listing_id="cost", *, quantity=1):
    from pricerecon.models.qualification import MerchantEvidenceReport

    report = synthetic_report(harness, listing_id)
    report.quantity = quantity
    for claim in report.claims:
        if claim.subject != "configuration":
            claim.context.quantity = quantity
        if claim.field == "quantity":
            claim.value = str(quantity)
    context = {
        "configuration_key": report.configuration_key,
        "merchant_key": report.merchant_key,
        "product_id": report.product_id,
        "variation_id": report.variation_id,
        "seller": "Synthetic merchant",
        "condition": "new",
        "purchase_mode": "buy_now",
        "quantity": quantity,
        "destination_country": "GB",
        "destination_nation": "England",
        "destination_region": "synthetic-region",
        "shipping_service": "synthetic-standard",
        "seller_establishment": "GB",
        "goods_location": "GB",
        "dispatch_country": "GB",
        "customs_origin": "synthetic-origin",
        "dispatch_route": "synthetic-domestic",
        "purchase_scope": "standalone",
        "basket_id": "synthetic-basket",
        "basket_members": [f"{listing_id}:{quantity}"],
        "consignment_id": "synthetic-consignment",
        "consignment_members": [f"{listing_id}:{quantity}"],
        "grouping_basis": "synthetic single seller quote",
        "payment_method": "synthetic-gbp-debit",
        "display_currency": "GBP",
        "charge_currency": "GBP",
        "funding_currency": "GBP",
    }

    def evidence(key):
        return {
            "id": f"synthetic:{listing_id}:{key}",
            "issuer": "Synthetic merchant",
            "issuer_kind": "seller",
            "extractor": "synthetic-cost-fixture-v1",
            "extractor_kind": "structured_data",
            "observed_at": harness.clock.now.isoformat(),
            "retrieved_at": harness.clock.now.isoformat(),
            "capture_id": f"synthetic:{listing_id}",
            "route": "offline_fixture",
            "pointer": f"https://synthetic.invalid/{listing_id}?variant={report.variation_id}",
            "locator": f"$.cost.{key}",
            "derived_from": [f"synthetic-original:{listing_id}:{key}"],
            "permission_reference": "original-synthetic-test-data",
            "retention": "synthetic",
            "context": context,
        }

    components = []
    for kind in (
        "item",
        "shipping",
        "merchant_tax",
        "merchant_fee",
        "import_tax",
        "duty",
        "carrier_fee",
        "payment_fee",
    ):
        component = {
            "kind": kind,
            "state": (
                "observed" if kind in {"item", "shipping", "merchant_tax"} else "not_applicable"
            ),
            "amount": {"item": "48.00", "shipping": "2.10", "merchant_tax": "8.00"}.get(kind),
            "currency": "GBP" if kind in {"item", "shipping", "merchant_tax"} else None,
            "basis": "per_unit" if kind == "item" else "scenario",
            "included_in": "item" if kind == "merchant_tax" else None,
            "payer": "buyer",
            "collector": (
                "synthetic merchant"
                if kind in {"item", "shipping", "merchant_tax", "merchant_fee"}
                else "synthetic third party"
            ),
            "reason": (
                "Synthetic quoted VAT already included in item"
                if kind == "merchant_tax"
                else "Synthetic exact-scenario quote or explicit inapplicability"
            ),
            "evidence": [evidence(kind)],
        }
        components.append(component)
    payload = report.model_dump(mode="json")
    payload["cost_scenarios"] = [
        {
            "key": "public",
            "kind": "public_no_coupon",
            "context": context,
            "context_evidence": [evidence("context")],
            "components": components,
        }
    ]
    return MerchantEvidenceReport.model_validate(payload)


async def read_capture(harness, client, reports):
    harness.reports["cex"] = reports
    harness.outcomes["cex"] = [
        listing(harness, "cex", r.source_listing_id, "Synthetic cost watch", "1.00")
        for r in reports
    ]
    await acquire(harness)
    feed = await get(client, "/api/discovery/watches")
    assert feed["collection_state"] == "staged"
    assert harness.deliveries == harness.blocked_edges == []
    return feed


async def included_vat():
    with MonitoringHarness() as harness:
        report = cost_report(harness)
        async with harness.session() as (client, _):
            feed = await read_capture(harness, client, [report])
            candidate = feed["candidates"][0]
            offer = candidate["offers"][0]
            cost = offer["cost_scenarios"][0]
            assert cost["state"] == "verified_at_observation"
            assert cost["total"] == {"amount": "50.10", "currency": "GBP"}
            assert cost["merchant_payable"] == {"GBP": "50.10"}
            assert cost["additional_liabilities"] == {}
            assert cost["known_subtotal"] == {"GBP": "50.10"}
            assert cost["offer_revision"] == offer["revision"]
            assert cost["binding_revision"] == offer["binding_revision"]
            assert candidate["public_delivered_total"]["amount"] == "50.10"
            assert candidate["public_delivered_total"]["scenario_id"] == cost["id"]
            assert candidate["usual_price"]["amount"] is candidate["savings"] is None
            assert candidate["alert_eligible"] is False
            assert offer["comparison"]["state"] == "unresolved"
            assert "freshness_unvalidated" in {i["code"] for i in offer["comparison"]["issues"]}
            assert "uk_cost_unknown" not in {i["code"] for i in offer["comparison"]["issues"]}


async def persistence_before():
    import json
    from pathlib import Path

    with MonitoringHarness(storage_root=Path(sys.argv[2])) as harness:
        async with harness.session() as (client, _):
            first = (await read_capture(harness, client, [cost_report(harness)]))["candidates"][0][
                "offers"
            ][0]
            history = await get(client, f"/api/discovery/offers/{first['id']}/costs")
            assert history["scenarios"] == first["cost_scenarios"]
            harness.root.joinpath("first-cost.json").write_text(json.dumps(history))
            harness.root.joinpath("offer-id").write_text(first["id"])


async def persistence_after():
    import json
    from pathlib import Path

    with MonitoringHarness(storage_root=Path(sys.argv[2])) as harness:
        async with harness.session() as (client, _):
            offer_id = harness.root.joinpath("offer-id").read_text()
            original = json.loads(harness.root.joinpath("first-cost.json").read_text())
            assert await get(client, f"/api/discovery/offers/{offer_id}/costs") == original
            report = cost_report(harness, quantity=2)
            scenario = report.cost_scenarios[0]
            shipping = next(c for c in scenario.components if c.kind == "shipping")
            shipping.amount = __import__("decimal").Decimal("4.20")
            tax = next(c for c in scenario.components if c.kind == "merchant_tax")
            tax.amount = __import__("decimal").Decimal("16.00")
            feed = await read_capture(harness, client, [report])
            offer = feed["candidates"][0]["offers"][0]
            cost = offer["cost_scenarios"][0]
            assert cost["total"] == {"amount": "100.20", "currency": "GBP"}
            assert cost["offer_revision"] == offer["revision"] == 2
            assert cost["binding_revision"] == offer["binding_revision"] == 2
            assert cost["configuration_revision"] == 2
            assert cost["id"] != original["scenarios"][0]["id"]
            harness.clock.advance()
            feed = await read_capture(harness, client, [report])
            latest = feed["candidates"][0]["offers"][0]["cost_scenarios"][0]
            assert latest["id"] == cost["id"] and latest["revision"] == 2
            assert latest["offer_revision"] == latest["binding_revision"] == 3
            history = await get(client, f"/api/discovery/offers/{offer_id}/costs")
            assert len(history["scenarios"]) == 3
            assert history["scenarios"][0] == original["scenarios"][0]
            assert history["scenarios"][1] == cost
            assert history["scenarios"][2] == latest
            assert history["freshness"] == "unvalidated"
            assert (
                await client.post(f"/api/discovery/offers/{offer_id}/costs", json={})
            ).status_code == 405
            assert (await get(client, "/api/discovery/offers/unknown/costs"))["scenarios"] == []


async def missing_conflicting():
    from decimal import Decimal

    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            cases = []
            for kind in (
                "shipping",
                "merchant_tax",
                "merchant_fee",
                "import_tax",
                "duty",
                "carrier_fee",
                "payment_fee",
            ):
                report = cost_report(harness, f"unknown-{kind}")
                part = next(c for c in report.cost_scenarios[0].components if c.kind == kind)
                part.state = "unknown"
                part.amount = part.currency = None
                cases.append(report)
            missing_currency = cost_report(harness, "missing-currency")
            missing_currency.cost_scenarios[0].components[0].currency = None
            cases.append(missing_currency)
            international = cost_report(harness, "gbp-display")
            international.destination = "US"
            for claim in international.claims:
                if claim.subject != "configuration":
                    claim.context.destination = "US"
                if claim.field == "destination":
                    claim.value = "US"
            context = international.cost_scenarios[0].context
            context.destination_country = "US"
            context.destination_nation = "synthetic-US"
            context.dispatch_country = "CN"
            cases.append(international)
            conflict = cost_report(harness, "conflict")
            other = conflict.model_copy(deep=True)
            next(c for c in other.cost_scenarios[0].components if c.kind == "shipping").amount = (
                Decimal("9.10")
            )
            cases.extend([conflict, other])
            feed = await read_capture(harness, client, cases)
            by_id = {c["source_listing_id"]: c for c in feed["candidates"]}
            for candidate in by_id.values():
                offer = candidate["offers"][0]
                assert candidate["configuration"]["state"] == "supported"
                assert offer["qualification"]["state"] == "supported"
                assert offer["cost_scenarios"][0]["state"] == "unknown", candidate
                assert offer["cost_scenarios"][0]["total"] is None
                assert candidate["public_delivered_total"]["amount"] is None
                assert candidate["alert_eligible"] is False
            assert by_id["unknown-shipping"]["offers"][0]["cost_scenarios"][0][
                "known_subtotal"
            ] == {"GBP": "48.00"}
            assert (
                "uk_destination_unproven"
                in by_id["gbp-display"]["offers"][0]["cost_scenarios"][0]["issues"]
            )
            cost = by_id["conflict"]["offers"][0]["cost_scenarios"][0]
            assert "shipping:conflicting_components" in cost["issues"]
            assert {c["amount"] for c in cost["components"] if c["kind"] == "shipping"} == {
                "2.10",
                "9.10",
            }


def bind_cost_context(report):
    for scenario in report.cost_scenarios:
        for evidence in scenario.context_evidence + [
            e for c in scenario.components for e in c.evidence
        ]:
            evidence.context = scenario.context.model_copy(deep=True)


async def liabilities_fx():
    from decimal import Decimal

    with MonitoringHarness() as harness:
        from pricerecon.models.qualification import MerchantEvidenceReport

        report = cost_report(harness, "import")
        scenario = report.cost_scenarios[0]
        scenario.context.dispatch_country = scenario.context.goods_location = "CN"
        scenario.context.dispatch_route = "synthetic recipient-paid import"
        for kind, value in (
            ("import_tax", "11.00"),
            ("duty", "3.00"),
            ("carrier_fee", "4.00"),
            ("payment_fee", "1.00"),
        ):
            part = next(c for c in scenario.components if c.kind == kind)
            part.state, part.amount, part.currency = "observed", Decimal(value), "GBP"
        bind_cost_context(report)
        foreign = cost_report(harness, "foreign")
        foreign.currency = "USD"
        for claim in foreign.claims:
            if claim.subject != "configuration":
                claim.context.currency = "USD"
            if claim.field == "currency":
                claim.value = "USD"
            if claim.field == "item_price":
                claim.value = "48.10"
        cost = foreign.cost_scenarios[0]
        cost.context.charge_currency = "USD"
        cost.context.display_currency = cost.context.funding_currency = "GBP"
        cost.components[0].amount = Decimal("48.10")
        cost.components[1].amount = Decimal("2.20")
        for part in cost.components:
            if part.amount is not None:
                part.currency = "USD"
        carrier = next(c for c in cost.components if c.kind == "carrier_fee")
        carrier.state, carrier.amount, carrier.currency = "observed", Decimal("3.05"), "GBP"
        bind_cost_context(foreign)
        payload = foreign.model_dump(mode="json")
        evidence = payload["cost_scenarios"][0]["context_evidence"]
        quote = {
            "purpose": "buyer_payment",
            "from_currency": "USD",
            "to_currency": "GBP",
            "rate": "0.8",
            "direction": "target_per_source",
            "converter": "synthetic payment provider",
            "spread_included": True,
            "quantum": "0.01",
            "rounding": "ROUND_HALF_UP",
            "state": "observed",
            "assumptions": [],
            "evidence": evidence,
        }
        customs = {**quote, "purpose": "customs_valuation", "rate": "0.7"}
        payload["cost_scenarios"][0]["fx_quotes"] = [quote, customs]
        foreign = MerchantEvidenceReport.model_validate(payload)
        async with harness.session() as (client, _):
            feed = await read_capture(harness, client, [report, foreign])
            by_id = {c["source_listing_id"]: c for c in feed["candidates"]}
            landed = by_id["import"]["offers"][0]["cost_scenarios"][0]
            assert landed["merchant_payable"] == {"GBP": "50.10"}
            assert landed["additional_liabilities"] == {"GBP": "19.00"}
            assert landed["total"] == {"amount": "69.10", "currency": "GBP"}
            fx = by_id["foreign"]["offers"][0]["cost_scenarios"][0]
            assert fx["state"] == "verified_at_observation", fx["issues"]
            assert fx["known_subtotal"] == {"USD": "50.30", "GBP": "3.05"}
            assert fx["total"] == {"amount": "43.29", "currency": "GBP"}
            foreign.cost_scenarios[0].fx_quotes = [foreign.cost_scenarios[0].fx_quotes[1]]
            feed = await read_capture(harness, client, [foreign])
            fx = feed["candidates"][0]["offers"][0]["cost_scenarios"][0]
            assert fx["state"] == "unknown" and fx["total"] is None
            assert "payment_fx_unknown:USD:GBP" in fx["issues"]


async def conditional_public():
    with MonitoringHarness() as harness:
        from pricerecon.models.qualification import MerchantEvidenceReport

        report = cost_report(harness, "eligibility")
        payload = report.model_dump(mode="json")
        public = payload["cost_scenarios"][0]
        for kind in ("personal", "payment", "cashback"):
            alternate = {
                **public,
                "key": kind,
                "kind": kind,
                "assumptions": [f"Synthetic {kind} eligibility remains conditional"],
                "benefits": [
                    {
                        "kind": kind,
                        "amount": "10.00",
                        "currency": "GBP",
                        "state": "conditional",
                        "reason": "Synthetic benefit is not a guaranteed reduction of payable cost",
                        "evidence": public["context_evidence"],
                    }
                ],
            }
            payload["cost_scenarios"].append(alternate)
        report = MerchantEvidenceReport.model_validate(payload)
        async with harness.session() as (client, _):
            await client.put(
                "/api/discovery/watches/preferences",
                json={"expected_revision": 0, "values": {"budget_gbp": "49.00"}},
            )
            candidate = (await read_capture(harness, client, [report]))["candidates"][0]
            costs = {c["kind"]: c for c in candidate["offers"][0]["cost_scenarios"]}
            assert set(costs) == {"public_no_coupon", "personal", "payment", "cashback"}
            assert candidate["public_delivered_total"]["amount"] == "50.10"
            assert costs["public_no_coupon"]["state"] == "verified_at_observation"
            for kind in ("personal", "payment", "cashback"):
                assert costs[kind]["state"] == "conditional"
                assert costs[kind]["assumptions"]
                assert costs[kind]["total"]["amount"] == "50.10"
                assert costs[kind]["benefits"][0]["amount"] == "10.00"
            budget = next(f for f in candidate["preference_fit"] if f["field"] == "budget")
            assert budget["state"] == "outside"
            assert "observation" in budget["reason"]
            assert candidate["advertised_item_price"] == "1.00"
            public_cost = report.cost_scenarios[0]
            public_cost.components[1].state = "conditional"
            public_cost.components[1].assumptions = [
                "Synthetic shipping quote subject to stated remote-region assumption"
            ]
            candidate = (await read_capture(harness, client, [report]))["candidates"][0]
            assert candidate["public_delivered_total"]["state"] == "conditional"
            assert candidate["public_delivered_total"]["amount"] == "50.10"
            assert "uk_cost_conditional" in {
                i["code"] for i in candidate["offers"][0]["comparison"]["issues"]
            }
            assert "uk_cost_unknown" not in {
                i["code"] for i in candidate["offers"][0]["comparison"]["issues"]
            }
            assert (
                next(f for f in candidate["preference_fit"] if f["field"] == "budget")["state"]
                == "unknown"
            )


async def context_changes():
    from decimal import Decimal

    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            original = cost_report(harness, "change")
            first = (await read_capture(harness, client, [original]))["candidates"][0]["offers"][0]
            for field, value in (
                ("quantity", 2),
                ("destination_nation", "Northern Ireland"),
                ("dispatch_country", "CN"),
                ("payment_method", "synthetic-other-card"),
                ("basket_members", ["change:1", "other-seller:1"]),
                ("consignment_members", ["change:1", "other-seller:1"]),
            ):
                stale = original.model_copy(deep=True)
                setattr(stale.cost_scenarios[0].context, field, value)
                candidate = (await read_capture(harness, client, [stale]))["candidates"][0]
                cost = candidate["offers"][0]["cost_scenarios"][0]
                assert cost["state"] == "unknown" and cost["total"] is None, field
                assert any("context_mismatch" in issue for issue in cost["issues"]), field
                assert candidate["bindings"][0]["resolution"]["state"] == "supported"
            changed = cost_report(harness, "change", quantity=3)
            changed.cost_scenarios[0].context.basket_members = ["change:3"]
            changed.cost_scenarios[0].context.consignment_members = ["change:3"]
            # Invented threshold treatment: amounts are synthetic quotes, not a rate engine.
            next(
                c for c in changed.cost_scenarios[0].components if c.kind == "import_tax"
            ).state = "unknown"
            bind_cost_context(changed)
            candidate = (await read_capture(harness, client, [changed]))["candidates"][0]
            cost = candidate["offers"][0]["cost_scenarios"][0]
            assert cost["known_subtotal"] == {"GBP": "146.10"}
            assert cost["total"] is None and "import_tax:unknown" in cost["issues"]
            selected = original.model_copy(deep=True)
            selected.variation_id = "other-selection"
            for claim in selected.claims:
                if claim.subject != "configuration":
                    claim.context.variation_id = "other-selection"
            candidate = (await read_capture(harness, client, [selected]))["candidates"][0]
            cost = candidate["offers"][0]["cost_scenarios"][0]
            assert cost["state"] == "unknown" and "offer_cost_context_mismatch" in cost["issues"]
            assert candidate["offers"][0]["id"] != first["id"]
            history = await get(client, f"/api/discovery/offers/{first['id']}/costs")
            assert history["scenarios"][0] == first["cost_scenarios"][0]
            # A component marked included cannot swallow the selected item price.
            invalid = original.model_copy(deep=True)
            invalid.cost_scenarios[0].components[0].included_in = "shipping"
            invalid.cost_scenarios[0].components[1].amount = Decimal("100.00")
            cost = (await read_capture(harness, client, [invalid]))["candidates"][0]["offers"][0][
                "cost_scenarios"
            ][0]
            assert cost["total"] is None
            assert "item:invalid_inclusion" in cost["issues"]


async def boundary_evidence():
    from decimal import Decimal

    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            free = cost_report(harness, "free")
            free.cost_scenarios[0].components[1].amount = Decimal("-0.00")
            candidate = (await read_capture(harness, client, [free]))["candidates"][0]
            assert candidate["public_delivered_total"]["amount"] == "48.00"
            assert candidate["offers"][0]["cost_scenarios"][0]["components"][1]["amount"] == "0.00"
            cases = []
            for name in (
                "missing-zero-proof",
                "unsafe",
                "no-time",
                "derived",
                "payer",
                "missing-context",
                "item-price",
                "tax-conflict",
                "fee-conflict",
                "currency-conflict",
            ):
                report = cost_report(harness, name)
                cost = report.cost_scenarios[0]
                shipping = cost.components[1]
                if name == "missing-zero-proof":
                    shipping.amount, shipping.evidence = Decimal("0.00"), []
                elif name == "unsafe":
                    shipping.evidence[0].pointer = (
                        "https://user:password@synthetic.invalid/quote?token=private"
                    )
                elif name == "no-time":
                    shipping.evidence[0].observed_at = None
                elif name == "derived":
                    shipping.evidence[0].extractor_kind = "ai"
                elif name == "payer":
                    shipping.payer = "seller"
                elif name == "missing-context":
                    cost.context.charge_currency = None
                elif name == "item-price":
                    cost.components[0].amount = Decimal("1.00")
                else:
                    kind = {
                        "tax-conflict": "merchant_tax",
                        "fee-conflict": "payment_fee",
                        "currency-conflict": "shipping",
                    }[name]
                    part = next(c for c in cost.components if c.kind == kind).model_copy(deep=True)
                    part.state, part.amount, part.currency = (
                        "observed",
                        Decimal("3.00"),
                        "USD" if name == "currency-conflict" else "GBP",
                    )
                    cost.components.append(part)
                cases.append(report)
            feed = await read_capture(harness, client, cases)
            by_id = {c["source_listing_id"]: c for c in feed["candidates"]}
            for name in [r.source_listing_id for r in cases]:
                cost = by_id[name]["offers"][0]["cost_scenarios"][0]
                assert cost["state"] == "unknown" and cost["total"] is None, (name, cost["issues"])
            unsafe = by_id["unsafe"]["offers"][0]["cost_scenarios"][0]
            assert unsafe["components"][1]["evidence"][0]["pointer"] is None
            assert "private" not in str(unsafe) and "password" not in str(unsafe)
            assert (await get(client, "/api/discovery/offers/%27%20OR%201%3D1--/costs"))[
                "scenarios"
            ] == []
            # Removal of an offer currency cannot be repaired by a GBP lead/cost display.
            no_currency = cost_report(harness, "no-currency")
            no_currency.currency = None
            no_currency.claims = [c for c in no_currency.claims if c.field != "currency"]
            candidate = (await read_capture(harness, client, [no_currency]))["candidates"][0]
            assert candidate["offers"][0]["currency"] is None
            assert candidate["offers"][0]["cost_scenarios"][0]["total"] is None
            assert harness.blocked_edges == harness.deliveries == []


async def invalid_acquisition():
    from decimal import Decimal

    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            for invalid in (
                0.1,
                Decimal("NaN"),
                Decimal("Infinity"),
                Decimal(-1),
                Decimal("1e10000"),
                "not-money",
            ):
                report = cost_report(harness)
                report.cost_scenarios[0].components[1].amount = invalid
                feed = await read_capture(harness, client, [report])
                assert feed["candidates"] == [], str(invalid)
                assert feed["captures"][0]["outcomes"][0]["state"] == "failed"
                assert feed["captures"][0]["outcomes"][0]["reason"] == "parse_error"
            from pricerecon.models.costs import FxQuote

            malformed_fx = cost_report(harness, "bad-quantum")
            scenario = malformed_fx.cost_scenarios[0]
            quote = FxQuote(
                purpose="buyer_payment",
                from_currency="GBP",
                to_currency="USD",
                rate="1.1",
                direction="target_per_source",
                converter="synthetic-provider",
                spread_included=True,
                quantum="0.01",
                rounding="ROUND_HALF_UP",
                state="observed",
                evidence=scenario.context_evidence,
            )
            quote.quantum = Decimal("1.00000000000000000000000000001")
            scenario.fx_quotes = [quote]
            feed = await read_capture(harness, client, [malformed_fx])
            assert feed["candidates"] == []
            assert feed["captures"][0]["outcomes"][0]["reason"] == "parse_error"
            from pricerecon.core.discovery import execute_discovery
            from pricerecon.models.discovery import DiscoveryRequest

            await execute_discovery(
                DiscoveryRequest(query="staged", sources=[{"connector": "cex"}])
            )
            feed = await get(client, "/api/discovery/watches")
            assert feed["captures"][0]["outcomes"][0]["state"] == "not_attempted"
            assert harness.deliveries == harness.blocked_edges == []


async def fx_conflicts():
    with MonitoringHarness() as harness:
        from pricerecon.models.qualification import MerchantEvidenceReport

        async with harness.session() as (client, _):
            for mode in ("missing", "conflicting", "spread", "expired", "conditional"):
                report = cost_report(harness, mode)
                report.cost_scenarios[0].components[1].currency = "USD"
                payload = report.model_dump(mode="json")
                scenario = payload["cost_scenarios"][0]
                quote = {
                    "purpose": "buyer_payment",
                    "from_currency": "USD",
                    "to_currency": "GBP",
                    "rate": "0.8",
                    "direction": "target_per_source",
                    "converter": "synthetic-provider",
                    "spread_included": True,
                    "quantum": "0.01",
                    "rounding": "ROUND_HALF_UP",
                    "state": "observed",
                    "assumptions": [],
                    "evidence": scenario["context_evidence"],
                }
                scenario["fx_quotes"] = [quote]
                if mode == "missing":
                    scenario["fx_quotes"] = []
                elif mode == "conflicting":
                    scenario["fx_quotes"].append({**quote, "rate": "0.9"})
                elif mode == "spread":
                    quote["spread_included"] = None
                elif mode == "expired":
                    quote["evidence"][0]["expires_at"] = "2026-10-26T00:00:00Z"
                else:
                    quote["state"] = "conditional"
                    quote["assumptions"] = [
                        "Synthetic estimated conversion, not a guaranteed debit"
                    ]
                report = MerchantEvidenceReport.model_validate(payload)
                candidate = (await read_capture(harness, client, [report]))["candidates"][0]
                cost = candidate["offers"][0]["cost_scenarios"][0]
                if mode == "conditional":
                    assert cost["state"] == "conditional"
                    assert cost["total"] == {"amount": "49.68", "currency": "GBP"}
                    assert cost["fx_quotes"][0]["assumptions"]
                else:
                    assert cost["state"] == "unknown" and cost["total"] is None, (
                        mode,
                        cost["issues"],
                    )
                    assert cost["known_subtotal"] == {"GBP": "48.00", "USD": "2.10"}


async def exact_precision():
    from decimal import Decimal

    with MonitoringHarness() as harness:
        report = cost_report(harness, "precision")
        report.cost_scenarios[0].components[1].amount = Decimal("1e100")
        async with harness.session() as (client, _):
            candidate = (await read_capture(harness, client, [report]))["candidates"][0]
            cost = candidate["offers"][0]["cost_scenarios"][0]
            assert cost["state"] == "verified_at_observation"
            assert Decimal(cost["total"]["amount"]) - Decimal("1e100") == Decimal("48.00")


async def basket_scope():
    with MonitoringHarness() as harness:
        from pricerecon.models.qualification import MerchantEvidenceReport

        report = cost_report(harness, "basket")
        payload = report.model_dump(mode="json")
        cost = payload["cost_scenarios"][0]
        cost["context"]["purchase_scope"] = "allocated_share"
        cost["context"]["basket_members"].append("synthetic-other-product:1")
        cost["context"]["consignment_members"].append("synthetic-other-product:1")
        cost["assumptions"] = [
            "Synthetic allocation requires purchasing the other basket item; not a standalone obtainable total"
        ]
        report = MerchantEvidenceReport.model_validate(payload)
        bind_cost_context(report)
        async with harness.session() as (client, _):
            candidate = (await read_capture(harness, client, [report]))["candidates"][0]
            scenario = candidate["offers"][0]["cost_scenarios"][0]
            assert scenario["state"] == "conditional" and scenario["total"]["amount"] == "50.10"
            assert candidate["public_delivered_total"]["amount"] is None
            assert "standalone" in candidate["public_delivered_total"]["reason"]
            report.cost_scenarios[0].context.purchase_scope = "whole_basket"
            report.cost_scenarios[0].assumptions = []
            payload = report.model_dump(mode="json")
            other = {
                **payload["cost_scenarios"][0]["components"][0],
                "kind": "basket_other_items",
                "basis": "scenario",
                "amount": "60.00",
                "included_in": None,
            }
            payload["cost_scenarios"][0]["components"].append(other)
            report = MerchantEvidenceReport.model_validate(payload)
            bind_cost_context(report)
            candidate = (await read_capture(harness, client, [report]))["candidates"][0]
            scenario = candidate["offers"][0]["cost_scenarios"][0]
            assert scenario["total"] == {"amount": "110.10", "currency": "GBP"}
            assert candidate["public_delivered_total"]["amount"] is None
            # A blanket free-shipping threshold claim cannot make the basket standalone.
            report.cost_scenarios[0].context.purchase_scope = "standalone"
            bind_cost_context(report)
            scenario = (await read_capture(harness, client, [report]))["candidates"][0]["offers"][
                0
            ]["cost_scenarios"][0]
            assert scenario["total"] is None and "standalone_basket_mismatch" in scenario["issues"]


async def repeated_cost_claims():
    with MonitoringHarness() as harness:
        report = cost_report(harness, "repeated-cost")
        original = report.cost_scenarios[0]
        report.cost_scenarios = []
        for index in range(16):
            scenario = original.model_copy(deep=True)
            for component in scenario.components:
                component.reason = f"Synthetic contradictory extraction {index}"
            report.cost_scenarios.append(scenario)
        async with harness.session() as (client, _):
            candidate = (await read_capture(harness, client, [report]))["candidates"][0]
            cost = candidate["offers"][0]["cost_scenarios"][0]
            assert cost["total"] is None and cost["state"] == "unknown"
            assert len(cost["components"]) == 128
            assert "shipping:conflicting_components" in cost["issues"]


if __name__ == "__main__":
    asyncio.run(globals()[sys.argv[1]]())
