"""Ticket03 API/execution workflows. All positive evidence is original synthetic data."""

import asyncio
import sys

from .harness import MonitoringHarness
from .workflows import get, listing


async def legacy_abstention():
    with MonitoringHarness() as harness:
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest

        lead = listing(harness, "cex", "legacy", "Casio MTP-B145D-2A2VEF", "1.00")
        lead.exact_variant_confirmed = True
        harness.outcomes["cex"] = [lead]
        async with harness.session() as (client, scheduler):
            await execute_discovery(
                DiscoveryRequest(query="watch", sources=[{"connector": "cex"}]),
                admission=DiscoveryAdmission(
                    mode="offline_verification",
                    policy_reference="synthetic",
                    permission_reference="synthetic",
                    activation_reference="isolated-harness",
                ),
            )
            candidate = (await get(client, "/api/discovery/watches"))["candidates"][0]
            assert candidate["configuration"]["state"] == "unresolved"
            assert candidate["bindings"][0]["resolution"]["state"] == "unresolved"
            assert candidate["offers"][0]["qualification"]["state"] == "unresolved"
            assert candidate["offers"][0]["seller"] is None
            assert candidate["offers"][0]["availability"] is None
            assert candidate["offers"][0]["authenticity"] == "unknown"
            assert candidate["public_delivered_total"]["amount"] is None
            assert scheduler.list_watches() == []
            assert harness.deliveries == harness.blocked_edges == []


def synthetic_report(
    harness,
    listing_id="addies",
    *,
    reference="AD2066",
    maker="Addiesdive",
    width="36",
    dial="mint",
    condition="new",
    mode="buy_now",
    variation="mint-vh31",
):
    """Invented assertions to test the resolver, never real merchant evidence."""
    from pricerecon.models.qualification import FieldEvidence, MerchantEvidenceReport

    identity = {
        "maker": maker,
        "reference": reference,
        "generation": "synthetic-revision-1",
        "movement": "VH31",
        "case_width_mm": width,
        "dial": dial,
        "strap": "steel",
        "date_display": "no_date",
        "product_kind": "complete_watch",
    }
    claims = []
    for subject, fields in (
        ("configuration", identity),
        ("selection", identity),
        (
            "offer",
            {
                "seller": "Synthetic merchant",
                "condition": condition,
                "quantity": "1",
                "availability": "in_stock",
                "purchase_mode": mode,
                "item_price": "48.00",
                "currency": "GBP",
                "destination": "GB",
            },
        ),
    ):
        for field, value in fields.items():
            selected = subject != "configuration"
            claims.append(
                FieldEvidence(
                    id=f"{listing_id}:{subject}:{field}",
                    subject=subject,
                    field=field,
                    value=value,
                    issuer="Synthetic merchant" if selected else "Synthetic manufacturer",
                    issuer_kind="seller" if selected else "manufacturer",
                    extractor="synthetic-fixture-v1",
                    extractor_kind="structured_data",
                    observed_at=harness.clock.now,
                    retrieved_at=harness.clock.now,
                    capture_id=f"synthetic:{listing_id}",
                    route="offline_fixture",
                    pointer=f"https://synthetic.invalid/{listing_id}?variant={variation}",
                    locator=f"$.{subject}.{field}",
                    context={
                        "configuration_key": f"synthetic:{listing_id}",
                        "scope": "selected_variation" if selected else "configuration",
                        "merchant_key": "synthetic.invalid" if selected else None,
                        "product_id": listing_id if selected else None,
                        "variation_id": variation if selected else None,
                        "destination": "GB" if selected else None,
                        "currency": "GBP" if selected else None,
                        "quantity": 1 if selected else None,
                    },
                    derived_from=[f"synthetic-original:{listing_id}:{subject}"],
                    permission_reference="original-synthetic-test-data",
                    retention="synthetic",
                )
            )
    return MerchantEvidenceReport(
        source_listing_id=listing_id,
        merchant_key="synthetic.invalid",
        product_id=listing_id,
        variation_id=variation,
        configuration_key=f"synthetic:{listing_id}",
        destination="GB",
        currency="GBP",
        quantity=1,
        claims=claims,
    )


