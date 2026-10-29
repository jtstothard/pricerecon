"""Correction scope acceptance through the guarded API and acquisition seams."""

import asyncio
import hashlib
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from .correction_merger_probe import main, reports
from .correction_workflows import edit
from .cost_workflows import read_capture
from .coupon_workflows import reproduced_report
from .harness import MonitoringHarness
from .history_workflows import history, priced_report
from .tracking_workflows import track
from .workflows import get


def configuration(candidate, dial):
    return next(c for c in candidate["configurations"] if c["values"].get("dial") == dial)


async def correct(
    client, candidate, dial="mint", value="salmon", *, root=None, revision=0, state="corrected"
):
    config = configuration(candidate, dial)
    endpoint = f"/api/discovery/candidates/{candidate['id']}/corrections/{root or config['id']}"
    response = await client.post(
        endpoint,
        json={
            **edit(candidate, value=value, expected_revision=revision, state=state),
            "configuration_revision": config["revision"],
            "observed_configuration_id": config["id"],
        },
    )
    return endpoint, response


def selected(candidate, variation):
    binding = next(b for b in candidate["bindings"] if b["variation_id"] == variation)
    offer = next(o for o in candidate["offers"] if o["binding_id"] == binding["id"])
    return binding, offer


def supported(candidate, variation):
    binding, offer = selected(candidate, variation)
    config = next(c for c in candidate["configurations"] if c["id"] == binding["configuration_id"])
    assert config["state"] == "supported"
    assert binding["resolution"]["state"] == offer["qualification"]["state"] == "supported"
    cost = offer["cost_scenarios"][0]
    assert cost["state"] == "verified_at_observation" and cost["withdrawn"] is False
    assert cost["total"] == {"amount": "50.10", "currency": "GBP"}


def withdrawn(candidate, variation):
    binding, offer = selected(candidate, variation)
    assert binding["resolution"]["state"] != "supported"
    assert offer["qualification"]["state"] != "supported"
    cost = offer["cost_scenarios"][0]
    assert cost["withdrawn"] is True and cost["total"] is None
    assert cost["historical_total"] == {"amount": "50.10", "currency": "GBP"}


def with_dials(harness, a="mint", b="blue"):
    result = reports(harness)
    for report, dial in zip(result, (a, b), strict=True):
        for claim in report.claims:
            if claim.field == "dial":
                claim.value = dial
    return result


async def merger_multi():
    with TemporaryDirectory(prefix="ticket07-probe-") as root:
        await main(Path(root) / "receipt.json")


async def merger_single():
    with TemporaryDirectory(prefix="ticket07-probe-") as root:
        await main(Path(root) / "receipt.json", single=True)


async def foreign_descendant():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            initial = (await read_capture(harness, client, reports(harness)))["candidates"][0]
            endpoint, response = await correct(client, initial)
            assert response.status_code == 201, response.text
            before = await get(client, endpoint)
            # A caller cannot attach the unrelated blue subject to mint's
            # journal just by supplying a real, current configuration ID.
            _, response = await correct(
                client, initial, "blue", "red", root=before["configuration_id"], revision=1
            )
            assert response.status_code == 409, response.text
            assert await get(client, endpoint) == before
            supported((await get(client, "/api/discovery/watches"))["candidates"][0], "b")
            assert harness.deliveries == harness.blocked_edges == []


async def other_candidate():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            feed = await read_capture(
                harness, client, [*reports(harness), priced_report(harness, listing_id="other")]
            )
            initial = next(c for c in feed["candidates"] if c["source_listing_id"] != "other")
            other = next(c for c in feed["candidates"] if c["source_listing_id"] == "other")
            assert configuration(initial, "mint")["id"] == configuration(other, "mint")["id"]
            original_history = await history(client, other)
            _, response = await correct(client, initial)
            assert response.status_code == 201
        async with harness.session() as (client, _):
            current = next(
                c
                for c in (await get(client, "/api/discovery/watches"))["candidates"]
                if c["id"] == other["id"]
            )
            assert (
                current["configurations"][0]["state"] == "supported"
            ), "Candidate-specific correction withdrew another listing's configuration revision"
            assert await history(client, other) == original_history
            assert harness.deliveries == harness.blocked_edges == []


