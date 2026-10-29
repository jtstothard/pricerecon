"""Ticket06 application workflows. Dates and merchant assertions are synthetic."""

import asyncio
import sys
from decimal import Decimal

from .cost_workflows import cost_report, read_capture
from .harness import MonitoringHarness
from .workflows import get


def priced_report(harness, price="48.00", listing_id="history", *, quantity=1):
    report = cost_report(harness, listing_id, quantity=quantity)
    for claim in report.claims:
        if claim.field == "item_price":
            claim.value = price
    report.cost_scenarios[0].components[0].amount = Decimal(price)
    # A new controlled retrieval has its own capture identity. Replaying this
    # report verbatim later is intentionally the same underlying acquisition.
    for claim in report.claims:
        claim.capture_id += ":" + harness.clock.now.isoformat()
        if claim.subject == "offer":
            claim.acquisition_capture_id = claim.capture_id
    for scenario in report.cost_scenarios:
        for claim in scenario.context_evidence + [
            e for c in scenario.components for e in c.evidence
        ]:
            claim.capture_id += ":" + harness.clock.now.isoformat()
            claim.acquisition_capture_id = claim.capture_id
    return report


async def history(client, candidate):
    return await get(client, f"/api/discovery/candidates/{candidate['id']}/history")


async def observations():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, scheduler):
            for price in ("48.00", "48.00", "58.00", "38.00"):
                candidate = (await read_capture(harness, client, [priced_report(harness, price)]))[
                    "candidates"
                ][0]
                harness.clock.advance()
            data = await history(client, candidate)
            assert [o["change"] for o in data["observations"]] == [
                "initial",
                "unchanged",
                "increased",
                "decreased",
            ]
            assert [o["costs"][0]["total"]["amount"] for o in data["observations"]] == [
                "50.10",
                "50.10",
                "60.10",
                "40.10",
            ]
            assert [o["offer"]["revision"] for o in data["observations"]] == [1, 2, 3, 4]
            for observation in data["observations"]:
                assert observation["validity"] == "supported_at_capture"
                assert observation["current_eligible"] is False
                assert observation["market_history_eligible"] is False
                assert observation["evidence_kind"] == "synthetic"
                assert (
                    observation["binding"]["revision"] == observation["offer"]["binding_revision"]
                )
                assert (
                    observation["configuration"]["revision"]
                    == observation["binding"]["configuration_revision"]
                )
                assert observation["costs"][0]["offer_revision"] == observation["offer"]["revision"]
                assert observation["offer"]["availability"] == "in_stock"
                assert observation["costs"][0]["context"]["destination_country"] == "GB"
                assert observation["policy_versions"]["history"] == "observation-history-v1"
            assert data["last_good"]["age_seconds"] == 3600
            assert data["usual_price"]["amount"] is data["savings"] is None
            assert data["history_state"] == "limited"
            assert data["legacy_events_included"] is False
            assert scheduler.list_watches() == []
            assert harness.deliveries == harness.blocked_edges == []