async def acquire(harness):
    from pricerecon.core.discovery import execute_discovery
    from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest

    return await execute_discovery(
        DiscoveryRequest(query="wristwatch", sources=[{"connector": "cex"}]),
        admission=DiscoveryAdmission(
            mode="offline_verification",
            policy_reference="synthetic",
            permission_reference="original-synthetic-test-data",
            activation_reference="isolated-harness",
        ),
    )


async def named_cohort():
    with MonitoringHarness() as harness:
        reports = [
            synthetic_report(harness),
            synthetic_report(harness, "san", reference="SN0144", maker="San Martin", width="39"),
            synthetic_report(
                harness,
                "casio",
                reference="MTP-B145D-2A2VEF",
                maker="Casio",
                width="35",
                dial="blue",
            ),
        ]
        harness.reports["cex"] = reports
        harness.outcomes["cex"] = [
            listing(harness, "cex", "addies", "Addiesdive AD2066 mint"),
            listing(harness, "cex", "san", "San Martin SN0144"),
            listing(harness, "cex", "casio", "Casio MTP-B145D-2A2VEF"),
            listing(harness, "cex", "militado", "Militado ML05/ML05B 2035/VH31/Ronda 515"),
            listing(harness, "cex", "merkur", "Merkur Lightning salmon"),
        ]
        async with harness.session() as (client, scheduler):
            await client.put(
                "/api/discovery/watches/preferences",
                json={
                    "expected_revision": 0,
                    "values": {
                        "compact_max_width_mm": "37.5",
                        "colourful_dials": ["mint"],
                        "budget_gbp": "100",
                    },
                },
            )
            await acquire(harness)
            feed = await get(client, "/api/discovery/watches")
            candidates = {c["source_listing_id"]: c for c in feed["candidates"]}
            for key in ("addies", "san", "casio"):
                candidate = candidates[key]
                assert candidate["configuration"]["state"] == "supported", candidate
                assert candidate["bindings"][0]["resolution"]["state"] == "supported", candidate
                offer = candidate["offers"][0]
                assert offer["qualification"]["state"] == "supported", offer
                assert offer["comparison"]["state"] == "unresolved"
                assert {i["code"] for i in offer["comparison"]["issues"]} >= {
                    "uk_cost_unknown",
                    "freshness_unvalidated",
                }
                assert offer["seller"] == "Synthetic merchant"
                assert offer["item_price"] == "48.00"
                assert offer["comparison_cohort"].endswith(":new:buy_now")
                assert candidate["public_delivered_total"]["amount"] is None
                assert candidate["usual_price"]["amount"] is candidate["savings"] is None
                assert candidate["alert_eligible"] is False
                assert offer["evidence"][0]["retention"] == "synthetic"
            assert [f["state"] for f in candidates["addies"]["preference_fit"]] == [
                "fits",
                "fits",
                "unknown",
            ]
            assert [f["state"] for f in candidates["san"]["preference_fit"]] == [
                "outside",
                "fits",
                "unknown",
            ]
            assert [f["state"] for f in candidates["casio"]["preference_fit"]] == [
                "fits",
                "outside",
                "unknown",
            ]
            for key in ("militado", "merkur"):
                assert candidates[key]["identity_state"] == "unresolved"
                assert candidates[key]["configuration"]["values"] == {}
            assert scheduler.list_watches() == []
        async with harness.session() as (client, _):
            assert (await get(client, "/api/discovery/watches"))["candidates"] == feed["candidates"]
            assert harness.deliveries == harness.blocked_edges == []