async def converged_descendants():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            initial = (await read_capture(harness, client, reports(harness)))["candidates"][0]
            endpoint, response = await correct(client, initial)
            assert response.status_code == 201
            harness.clock.advance(hours=0.1)
            fresh = (await read_capture(harness, client, with_dials(harness, "salmon", "salmon")))[
                "candidates"
            ][0]
            assert len(fresh["configurations"]) == 1
            supported(fresh, "a")
            supported(fresh, "b")
            original = await get(client, endpoint)
            _, response = await correct(
                client, fresh, "salmon", "gold", root=original["configuration_id"], revision=1
            )
            assert response.status_code == 201
            current = (await get(client, "/api/discovery/watches"))["candidates"][0]
            withdrawn(current, "a")
            supported(current, "b")
        async with harness.session() as (client, _):
            assert (await get(client, endpoint))["requalification"] == "required"
            supported((await get(client, "/api/discovery/watches"))["candidates"][0], "b")
            harness.clock.advance(hours=0.1)
            fresh = (await read_capture(harness, client, with_dials(harness, "gold", "salmon")))[
                "candidates"
            ][0]
            supported(fresh, "a")
            supported(fresh, "b")
            assert (await get(client, endpoint))["requalification"] == "supported_by_fresh_evidence"
            assert harness.deliveries == harness.blocked_edges == []


async def stale_corrected_scope(*, shared_original=False):
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            original_reports = with_dials(harness, "mint", "mint" if shared_original else "blue")
            initial = (await read_capture(harness, client, original_reports))["candidates"][0]
            endpoint, response = await correct(client, initial)
            assert response.status_code == 201
            original_facts = response.json()["original_evidence"]
            harness.clock.advance(hours=0.1)
            fresh_reports = with_dials(harness, "salmon", "salmon")
            # The corrected offer claims a new direct capture but one payable
            # dependency still resolves to the retained pre-correction quote.
            fresh_reports[0].cost_scenarios[0].context_evidence[0].derived_from = [
                original_reports[0].cost_scenarios[0].context_evidence[0].capture_id
            ]
            fresh = (await read_capture(harness, client, fresh_reports))["candidates"][0]
            withdrawn(fresh, "a")
            supported(fresh, "b")
            expected = "supported_by_fresh_evidence" if shared_original else "required"
            assert (await get(client, endpoint))["requalification"] == expected
            retained = await history(client, initial)
            newest = [o for o in retained["observations"] if o["capture_id"] == fresh["capture_id"]]
            assert (
                next(o for o in newest if o["binding"]["variation_id"] == "a")["validity"]
                == "invalidated"
            )
            assert (
                next(o for o in newest if o["binding"]["variation_id"] == "b")["validity"]
                == "supported_at_capture"
            )
        async with harness.session() as (client, _):
            restarted = (await get(client, "/api/discovery/watches"))["candidates"][0]
            withdrawn(restarted, "a")
            supported(restarted, "b")
            correction = await get(client, endpoint)
            assert correction["requalification"] == expected
            assert correction["original_evidence"] == original_facts
            assert harness.deliveries == harness.blocked_edges == []


async def unrelated_valid_corrected_stale():
    await stale_corrected_scope()


async def shared_definition_offers():
    await stale_corrected_scope(shared_original=True)