async def gaps():
    with MonitoringHarness() as harness:
        from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest
        from pricerecon.models.qualification import EvidenceSearchReport

        from .workflows import listing

        request = DiscoveryRequest(query="wristwatch", sources=[{"connector": "cex"}])
        admission = DiscoveryAdmission(
            mode="offline_verification",
            policy_reference="synthetic-no-cadence",
            permission_reference="synthetic-only",
            activation_reference="isolated-fixture",
        )
        async with harness.session() as (client, _):
            original = priced_report(harness)
            candidate = (await read_capture(harness, client, [original]))["candidates"][0]
            harness.clock.advance()
            await read_capture(harness, client, [original])
            data = await history(client, candidate)
            assert len(data["observations"]) == 2
            assert data["observations"][1]["duplicate_of"] == data["observations"][0]["id"]
            assert data["observations"][1]["validity"] == "unqualified"
            assert data["last_good"]["age_seconds"] == 3600
            harness.clock.advance()
            harness.report_overrides["cex"] = EvidenceSearchReport(
                listings=harness.outcomes["cex"],
                evidence=[original],
                acquisition_state="cache_reuse",
                acquisition_reason="controlled cached fallback",
                reused_capture_id=original.claims[0].capture_id,
            )
            await execute_discovery(request, admission=admission)
            harness.clock.advance()
            harness.report_overrides["cex"] = EvidenceSearchReport(
                listings=[listing(harness, "cex", "history", "Synthetic history", "48.00")],
                evidence=[priced_report(harness)],
                acquisition_state="partial",
                acquisition_reason="controlled page cap",
                completeness="partial",
            )
            await execute_discovery(request, admission=admission)
            del harness.report_overrides["cex"]
            harness.clock.advance()
            harness.outcomes["cex"] = RuntimeError("controlled failure")
            await execute_discovery(request, admission=admission)
            harness.clock.advance()
            harness.outcomes["cex"] = ConnectorDegradedError(
                status=ConnectorStatus.rate_limited,
                message="controlled cap",
                connector_id="cex",
                detail={"capped": True},
            )
            await execute_discovery(request, admission=admission)
            harness.clock.advance()
            harness.outcomes["cex"] = []
            harness.reports["cex"] = []
            await execute_discovery(request, admission=admission)
            harness.clock.advance(hours=24)
            data = await history(client, candidate)
            assert [a["state"] for a in data["attempts"]] == [
                "success",
                "success",
                "cache_reuse",
                "partial",
                "failed",
                "capped",
                "success_empty",
            ]
            assert {g["state"] for g in data["gaps"] if g["kind"] == "source_outcome"} == {
                "cache_reuse",
                "partial",
                "failed",
                "capped",
                "success_empty",
            }
            assert any(g["kind"] == "unobserved_interval" for g in data["gaps"])
            assert any(g["kind"] == "open_interval" for g in data["gaps"])
            assert data["last_good"]["age_seconds"] == 97200
            assert data["last_good"]["current_eligible"] is False
            assert data["observations"][2]["acquisition_state"] == "cache_reuse"
            assert data["observations"][2]["validity"] == "unqualified"
            assert data["observations"][3]["acquisition_state"] == "partial"
            assert len(data["observations"]) == 4
            feed_candidate = (await get(client, "/api/discovery/watches"))["candidates"][0]
            assert feed_candidate["history"]["last_good"] == data["last_good"]
            assert harness.deliveries == harness.blocked_edges == []


async def copied_lineage():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            original = priced_report(harness)
            candidate = (await read_capture(harness, client, [original]))["candidates"][0]
            harness.clock.advance()
            copied = original.model_copy(deep=True)
            extra = copied.claims[-1].model_copy(deep=True)
            extra.id = "copied-extra"
            extra.capture_id = "another-extraction-of-same-input"
            copied.claims.append(extra)
            await read_capture(harness, client, [copied])
            data = await history(client, candidate)
            assert data["observations"][1]["duplicate_of"] == data["observations"][0]["id"]
            assert data["observations"][1]["validity"] == "unqualified"
            assert data["last_good"]["age_seconds"] == 3600


async def derived_reextraction():
    from pathlib import Path
    from tempfile import TemporaryDirectory

    from .history_merger_probe import probe

    with TemporaryDirectory(prefix="pricerecon-ticket06-probe-") as root:
        await probe(Path(root) / "derived-copy.json")


async def unknown_lineage():
    with MonitoringHarness() as harness:
        from pricerecon.models.qualification import MerchantEvidenceReport

        async with harness.session() as (client, _):
            candidate = (await read_capture(harness, client, [priced_report(harness)]))[
                "candidates"
            ][0]
            before = await history(client, candidate)
            harness.clock.advance()
            payload = priced_report(harness, "38.00").model_dump(mode="json")
            for claim in payload["claims"]:
                if claim["subject"] == "offer" and claim["field"] in {"item_price", "availability"}:
                    claim.pop("acquisition_capture_id", None)
                    claim["derived_from"] = ["unidentified-upstream-input"]
                    claim["extractor"] = "a-new-extractor-is-not-an-acquisition"
            await read_capture(harness, client, [MerchantEvidenceReport.model_validate(payload)])
            data = await history(client, candidate)
            first, unidentified = data["observations"]
            assert unidentified["validity"] == "unqualified"
            assert "capture_lineage_unknown" in unidentified["reasons"]
            assert unidentified["duplicate_of"] is None
            assert unidentified["change"] == "not_comparable"
            assert data["last_good"]["observation_id"] == first["id"]
            assert data["last_good"]["age_seconds"] == 3600
            assert first == before["observations"][0]
            assert data["usual_price"]["amount"] is data["savings"] is None
            assert harness.deliveries == harness.blocked_edges == []