async def traps():
    with MonitoringHarness() as harness:
        reports = []

        def variant(key, subject, field, value):
            report = synthetic_report(harness, key)
            for claim in report.claims:
                if claim.subject == subject and claim.field == field:
                    claim.value = value
            reports.append(report)
            return report

        variant("dial", "selection", "dial", "Space Gray")
        variant("size", "selection", "case_width_mm", "42")
        variant("movement", "selection", "movement", "2035")
        variant("strap", "selection", "strap", "FKM")
        variant("revision", "selection", "generation", "synthetic-revision-2")
        variant("suffix", "selection", "reference", "MTP-B145D-3AVEF")
        variant("date", "selection", "date_display", "date")
        variant("accessory", "selection", "product_kind", "accessory")
        conflict = synthetic_report(harness, "conflict")
        claim = next(
            c for c in conflict.claims if c.subject == "configuration" and c.field == "movement"
        )
        conflict.claims.append(
            claim.model_copy(update={"id": "different-manufacturer-claim", "value": "Ronda 515"})
        )
        reports.append(conflict)
        no_sku = synthetic_report(harness, "first-sku")
        no_sku.variation_id = None
        reports.append(no_sku)
        generic = synthetic_report(harness, "generic-stock")
        next(
            c for c in generic.claims if c.field == "availability"
        ).context.scope = "generic_listing"
        reports.append(generic)
        inferred = synthetic_report(harness, "ai")
        primary = next(
            c for c in inferred.claims if c.subject == "configuration" and c.field == "movement"
        )
        inferred.claims.remove(primary)
        for i in range(5):
            inferred.claims.append(
                primary.model_copy(
                    update={
                        "id": f"ai-copy-{i}",
                        "issuer_kind": "ai_inference",
                        "extractor_kind": "ai",
                        "input_claim_ids": [primary.id],
                        "derived_from": ["same-copied-page"],
                    }
                )
            )
        reports.append(inferred)
        copied = synthetic_report(harness, "copied")
        for c in copied.claims:
            if c.subject == "configuration":
                c.issuer_kind = "seller"
                c.derived_from = ["copied-catalogue-page"]
        reports.append(copied)
        reports.extend(
            [
                synthetic_report(harness, "new"),
                synthetic_report(harness, "used", condition="used"),
                synthetic_report(harness, "auction", mode="auction"),
            ]
        )
        for c in reports[-2].claims:
            if c.subject == "configuration":
                c.context.configuration_key = "synthetic:new"
        reports[-2].configuration_key = "synthetic:new"
        # Configuration values match despite separate seller offers.
        reports[-2].claims.append(
            reports[-2]
            .claims[-1]
            .model_copy(
                update={
                    "id": "used-visible",
                    "field": "visible_condition",
                    "value": "Seller reports light scratches",
                }
            )
        )
        harness.reports["cex"] = reports
        harness.outcomes["cex"] = [
            listing(harness, "cex", r.source_listing_id, r.source_listing_id) for r in reports
        ]
        async with harness.session() as (client, _):
            await acquire(harness)
            candidates = {
                c["source_listing_id"]: c
                for c in (await get(client, "/api/discovery/watches"))["candidates"]
            }
            for key in (
                "dial",
                "size",
                "movement",
                "strap",
                "revision",
                "suffix",
                "date",
                "accessory",
            ):
                assert candidates[key]["configuration"]["state"] == "supported"
                assert candidates[key]["bindings"][0]["resolution"]["state"] == "rejected", (
                    candidates[key]
                )
                assert candidates[key]["offers"][0]["qualification"]["state"] != "supported"
            assert candidates["conflict"]["configuration"]["state"] == "conflicting"
            assert "movement" not in candidates["conflict"]["configuration"]["values"]
            for key in ("ai", "copied"):
                assert candidates[key]["identity_state"] == "unresolved"
                assert candidates[key]["configuration"]["issues"]
            assert candidates["first-sku"]["bindings"][0]["resolution"]["state"] == "unresolved"
            assert candidates["generic-stock"]["offers"][0]["availability"] is None
            new, used, auction = [
                candidates[key]["offers"][0] for key in ("new", "used", "auction")
            ]
            assert len({o["comparison_cohort"] for o in (new, used, auction)}) == 3
            assert used["visible_condition"] == "Seller reports light scratches"
            assert used["authenticity"] == used["internal_health"] == "unknown"
            assert "not_fixed_purchase_price" in {
                i["code"] for i in auction["comparison"]["issues"]
            }
            assert all(c["public_delivered_total"]["amount"] is None for c in candidates.values())
            assert harness.blocked_edges == harness.deliveries == []