async def multiple_corrections(*, convergent=False):
    intended = "blue" if convergent else "salmon"
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            initial = (await read_capture(harness, client, reports(harness)))["candidates"][0]
            saved = []
            for dial in ("mint", "blue"):
                saved.append(
                    await track(
                        client, {**initial, "configurations": [configuration(initial, dial)]}
                    )
                )
            first, response = await correct(client, initial, value=intended)
            assert response.status_code == 201
            second, response = await correct(client, initial, "blue", "red")
            assert response.status_code == 201
            harness.clock.advance(hours=0.1)
            fresh = (await read_capture(harness, client, with_dials(harness, intended, "blue")))[
                "candidates"
            ][0]
            supported(fresh, "a")
            withdrawn(fresh, "b")
            assert (await get(client, first))["requalification"] == "supported_by_fresh_evidence"
            assert (await get(client, second))["requalification"] == "required"
            intents = [await get(client, f"/api/discovery/tracking/{s['id']}") for s in saved]
            assert intents[0]["invalidation_reason"] is None
            assert intents[1]["invalidation_reason"] is not None
        async with harness.session() as (client, _):
            restarted = (await get(client, "/api/discovery/watches"))["candidates"][0]
            supported(restarted, "a")
            withdrawn(restarted, "b")
            assert (await get(client, first))["requalification"] == "supported_by_fresh_evidence"
            assert (await get(client, second))["requalification"] == "required"
            harness.clock.advance(hours=0.1)
            fresh = (await read_capture(harness, client, with_dials(harness, intended, "red")))[
                "candidates"
            ][0]
            supported(fresh, "a")
            supported(fresh, "b")
            for endpoint, original, dial in zip(
                (first, second), saved, (intended, "red"), strict=True
            ):
                correction = await get(client, endpoint)
                assert correction["requalification"] == "supported_by_fresh_evidence"
                intent = await get(client, f"/api/discovery/tracking/{original['id']}")
                assert intent["target_gbp"] == "60.00"
                assert intent["configuration_id"] == original["configuration_id"]
                assert intent["intended_values"]["dial"] == dial
                assert intent["invalidation_reason"] is None
            retained = await history(client, initial)
            originals = [
                o for o in retained["observations"] if o["capture_id"] == initial["capture_id"]
            ]
            assert {o["configuration"]["values"]["dial"] for o in originals} == {"mint", "blue"}
            assert all(o["validity"] == "invalidated" for o in originals)
            assert harness.deliveries == harness.blocked_edges == []


async def multiple_convergent_corrections():
    await multiple_corrections(convergent=True)


async def unrelated_coupon():
    with MonitoringHarness() as harness:
        from pricerecon.models.coupons import CouponInput

        async with harness.session() as (client, _):
            initial_reports = reports(harness)
            blue = initial_reports[1]
            payload = (
                reproduced_report(harness, "multi-correction").coupons[0].model_dump(mode="json")
            )

            def selected_context(value):
                if isinstance(value, dict):
                    for key, item in value.items():
                        if key == "configuration_key":
                            value[key] = blue.configuration_key
                        elif key == "variation_id":
                            value[key] = blue.variation_id
                        else:
                            selected_context(item)
                elif isinstance(value, list):
                    for item in value:
                        selected_context(item)

            selected_context(payload)
            coupon = CouponInput.model_validate(payload)
            fingerprint = hashlib.sha256(coupon.terms.model_dump_json().encode()).hexdigest()
            coupon.application.terms_fingerprint = fingerprint
            coupon.application.receipt.observation.terms_fingerprint = fingerprint
            blue.coupons = [coupon]
            initial = (await read_capture(harness, client, initial_reports))["candidates"][0]
            before = selected(initial, "b")[1]["coupons"][0]
            assert before["state"] == "reproduced_at_observation", before["issues"]
            _, response = await correct(client, initial)
            assert response.status_code == 201
            current = (await get(client, "/api/discovery/watches"))["candidates"][0]
            supported(current, "b")
            after = selected(current, "b")[1]["coupons"][0]
            assert (
                after == before
            ), "Unrelated blue coupon was withdrawn by mint's correction boundary"
        async with harness.session() as (client, _):
            restarted = (await get(client, "/api/discovery/watches"))["candidates"][0]
            assert selected(restarted, "b")[1]["coupons"][0] == before
            assert harness.deliveries == harness.blocked_edges == []