def reextract(report, harness, name):
    copied = report.model_copy(deep=True)
    for claim in copied.claims:
        claim.derived_from = [claim.capture_id]
        claim.capture_id = name + ":" + claim.capture_id
        claim.acquisition_capture_id = None
        claim.extractor = name
        claim.retrieved_at = claim.observed_at = harness.clock.now
    return copied


async def transitive_lineage():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            original = priced_report(harness)
            candidate = (await read_capture(harness, client, [original]))["candidates"][0]
            before = await history(client, candidate)
            harness.clock.advance()
            copied = reextract(original, harness, "first-extraction")
            await read_capture(harness, client, [copied])
            harness.clock.advance()
            await read_capture(harness, client, [reextract(copied, harness, "second-extraction")])
            data = await history(client, candidate)
            first, *copies = data["observations"]
            assert [c["duplicate_of"] for c in copies] == [first["id"], first["id"]]
            assert all(c["validity"] == "unqualified" for c in copies)
            assert all(c["change"] == "not_comparable" for c in copies)
            assert all(c["observed_at"] == first["observed_at"] for c in copies)
            assert original.claims[-1].capture_id in copies[-1]["lineage"]
            assert data["last_good"]["observation_id"] == first["id"]
            assert data["last_good"]["age_seconds"] == 7200
            assert first == before["observations"][0]
            assert harness.deliveries == harness.blocked_edges == []


async def cache_lineage_seed():
    import json
    from pathlib import Path

    with MonitoringHarness(storage_root=Path(sys.argv[2])) as harness:
        from pricerecon.models.qualification import EvidenceSearchReport

        async with harness.session() as (client, _):
            original = priced_report(harness)
            candidate = (await read_capture(harness, client, [original]))["candidates"][0]
            before = await history(client, candidate)
            harness.clock.advance()
            cached = reextract(original, harness, "cache-extraction")
            for claim in cached.claims:
                claim.acquisition_capture_id = claim.capture_id
                claim.derived_from = ["cache-output-without-original-field-provenance"]
            # The acquisition envelope identifies the retained original, even
            # when an adapter's field metadata incorrectly calls extraction new.
            harness.report_overrides["cex"] = EvidenceSearchReport(
                listings=harness.outcomes["cex"],
                evidence=[cached],
                acquisition_state="cache_reuse",
                acquisition_reason="synthetic cached response",
                reused_capture_id=candidate["capture_id"],
            )
            await read_capture(harness, client, [cached])
            after = await history(client, candidate)
            first, second = after["observations"]
            assert second["duplicate_of"] == first["id"]
            assert second["validity"] == "unqualified"
            assert second["observed_at"] == first["observed_at"]
            assert after["last_good"]["age_seconds"] == 3600
            assert first == before["observations"][0]
            harness.root.joinpath("cache-lineage-seed.json").write_text(
                json.dumps(
                    {
                        "candidate": candidate,
                        "original": original.model_dump(mode="json"),
                        "cached": cached.model_dump(mode="json"),
                        "history": after,
                    }
                )
            )
            assert harness.deliveries == harness.blocked_edges == []