async def multiple_variations():
    with MonitoringHarness() as harness:
        first = synthetic_report(harness, "multi", variation="first-cheap-strap")
        for c in first.claims:
            if c.subject == "selection" and c.field == "product_kind":
                c.value = "accessory"
            if c.field == "item_price":
                c.value = "1.00"
        selected = synthetic_report(harness, "multi", variation="intended-watch")
        # Separate claims with lineage scoped to the variation, not array position.
        for c in first.claims:
            c.id = "first:" + c.id
        harness.reports["cex"] = [first, selected, selected]
        harness.outcomes["cex"] = [listing(harness, "cex", "multi", "AD2066", "1.00")]
        async with harness.session() as (client, _):
            await acquire(harness)
            candidate = (await get(client, "/api/discovery/watches"))["candidates"][0]
            assert len(candidate["offers"]) == len(candidate["bindings"]) == 2
            offers = {o["binding_id"]: o for o in candidate["offers"]}
            bindings = {b["variation_id"]: b for b in candidate["bindings"]}
            assert offers[bindings["intended-watch"]["id"]]["item_price"] == "48.00"
            assert (
                offers[bindings["first-cheap-strap"]["id"]]["qualification"]["state"] != "supported"
            )
            assert offers[bindings["intended-watch"]["id"]]["qualification"]["state"] == "supported"
            assert len(candidate["configurations"]) == 1
            assert offers[bindings["first-cheap-strap"]["id"]]["comparison"]["state"] == "rejected"


async def persisted_qualification():
    from pathlib import Path

    shared = Path(sys.argv[2])
    with MonitoringHarness(storage_root=shared) as harness:
        if sys.argv[1] == "persist_before":
            harness.outcomes["cex"] = [listing(harness, "cex", "addies", "Addiesdive AD2066 mint")]
            harness.reports["cex"] = [synthetic_report(harness)]
        async with harness.session() as (client, _):
            if sys.argv[1] == "persist_before":
                await acquire(harness)
            initial = (await get(client, "/api/discovery/watches"))["candidates"][0]
            offer = initial["offers"][0]
            assert offer["qualification"]["state"] == "supported"
            assert offer["revision"] == 1
            if sys.argv[1] == "persist_before":
                (shared / "expected.json").write_text(__import__("json").dumps(initial))
            else:
                assert initial == __import__("json").loads((shared / "expected.json").read_text())
                assert harness.searches == []
                harness.clock.advance()
                report = synthetic_report(harness)
                next(c for c in report.claims if c.field == "item_price").value = "45.00"
                harness.reports["cex"] = [report]
                harness.outcomes["cex"] = [listing(harness, "cex", "addies", "AD2066")]
                await acquire(harness)
                refreshed = (await get(client, "/api/discovery/watches"))["candidates"][0]
                assert refreshed["offers"][0]["id"] == offer["id"]
                assert refreshed["offers"][0]["revision"] == 2
                assert refreshed["bindings"][0]["id"] == initial["bindings"][0]["id"]
                assert refreshed["bindings"][0]["revision"] == 2
                assert refreshed["offers"][0]["binding_revision"] == 2
                assert refreshed["offers"][0]["item_price"] == "45.00"
                assert refreshed["offers"][0]["comparison"]["state"] == "unresolved"
            assert harness.deliveries == harness.blocked_edges == []


async def persist_before():
    await persisted_qualification()


async def persist_after():
    await persisted_qualification()


async def boundary_contexts():
    with MonitoringHarness() as harness:
        reports = []
        for key in (
            "basket",
            "near-reference",
            "token-url",
            "no-observed-time",
            "foreign",
            "out-of-stock",
            "same-id",
            "unknown-value",
        ):
            report = synthetic_report(harness, key)
            reports.append(report)
        next(c for c in reports[0].claims if c.field == "item_price").context.quantity = 2
        next(
            c for c in reports[1].claims if c.subject == "configuration" and c.field == "movement"
        ).context.configuration_key = "nearby-family"
        next(
            c for c in reports[2].claims if c.subject == "configuration" and c.field == "movement"
        ).pointer = (
            "https://synthetic.invalid/p?access_token=offline-sensitive-sentinel&variant=123"
        )
        next(
            c for c in reports[3].claims if c.subject == "configuration" and c.field == "movement"
        ).observed_at = None
        for c in reports[4].claims:
            if c.subject != "configuration":
                c.context.destination = "US"
                if c.field == "destination":
                    c.value = "US"
        reports[4].destination = "US"
        next(c for c in reports[5].claims if c.field == "availability").value = "out_of_stock"
        direct = next(
            c for c in reports[6].claims if c.subject == "configuration" and c.field == "movement"
        )
        reports[6].claims.insert(
            0, direct.model_copy(update={"value": "2035", "issuer_kind": "ai_inference"})
        )
        next(
            c for c in reports[7].claims if c.subject == "configuration" and c.field == "movement"
        ).value = "unknown"
        harness.reports["cex"] = reports
        harness.outcomes["cex"] = [
            listing(harness, "cex", r.source_listing_id, r.source_listing_id) for r in reports
        ]
        harness.outcomes["cex"][
            0
        ].url = "https://user:offline-sensitive-sentinel@synthetic.invalid/product?variant=123"
        async with harness.session() as (client, _):
            await acquire(harness)
            response = await client.get("/api/discovery/watches")
            assert "offline-sensitive-sentinel" not in response.text
            candidates = {c["source_listing_id"]: c for c in response.json()["candidates"]}
            assert candidates["basket"]["bindings"][0]["resolution"]["state"] != "supported"
            for key in ("near-reference", "token-url", "no-observed-time", "unknown-value"):
                assert candidates[key]["identity_state"] == "unresolved"
            assert candidates["same-id"]["configuration"]["values"].get("movement") != "2035"
            assert candidates["out-of-stock"]["offers"][0]["qualification"]["state"] == "rejected"
            assert "uk_delivery_unproven" in {
                i["code"] for i in candidates["foreign"]["offers"][0]["comparison"]["issues"]
            }
            assert (
                await client.post(
                    "/api/discovery/watches/qualification", json={"state": "supported"}
                )
            ).status_code in {404, 405}
            assert (
                await client.post("/api/discovery/watches", json={"state": "supported"})
            ).status_code == 405
            assert harness.blocked_edges == harness.deliveries == []