async def dispute_scope():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            initial = (await read_capture(harness, client, reports(harness)))["candidates"][0]
            _, response = await correct(client, initial)
            assert response.status_code == 201
            _, response = await correct(client, initial, "blue", "red", state="disputed")
            assert response.status_code == 201
            current = (await get(client, "/api/discovery/watches"))["candidates"][0]
            assert (
                configuration(current, "mint")["state"] == "unresolved"
            ), "An independent blue dispute changed mint's corrected state to conflicting"
            assert configuration(current, "blue")["state"] == "conflicting"
            assert harness.deliveries == harness.blocked_edges == []


async def partial_scope():
    with MonitoringHarness() as harness:
        from pricerecon.models.qualification import EvidenceSearchReport

        from .workflows import listing

        async with harness.session() as (client, _):
            initial = (await read_capture(harness, client, reports(harness)))["candidates"][0]
            endpoint, response = await correct(client, initial)
            assert response.status_code == 201
            harness.clock.advance(hours=0.1)
            fresh = reports(harness, corrected=True)
            harness.report_overrides["cex"] = EvidenceSearchReport(
                acquisition_state="partial",
                acquisition_reason="Synthetic truncated selected scope",
                completeness="partial",
                evidence=fresh,
                listings=[listing(harness, "cex", "multi-correction", "Synthetic watch", "1.00")],
            )
            current = (await read_capture(harness, client, fresh))["candidates"][0]
            withdrawn(current, "a")
            supported(current, "b")
            assert (await get(client, endpoint))["requalification"] == "required"
        async with harness.session() as (client, _):
            current = (await get(client, "/api/discovery/watches"))["candidates"][0]
            withdrawn(current, "a")
            supported(current, "b")
            assert (await get(client, endpoint))["requalification"] == "required"
            assert harness.deliveries == harness.blocked_edges == []


async def unsupported_scope():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            initial = (await read_capture(harness, client, reports(harness)))["candidates"][0]
            endpoint, response = await correct(client, initial)
            assert response.status_code == 201
            harness.clock.advance(hours=0.1)
            fresh = with_dials(harness, "salmon", "salmon")
            for claim in fresh[0].claims:
                if claim.subject == "selection" and claim.field == "dial":
                    claim.issuer_kind = "human_correction"
                    claim.extractor_kind = "human"
            current = (await read_capture(harness, client, fresh))["candidates"][0]
            binding, offer = selected(current, "a")
            assert binding["resolution"]["state"] != "supported"
            assert offer["cost_scenarios"][0]["withdrawn"] is True
            assert offer["cost_scenarios"][0]["total"] is None
            supported(current, "b")
            assert (await get(client, endpoint))["requalification"] == "required"
            assert harness.deliveries == harness.blocked_edges == []


async def overlap_scope():
    from unittest.mock import patch

    with MonitoringHarness() as harness:
        from pricerecon import connectors

        async with harness.session() as (client, _):
            initial = (await read_capture(harness, client, reports(harness)))["candidates"][0]
            started, release = asyncio.Event(), asyncio.Event()
            connector = connectors.discover_connectors()["cex"]

            class PausedConnector(connector):
                async def search_with_evidence(self, query, filters=None):
                    result = await super().search_with_evidence(query, filters)
                    started.set()
                    await asyncio.wait_for(release.wait(), 5)
                    return result

            harness.clock.advance(hours=0.1)
            stale = reports(harness, corrected=True)
            with patch.object(connectors, "discover_connectors", lambda: {"cex": PausedConnector}):
                running = asyncio.create_task(read_capture(harness, client, stale))
                await asyncio.wait_for(started.wait(), 5)
                harness.clock.advance(hours=0.01)
                endpoint, response = await correct(client, initial)
                assert response.status_code == 201
                release.set()
                current = (await running)["candidates"][0]
            withdrawn(current, "a")
            supported(current, "b")
            assert (await get(client, endpoint))["requalification"] == "required"
        async with harness.session() as (client, _):
            harness.clock.advance(hours=0.1)
            replayed = (await read_capture(harness, client, stale))["candidates"][0]
            withdrawn(replayed, "a")
            supported(replayed, "b")
            assert (await get(client, endpoint))["requalification"] == "required"
            assert harness.deliveries == harness.blocked_edges == []