async def cache_lineage_restart():
    import json
    from pathlib import Path

    with MonitoringHarness(storage_root=Path(sys.argv[2])) as harness:
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest
        from pricerecon.models.qualification import EvidenceSearchReport, MerchantEvidenceReport

        from .workflows import listing

        seed = json.loads(harness.root.joinpath("cache-lineage-seed.json").read_text())
        harness.clock.advance(hours=24)
        async with harness.session() as (client, _):
            candidate = seed["candidate"]
            retained = await history(client, candidate)
            assert retained["observations"] == seed["history"]["observations"]
            assert retained["last_good"]["age_seconds"] == 86400
            cached = MerchantEvidenceReport.model_validate(seed["cached"])
            await read_capture(harness, client, [cached])  # replay labelled success
            after = await history(client, candidate)
            first = after["observations"][0]
            assert after["observations"][-1]["duplicate_of"] == first["id"]
            assert after["observations"][-1]["validity"] == "unqualified"
            assert after["last_good"]["observation_id"] == first["id"]
            assert after["last_good"]["age_seconds"] == 86400
            harness.clock.advance()
            harness.outcomes["scan"] = [listing(harness, "scan", "history", "Copied", "48.00")]
            harness.reports["scan"] = [reextract(cached, harness, "another-route")]
            await execute_discovery(
                DiscoveryRequest(query="wristwatch", sources=[{"connector": "scan"}]),
                admission=DiscoveryAdmission(
                    mode="offline_verification",
                    policy_reference="synthetic",
                    permission_reference="synthetic",
                    activation_reference="offline-only",
                ),
            )
            copied = next(
                c
                for c in (await get(client, "/api/discovery/watches"))["candidates"]
                if c["source"] == "scan"
            )
            cross_route = await history(client, copied)
            assert cross_route["observations"][0]["duplicate_of"] == first["id"]
            assert cross_route["observations"][0]["validity"] == "unqualified"
            assert cross_route["last_good"] is None
            harness.clock.advance()
            original = MerchantEvidenceReport.model_validate(seed["original"])
            mixed = priced_report(harness, "48.00")
            # A partial result refreshes stock but copies the original price.
            mixed.claims = [c for c in mixed.claims if c.field != "item_price"] + [
                c for c in original.claims if c.subject == "offer" and c.field == "item_price"
            ]
            harness.report_overrides["cex"] = EvidenceSearchReport(
                listings=harness.outcomes["cex"],
                evidence=[mixed],
                acquisition_state="partial",
                acquisition_reason="synthetic partial cache",
                completeness="partial",
            )
            await read_capture(harness, client, [mixed])
            after = await history(client, candidate)
            assert after["observations"][-1]["duplicate_of"] == first["id"]
            assert after["observations"][-1]["validity"] == "unqualified"
            assert after["last_good"]["age_seconds"] == 93600
            harness.clock.advance()
            fresh = priced_report(harness, "58.00")
            fresh.claims = [c for c in original.claims if c.subject != "offer"] + [
                c for c in fresh.claims if c.subject == "offer"
            ]
            harness.report_overrides["cex"].evidence = [fresh]
            await read_capture(harness, client, [fresh])
            final = await history(client, candidate)
            assert final["observations"][-1]["validity"] == "supported_at_capture"
            assert final["observations"][-1]["change"] == "increased"
            assert final["observations"][-1]["duplicate_of"] is None
            assert final["last_good"]["age_seconds"] == 0
            assert final["observations"][:2] == seed["history"]["observations"]
            assert harness.deliveries == harness.blocked_edges == []


async def retained_cost_age():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            original = priced_report(harness)
            candidate = (await read_capture(harness, client, [original]))["candidates"][0]
            before = await history(client, candidate)
            harness.clock.advance()
            fresh = priced_report(harness, "58.00")
            old_shipping = original.cost_scenarios[0].components[1].evidence[0]
            shipping = old_shipping.model_copy(deep=True)
            shipping.derived_from = [shipping.capture_id]
            shipping.capture_id = "new-cost-extraction:" + shipping.capture_id
            shipping.observed_at = shipping.retrieved_at = harness.clock.now
            fresh.cost_scenarios[0].components[1].evidence = [shipping]
            await read_capture(harness, client, [fresh])
            data = await history(client, candidate)
            first, second = data["observations"]
            assert second["validity"] == "supported_at_capture"
            assert second["change"] == "increased"
            assert second["duplicate_of"] is None
            assert second["observed_at"] == first["observed_at"]
            assert data["last_good"]["age_seconds"] == 3600
            assert first == before["observations"][0]
            assert (
                second["costs"][0]["components"][1]["evidence"][0]["observed_at"]
                == "2026-10-27T13:00:00Z"
            )
            assert harness.deliveries == harness.blocked_edges == []