async def untyped_report():
    with MonitoringHarness() as harness:
        harness.report_overrides["cex"] = {
            "exact_variant_confirmed": True,
            "configuration": {"movement": "VH31"},
        }
        async with harness.session() as (client, _):
            await acquire(harness)
            feed = await get(client, "/api/discovery/watches")
            assert feed["candidates"] == []
            assert feed["captures"][0]["outcomes"][0]["state"] == "failed"
            assert feed["captures"][0]["outcomes"][0]["reason"] == "parse_error"
            assert harness.blocked_edges == harness.deliveries == []


async def migration():
    import sqlite3

    with MonitoringHarness() as harness:
        from pricerecon.models.discovery import (
            DiscoveryAdmission,
            DiscoveryCandidate,
            DiscoveryCapture,
            DiscoveryOrigin,
        )

        from .workflows import LEGACY

        harness.seed_legacy([(7, LEGACY)])
        capture = DiscoveryCapture(
            capture_id="ticket02-existing",
            captured_at=harness.clock.now,
            request=DiscoveryOrigin(query="original raw query", sources=["cex"], source_queries={}),
            admission=DiscoveryAdmission(),
            outcomes=[],
        )
        old_lead = DiscoveryCandidate(
            id="old-lead",
            source="cex",
            reported_source="cex",
            source_listing_id="original-listing",
            title="Militado ML05",
            query="original raw query",
            url="https://merchant.invalid/old?variant=original",
            capture_id=capture.capture_id,
            captured_at=harness.clock.now,
            evidence=[],
            advertised_item_price="1.00",
            reported_currency="GBP",
        )
        # This is pre-migration input setup, not a storage assertion. The old
        # lead payload has none of ticket03's new records or proof.
        with sqlite3.connect(harness.database) as connection:
            connection.executescript("""
                CREATE TABLE discovery_captures(capture_id TEXT PRIMARY KEY, category TEXT NOT NULL,
                    captured_at TEXT NOT NULL, payload_json TEXT NOT NULL);
                CREATE TABLE discovery_leads(candidate_id TEXT NOT NULL, capture_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL, PRIMARY KEY(candidate_id,capture_id));
            """)
            connection.execute(
                "INSERT INTO discovery_captures VALUES (?, 'watches', ?, ?)",
                (capture.capture_id, capture.captured_at.isoformat(), capture.model_dump_json()),
            )
            connection.execute(
                "INSERT INTO discovery_leads VALUES (?, ?, ?)",
                (
                    old_lead.id,
                    capture.capture_id,
                    old_lead.model_dump_json(
                        exclude={"configuration", "configurations", "bindings", "offers"}
                    ),
                ),
            )
        async with harness.session() as (client, scheduler):
            candidate = (await get(client, "/api/discovery/watches"))["candidates"][0]
            assert candidate["title"] == "Militado ML05"
            assert candidate["query"] == "original raw query"
            assert candidate["identity_state"] == "unresolved"
            assert candidate["offers"][0]["item_price"] is None
            assert candidate["offers"][0]["seller"] is None
            assert candidate["bindings"][0]["resolution"]["state"] == "unresolved"
            assert candidate["public_delivered_total"]["amount"] is None
            assert len((await get(client, "/api/watches"))["items"]) == 1
            assert len(scheduler.list_watches()) == 1
            assert harness.searches == harness.deliveries == harness.blocked_edges == []