async def descendant_target():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            initial = (await read_capture(harness, client, reports(harness)))["candidates"][0]
            endpoint, response = await correct(client, initial)
            assert response.status_code == 201
            root = response.json()["configuration_id"]
            harness.clock.advance(hours=0.1)
            fresh = (await read_capture(harness, client, reports(harness, corrected=True)))[
                "candidates"
            ][0]
            descendant = await track(
                client, {**fresh, "configurations": [configuration(fresh, "salmon")]}
            )
            _, response = await correct(client, fresh, "salmon", "gold", root=root, revision=1)
            assert response.status_code == 201
            harness.clock.advance(hours=0.1)
            current = (await read_capture(harness, client, with_dials(harness, "gold", "blue")))[
                "candidates"
            ][0]
            supported(current, "a")
            assert (await get(client, endpoint))["requalification"] == "supported_by_fresh_evidence"
        async with harness.session() as (client, _):
            intent = await get(client, f"/api/discovery/tracking/{descendant['id']}")
            assert intent["configuration_id"] == descendant["configuration_id"]
            assert intent["target_gbp"] == "60.00"
            assert intent["intended_values"]["dial"] == "gold"
            assert (
                intent["invalidation_reason"] is None
            ), "A target created on the actual descendant cannot recover after fresh requalification"
            assert harness.deliveries == harness.blocked_edges == []


async def former_definition_member():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            await read_capture(harness, client, with_dials(harness, "mint", "mint"))
            harness.clock.advance(hours=0.1)
            current = (await read_capture(harness, client, with_dials(harness, "blue", "mint")))[
                "candidates"
            ][0]
            endpoint, response = await correct(client, current)
            assert response.status_code == 201
            updated = (await get(client, "/api/discovery/watches"))["candidates"][0]
            supported(updated, "a")
            withdrawn(updated, "b")
            harness.clock.advance(hours=0.1)
            fresh = (await read_capture(harness, client, with_dials(harness, "blue", "salmon")))[
                "candidates"
            ][0]
            supported(fresh, "a")
            supported(fresh, "b")
            assert (await get(client, endpoint))["requalification"] == "supported_by_fresh_evidence"
            assert harness.deliveries == harness.blocked_edges == []


async def pre_correction_other_identity():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            previous = (await read_capture(harness, client, with_dials(harness, "blue", "red")))[
                "candidates"
            ][0]
            target = await track(
                client, {**previous, "configurations": [configuration(previous, "blue")]}
            )
            harness.clock.advance(hours=0.1)
            current = (await read_capture(harness, client, with_dials(harness, "mint", "red")))[
                "candidates"
            ][0]
            target_before = await get(client, f"/api/discovery/tracking/{target['id']}")
            _, response = await correct(client, current)
            assert response.status_code == 201
            retained = await history(client, current)
            old_blue = next(
                o
                for o in retained["observations"]
                if o["capture_id"] == previous["capture_id"]
                and o["configuration"]["values"]["dial"] == "blue"
            )
            assert (
                old_blue["validity"] == "supported_at_capture"
            ), "Mint correction withdrew a different identity observed before its subject capture"
            after = await get(client, f"/api/discovery/tracking/{target['id']}")
            for field in (
                "configuration_id",
                "target_gbp",
                "intended_values",
                "revision",
                "invalidation_revision",
                "invalidation_reason",
            ):
                assert after[field] == target_before[field]
            assert harness.deliveries == harness.blocked_edges == []


if __name__ == "__main__":
    asyncio.run(globals()[sys.argv[1]]())