async def unresolved_origins():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            original = priced_report(harness)
            candidate = (await read_capture(harness, client, [original]))["candidates"][0]
            before = await history(client, candidate)
            harness.clock.advance()
            first = priced_report(harness, "38.00")
            first_id = first.claims[-1].capture_id
            harness.clock.advance()
            second = priced_report(harness, "38.00")
            second_id = second.claims[-1].capture_id
            for report, other in ((first, second_id), (second, first_id)):
                for claim in report.claims:
                    if claim.subject == "offer" and claim.field in {"item_price", "availability"}:
                        claim.acquisition_capture_id = None
                        claim.derived_from = [other]
                await read_capture(harness, client, [report])
            data = await history(client, candidate)
            assert all(o["validity"] == "unqualified" for o in data["observations"][1:])
            assert all("capture_lineage_unknown" in o["reasons"] for o in data["observations"][1:])
            assert all(o["duplicate_of"] is None for o in data["observations"][1:])
            assert all(o["change"] == "not_comparable" for o in data["observations"][1:])
            assert data["observations"][0] == before["observations"][0]
            assert data["last_good"]["age_seconds"] == 7200
            harness.clock.advance()
            foreign = priced_report(harness, listing_id="other-product")
            for claim in foreign.claims:
                if claim.subject == "offer" and claim.field in {"item_price", "availability"}:
                    claim.acquisition_capture_id = original.claims[-1].capture_id
                    claim.derived_from = [original.claims[-1].capture_id]
            other = next(
                c
                for c in (await read_capture(harness, client, [foreign]))["candidates"]
                if c["source_listing_id"] == "other-product"
            )
            withheld = await history(client, other)
            assert withheld["history_state"] == "unavailable"
            assert withheld["last_good"] is None
            assert withheld["observations"][0]["duplicate_of"] is None
            assert "capture_lineage_unknown" in withheld["observations"][0]["reasons"]
            assert (await history(client, candidate))["observations"] == data["observations"]
            assert harness.deliveries == harness.blocked_edges == []


async def migration_before():
    import json
    import sqlite3
    from contextlib import closing
    from pathlib import Path

    from .workflows import LEGACY, check, listing

    with MonitoringHarness(storage_root=Path(sys.argv[2])) as harness:
        harness.seed_legacy(
            [(7, LEGACY), (8, {**LEGACY, "name": "Paused history fixture", "enabled": False})]
        )
        async with harness.session() as (client, _):
            harness.outcomes["cex"] = [listing(harness, "cex", "legacy", "ML05B mint", "90.00")]
            await check(client, 7)
            harness.clock.advance()
            harness.outcomes["cex"] = [listing(harness, "cex", "legacy", "ML05B mint", "80.00")]
            await check(client, 7)
            assert len(harness.deliveries) == 3
            harness.deliveries.clear()
            candidate = (await read_capture(harness, client, [priced_report(harness)]))[
                "candidates"
            ][0]
            retained = await history(client, candidate)
            receipt = {
                "candidate": candidate,
                "observation": retained["observations"][0],
                "watch": await get(client, "/api/watches/7"),
                "paused": await get(client, "/api/watches/8"),
                "listings": await get(client, "/api/watches/7/listings"),
                "events": await get(client, "/api/watches/7/events"),
            }
            assert receipt["events"]["total"] == 1
        # Explicit old-schema seed, never a production connection. Remove only
        # the new additive migration and mark the original capture as pre-contract.
        with closing(sqlite3.connect(harness.database)) as db, db:
            from pricerecon.models.discovery import DiscoveryCapture

            payload = DiscoveryCapture.model_validate_json(
                db.execute(
                    "SELECT payload_json FROM discovery_captures WHERE capture_id = ?",
                    (candidate["capture_id"],),
                ).fetchone()[0]
            ).model_dump(mode="json")
            payload.pop("history_contract_version")
            db.execute(
                "UPDATE discovery_captures SET payload_json = ? WHERE capture_id = ?",
                (json.dumps(payload), candidate["capture_id"]),
            )
            db.execute("DROP TABLE discovery_history_invalidations")
            db.execute("DELETE FROM schema_migrations WHERE version = '1.7'")
            db.execute(
                "INSERT INTO price_history(listing_key,watch_id,price,currency,in_stock,timestamp) VALUES(?,7,'12.34','GBP',1,?)",
                ("cex:legacy", "2026-01-01T12:00:00+00:00"),
            )
        harness.root.joinpath("history-seed.json").write_text(json.dumps(receipt))