def partial_reports(harness):
    reports = []
    for variation, dial, definition in (
        ("mint", "mint", "synthetic:partial-mint"),
        ("blue", "blue", "synthetic:partial-blue"),
        # Identical partial dimensions do not establish definition equivalence.
        ("twin", "blue", "synthetic:partial-twin"),
        ("no-definition-a", "mint", None),
        ("no-definition-b", "blue", None),
    ):
        report = synthetic_report(harness, "partial", variation=variation, dial=dial)
        report.configuration_key = definition
        report.claims = [c for c in report.claims if c.field != "generation"]
        for claim in report.claims:
            claim.id = variation + ":" + claim.id
            claim.context.configuration_key = definition
            claim.derived_from = [f"synthetic-original:partial:{variation}:{claim.subject}"]
        reports.append(report)
    return reports


async def partial_definitions():
    with MonitoringHarness() as harness:
        mint, blue = partial_reports(harness)[:2]
        harness.reports["cex"] = [mint, blue, blue]
        harness.outcomes["cex"] = [listing(harness, "cex", "partial", "AD2066")]
        async with harness.session() as (client, _):
            response = await client.put(
                "/api/discovery/watches/preferences",
                json={
                    "expected_revision": 0,
                    "values": {"compact_max_width_mm": "37.5", "colourful_dials": ["mint"]},
                },
            )
            assert response.status_code == 200, response.text
            await acquire(harness)
            candidate = (await get(client, "/api/discovery/watches"))["candidates"][0]
            assert len(candidate["configurations"]) == 2, candidate["configurations"]
            configurations = {c["id"]: c for c in candidate["configurations"]}
            assert len(candidate["bindings"]) == len(candidate["offers"]) == 2
            for binding in candidate["bindings"]:
                configuration = configurations[binding["configuration_id"]]
                assert configuration["values"]["dial"] == binding["variation_id"]
                assert configuration["state"] == "unresolved"
                assert "generation" not in configuration["values"]
                assert binding["resolution"]["state"] == "unresolved"
                assert binding["configuration_revision"] == configuration["revision"]
            fits = {f["field"]: f["state"] for f in candidate["preference_fit"]}
            assert fits["compact"] == "fits"
            assert fits["colourful"] == "unknown"
            assert harness.deliveries == harness.blocked_edges == []


async def partial_persistence():
    import json
    from pathlib import Path

    shared = Path(sys.argv[2])
    before = sys.argv[1] == "partial_before"
    with MonitoringHarness(storage_root=shared) as harness:
        async with harness.session() as (client, _):
            if before:
                harness.reports["cex"] = partial_reports(harness)
                harness.outcomes["cex"] = [listing(harness, "cex", "partial", "AD2066")]
                await acquire(harness)
            initial = (await get(client, "/api/discovery/watches"))["candidates"][0]
            if before:
                (shared / "partial.json").write_text(json.dumps(initial))
            else:
                assert initial == json.loads((shared / "partial.json").read_text())
                assert harness.searches == []
                harness.clock.advance()
                reports = partial_reports(harness)
                # Resolution changes and connector order must not change the
                # retained subject's ID or transfer another variation's claims.
                for claim in reports[0].claims:
                    if claim.field == "case_width_mm":
                        claim.value = "37"
                harness.reports["cex"] = list(reversed(reports)) + [reports[1]]
                harness.outcomes["cex"] = [listing(harness, "cex", "partial", "AD2066")]
                await acquire(harness)
            feed = await get(client, "/api/discovery/watches")
            candidate = feed["candidates"][0]
            assert feed["collection_state"] == "staged"
            assert len(candidate["configurations"]) == 5
            configurations = {c["id"]: c for c in candidate["configurations"]}
            bindings = {b["variation_id"]: b for b in candidate["bindings"]}
            initial_bindings = {b["variation_id"]: b for b in initial["bindings"]}
            assert len(bindings) == len(candidate["offers"]) == 5
            for variation, binding in bindings.items():
                configuration = configurations[binding["configuration_id"]]
                assert (
                    binding["configuration_id"] == initial_bindings[variation]["configuration_id"]
                )
                assert binding["id"] == initial_bindings[variation]["id"]
                assert (
                    binding["revision"] == binding["configuration_revision"] == (1 if before else 2)
                )
                assert configuration["revision"] == binding["configuration_revision"]
                assert configuration["state"] == binding["resolution"]["state"] == "unresolved"
                if variation.startswith("no-definition"):
                    assert configuration["values"] == {}
                else:
                    assert configuration["values"]["dial"] == (
                        "mint" if variation == "mint" else "blue"
                    )
                    assert "generation" not in configuration["values"]
                offer = next(o for o in candidate["offers"] if o["binding_id"] == binding["id"])
                assert offer["binding_revision"] == binding["revision"]
                assert offer["qualification"]["state"] == "unresolved"
                assert all(c["id"].startswith(variation + ":") for c in offer["evidence"])
                assert all(variation in c["derived_from"][0] for c in offer["evidence"])
                assert set(configuration["evidence_ids"]) <= {c["id"] for c in offer["evidence"]}
            if not before:
                assert (
                    configurations[bindings["mint"]["configuration_id"]]["values"]["case_width_mm"]
                    == "37"
                )
            assert candidate["public_delivered_total"]["amount"] is None
            assert candidate["usual_price"]["amount"] is candidate["savings"] is None
            assert candidate["alert_eligible"] is False
            assert harness.deliveries == harness.blocked_edges == []


async def partial_before():
    await partial_persistence()


async def partial_after():
    await partial_persistence()


async def shared_definition_conflict():
    with MonitoringHarness() as harness:
        first = synthetic_report(harness, "shared", variation="first")
        second = synthetic_report(harness, "shared", variation="second")
        movement = next(
            c for c in second.claims if c.subject == "configuration" and c.field == "movement"
        )
        movement.id = "conflicting-definition-movement"
        movement.value = "2035"
        direct = next(
            c for c in first.claims if c.subject == "configuration" and c.field == "movement"
        )
        first.claims.extend(direct.model_copy(update={"id": f"re-extracted-{i}"}) for i in range(5))
        harness.reports["cex"] = [first, first, second, first]
        harness.outcomes["cex"] = [listing(harness, "cex", "shared", "AD2066")]
        async with harness.session() as (client, _):
            await acquire(harness)
            candidate = (await get(client, "/api/discovery/watches"))["candidates"][0]
            assert len(candidate["configurations"]) == 1
            configuration = candidate["configuration"]
            assert configuration["state"] == candidate["identity_state"] == "conflicting"
            assert "movement" not in configuration["values"]
            assert any(
                i["field"] == "movement"
                and i["code"] == "conflicting_claims"
                and movement.id in i["evidence_ids"]
                for i in configuration["issues"]
            )
            assert len(candidate["bindings"]) == len(candidate["offers"]) == 2
            assert all(
                b["configuration_id"] == configuration["id"]
                and b["resolution"]["state"] != "supported"
                for b in candidate["bindings"]
            )
            assert all(o["qualification"]["state"] != "supported" for o in candidate["offers"])
            assert harness.deliveries == harness.blocked_edges == []