async def migration_after():
    import json
    import sqlite3
    from contextlib import closing
    from pathlib import Path

    with MonitoringHarness(storage_root=Path(sys.argv[2])) as harness:
        from pricerecon.db.history import append_history_invalidation
        from pricerecon.models.history import HistoryInvalidation

        receipt = json.loads(harness.root.joinpath("history-seed.json").read_text())
        harness.clock.advance(hours=24)
        async with harness.session() as (client, scheduler):
            assert await get(client, "/api/watches/7") == receipt["watch"]
            assert await get(client, "/api/watches/8") == receipt["paused"]
            assert await get(client, "/api/watches/7/listings") == receipt["listings"]
            assert await get(client, "/api/watches/7/events") == receipt["events"]
            old_history = await get(client, "/api/watches/7/history")
            assert old_history["total"] == 1 and old_history["items"][0]["price"] == "12.34"
            data = await history(client, receipt["candidate"])
            assert data["observations"][0]["validity"] == "legacy_unqualified"
            assert data["observations"][0]["offer"] == receipt["observation"]["offer"]
            assert data["last_good"] is None
            candidate = (await read_capture(harness, client, [priced_report(harness, "38.00")]))[
                "candidates"
            ][0]
            before = await history(client, candidate)
            assert before["observations"][1]["validity"] == "supported_at_capture"
            target = next(
                d for d in before["observations"][1]["dependencies"] if d["kind"] == "cost"
            )
            with closing(sqlite3.connect(harness.database)) as db, db:
                append_history_invalidation(
                    db,
                    HistoryInvalidation(
                        id="synthetic-future-correction",
                        target=target,
                        recorded_at=harness.clock.now,
                        reason="Synthetic dependent-cost withdrawal seed for ticket07 contract",
                        correction_reference="synthetic-correction-07-not-implemented",
                    ),
                )
            harness.root.joinpath("history-before-withdrawal.json").write_text(json.dumps(before))
            assert len(scheduler.list_watches()) == 1
            assert harness.searches and harness.deliveries == harness.blocked_edges == []


async def invalidation_after():
    import json
    from pathlib import Path

    with MonitoringHarness(storage_root=Path(sys.argv[2])) as harness:
        harness.clock.advance(hours=48)
        async with harness.session() as (client, _):
            seed = json.loads(harness.root.joinpath("history-seed.json").read_text())
            before = json.loads(harness.root.joinpath("history-before-withdrawal.json").read_text())
            after = await history(client, seed["candidate"])
            assert after["observations"][0]["validity"] == "legacy_unqualified"
            assert after["observations"][1]["validity"] == "invalidated"
            assert after["observations"][1]["offer"] == before["observations"][1]["offer"]
            assert after["observations"][1]["costs"] == before["observations"][1]["costs"]
            assert (
                after["observations"][1]["dependencies"]
                == before["observations"][1]["dependencies"]
            )
            assert after["observations"][1]["market_history_eligible"] is False
            assert after["last_good"] is None
            assert after["history_state"] == "unavailable"
            assert await get(client, "/api/watches/7/events") == seed["events"]
            assert (
                await client.get("/api/discovery/candidates/unknown/history")
            ).status_code == 404
            assert (
                await client.get("/api/discovery/candidates/' OR 1=1--/history")
            ).status_code == 404
            assert (
                await client.post(
                    f"/api/discovery/candidates/{seed['candidate']['id']}/history", json={}
                )
            ).status_code == 405
            assert harness.searches == harness.deliveries == harness.blocked_edges == []