async def purchase_contexts():
    with MonitoringHarness() as harness:
        reports = [
            synthetic_report(harness, "currency-modes", variation="new"),
            synthetic_report(harness, "currency-modes", variation="used", condition="used"),
            synthetic_report(harness, "currency-modes", variation="auction", mode="auction"),
        ]
        for report in reports:
            for claim in report.claims:
                claim.id = report.variation_id + ":" + claim.id
                if claim.field == "currency":
                    claim.value = "USD"
        for key in (
            "usd",
            "gbp",
            "unknown",
            "price-context",
            "quantity-value",
            "destination-value",
        ):
            report = synthetic_report(harness, key)
            if key in {"usd", "unknown"}:
                report.currency = "USD" if key == "usd" else None
                for claim in report.claims:
                    if claim.subject != "configuration":
                        claim.context.currency = report.currency
                    if claim.field == "currency":
                        claim.value = "USD"
            elif key == "price-context":
                next(c for c in report.claims if c.field == "item_price").context.currency = "USD"
            elif key == "quantity-value":
                next(c for c in report.claims if c.field == "quantity").value = "2"
            elif key == "destination-value":
                next(c for c in report.claims if c.field == "destination").value = "US"
            reports.append(report)
        harness.reports["cex"] = reports
        # An advertised GBP display is only a lead. It cannot replace the
        # explicitly evidenced USD purchase currency or supply missing context.
        harness.outcomes["cex"] = [
            listing(harness, "cex", key, "AD2066")
            for key in dict.fromkeys(r.source_listing_id for r in reports)
        ]
        async with harness.session() as (client, _):
            await acquire(harness)
            feed = await get(client, "/api/discovery/watches")
            candidates = {c["source_listing_id"]: c for c in feed["candidates"]}
            for key, candidate in candidates.items():
                assert candidate["configuration"]["state"] == "supported"
                for binding in candidate["bindings"]:
                    assert (binding["resolution"]["state"] == "supported") == (
                        key in {"usd", "gbp"}
                    )
                for offer in candidate["offers"]:
                    assert (offer["qualification"]["state"] == "supported") == (
                        key in {"usd", "gbp"}
                    )
                    assert offer["comparison"]["state"] != "supported"
                assert candidate["public_delivered_total"]["amount"] is None
                assert candidate["usual_price"]["amount"] is candidate["savings"] is None
                assert candidate["alert_eligible"] is False
            assert candidates["usd"]["offers"][0]["currency"] == "USD"
            assert candidates["usd"]["reported_currency"] == "GBP"
            assert (
                candidates["usd"]["configuration"]["id"] == candidates["gbp"]["configuration"]["id"]
            )
            assert candidates["unknown"]["offers"][0]["currency"] is None
            modes = candidates["currency-modes"]
            assert len(modes["offers"]) == 3
            assert {o["condition"] for o in modes["offers"]} == {"new", "used"}
            assert {o["purchase_mode"] for o in modes["offers"]} == {"buy_now", "auction"}
            assert (
                next(o for o in modes["offers"] if o["purchase_mode"] == "auction")["comparison"][
                    "state"
                ]
                == "rejected"
            )
            assert feed["collection_state"] == "staged"
            assert harness.deliveries == harness.blocked_edges == []


async def currency_binding():
    with MonitoringHarness() as harness:
        report = synthetic_report(harness, "currency-context")
        currency = next(c for c in report.claims if c.field == "currency")
        currency.value = "USD"
        harness.reports["cex"] = [report]
        harness.outcomes["cex"] = [listing(harness, "cex", "currency-context", "AD2066")]
        async with harness.session() as (client, _):
            await acquire(harness)
            candidate = (await get(client, "/api/discovery/watches"))["candidates"][0]
            binding = candidate["bindings"][0]
            offer = candidate["offers"][0]
            assert binding["resolution"]["state"] == "conflicting", binding
            assert offer["qualification"]["state"] == "conflicting", offer
            for resolution in (binding["resolution"], offer["qualification"]):
                assert {
                    "field": "currency",
                    "code": "purchase_context_mismatch",
                    "evidence_ids": [currency.id],
                } in resolution["issues"]
            assert offer["currency"] == "USD"
            assert (
                next(c for c in offer["evidence"] if c["field"] == "item_price")["context"][
                    "currency"
                ]
                == "GBP"
            )
            assert candidate["public_delivered_total"]["amount"] is None
            assert candidate["usual_price"]["amount"] is candidate["savings"] is None
            assert candidate["alert_eligible"] is False
            assert harness.deliveries == harness.blocked_edges == []


async def numeric_safety():
    with MonitoringHarness() as harness:
        report = synthetic_report(harness)
        next(c for c in report.claims if c.field == "item_price").value = "1e999999999"
        harness.reports["cex"] = [report]
        harness.outcomes["cex"] = [listing(harness, "cex", "addies", "Synthetic oversized amount")]
        async with harness.session() as (client, _):
            await acquire(harness)
            feed = await get(client, "/api/discovery/watches")
            assert feed["candidates"] == []
            assert feed["captures"][0]["outcomes"][0]["reason"] == "parse_error"
            assert harness.blocked_edges == harness.deliveries == []


if __name__ == "__main__":
    asyncio.run(globals()[sys.argv[1]]())