async def basis_changes():
    with MonitoringHarness() as harness:
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest
        from pricerecon.models.qualification import EvidenceSearchReport

        from .workflows import listing

        admission = DiscoveryAdmission(
            mode="offline_verification",
            policy_reference="synthetic",
            permission_reference="synthetic",
            activation_reference="offline-only",
        )
        request = DiscoveryRequest(query="wristwatch", sources=[{"connector": "cex"}])
        async with harness.session() as (client, _):
            candidate = (await read_capture(harness, client, [priced_report(harness)]))[
                "candidates"
            ][0]
            harness.clock.advance()
            different_quantity = priced_report(harness, quantity=2)
            await read_capture(harness, client, [different_quantity])
            data = await history(client, candidate)
            assert [o["change"] for o in data["observations"]] == ["initial", "initial"]
            harness.clock.advance()
            missing = priced_report(harness)
            missing.cost_scenarios[0].components[1].state = "unknown"
            missing.cost_scenarios[0].components[1].amount = None
            missing.cost_scenarios[0].components[1].currency = None
            await read_capture(harness, client, [missing])
            data = await history(client, candidate)
            assert data["observations"][2]["validity"] == "unqualified"
            assert data["observations"][2]["change"] == "not_comparable"
            assert data["observations"][2]["costs"][0]["total"] is None
            assert data["observations"][2]["costs"][0]["known_subtotal"] == {"GBP": "48.00"}
            assert data["last_good"]["age_seconds"] == 3600
            harness.clock.advance()
            # Adapter mutation must be revalidated before recording a cached result.
            malformed = EvidenceSearchReport(listings=[])
            malformed.acquisition_state = "cache_reuse"
            harness.report_overrides["cex"] = malformed
            await execute_discovery(request, admission=admission)
            del harness.report_overrides["cex"]
            harness.clock.advance()
            harness.outcomes["cex"] = [listing(harness, "cex", "other", "Other lead", "8.00")]
            harness.reports["cex"] = []
            await execute_discovery(request, admission=admission)
            before = await history(client, candidate)
            assert before["attempts"][-2]["state"] == "failed"
            assert before["attempts"][-2]["reason"] == "parse_error"
            assert any(g["kind"] == "not_returned" for g in before["gaps"])
            harness.clock.advance()
            harness.outcomes["cex"] = RuntimeError("Unrelated query failure")
            await execute_discovery(
                DiscoveryRequest(query="unrelated query", sources=[{"connector": "cex"}]),
                admission=admission,
            )
            after = await history(client, candidate)
            assert after["attempts"] == before["attempts"]
            assert len(after["observations"]) == 3
            assert after["savings"] is after["usual_price"]["amount"] is None
            assert harness.deliveries == harness.blocked_edges == []


async def cross_route():
    with MonitoringHarness() as harness:
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.models.discovery import DiscoveryAdmission, DiscoveryRequest

        from .workflows import listing

        async with harness.session() as (client, _):
            report = priced_report(harness)
            original = (await read_capture(harness, client, [report]))["candidates"][0]
            first = (await history(client, original))["observations"][0]
            harness.clock.advance()
            harness.outcomes["scan"] = [listing(harness, "scan", "history", "Copied lead", "48.00")]
            harness.reports["scan"] = [report]
            await execute_discovery(
                DiscoveryRequest(query="wristwatch", sources=[{"connector": "scan"}]),
                admission=DiscoveryAdmission(
                    mode="offline_verification",
                    policy_reference="synthetic",
                    permission_reference="synthetic",
                    activation_reference="offline-only",
                ),
            )
            copied = next(
                c
                for c in (await get(client, "/api/discovery/watches"))["candidates"]
                if c["source"] == "scan"
            )
            data = await history(client, copied)
            assert data["observations"][0]["duplicate_of"] == first["id"]
            assert data["observations"][0]["captured_at"] != first["captured_at"]
            assert data["observations"][0]["observed_at"] == first["observed_at"]
            assert data["history_state"] == "unavailable"
            assert data["last_good"] is None
            assert data["observations"][0]["offer"]["evidence"] == first["offer"]["evidence"]
            assert harness.deliveries == harness.blocked_edges == []


async def retained_definitions():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            original = priced_report(harness)
            candidate = (await read_capture(harness, client, [original]))["candidates"][0]
            harness.clock.advance()
            fresh = priced_report(harness, "58.00")
            fresh.claims = [c for c in original.claims if c.subject != "offer"] + [
                c for c in fresh.claims if c.subject == "offer"
            ]
            await read_capture(harness, client, [fresh])
            data = await history(client, candidate)
            assert data["observations"][1]["duplicate_of"] is None
            assert data["observations"][1]["change"] == "increased"
            assert data["observations"][1]["validity"] == "supported_at_capture"
            assert data["last_good"]["age_seconds"] == 0
            assert harness.deliveries == harness.blocked_edges == []


if __name__ == "__main__":
    asyncio.run(globals()[sys.argv[1]]())
