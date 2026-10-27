"""Ticket07 API/execution workflows using original synthetic evidence only."""

import asyncio
import sys

from .coupon_workflows import reproduced_report
from .harness import MonitoringHarness
from .history_workflows import history, priced_report
from .tracking_workflows import capture, track
from .workflows import get


def edit(candidate, *, expected_revision=0, field="dial", value="salmon", state="corrected"):
    config = candidate["configurations"][0]
    return {
        "expected_revision": expected_revision,
        "capture_id": candidate["capture_id"],
        "configuration_revision": config["revision"],
        "field": field,
        "value": value,
        "state": state,
        "actor": "Synthetic buyer",
        "rationale": "Selected dial was misidentified",
    }


def url(candidate):
    return f"/api/discovery/candidates/{candidate['id']}/corrections/{candidate['configurations'][0]['id']}"


async def persistence():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            _, feed = await capture(harness, client, reproduced_report(harness, "history"))
            candidate = feed["candidates"][0]
            saved = await track(client, candidate)
            original = await history(client, candidate)
            response = await client.post(url(candidate), json=edit(candidate))
            assert response.status_code == 201, response.text
            correction = response.json()
            assert correction["revision"] == 1
            assert correction["state"] == "corrected"
            assert correction["values"]["dial"] == "salmon"
            assert correction["lineage"][0]["original_value"] == "mint"
            assert correction["lineage"][0]["actor"] == "Synthetic buyer"
            assert correction["original_configuration"] == candidate["configurations"][0]
            assert correction["original_evidence"] == candidate["offers"][0]["evidence"]
            assert (await client.post(url(candidate), json=edit(candidate))).status_code == 409
            updated = (await get(client, "/api/discovery/watches"))["candidates"][0]
            assert updated["corrections"][0] == correction
            assert updated["public_delivered_total"]["amount"] is None
            assert updated["offers"][0]["comparison_cohort"] is None
            assert updated["offers"][0]["comparison"]["state"] != "supported"
            assert updated["bindings"][0]["resolution"]["state"] != "supported"
            costs = await get(client, f"/api/discovery/offers/{candidate['offers'][0]['id']}/costs")
            assert costs["scenarios"][0]["withdrawn"] is True
            assert costs["scenarios"][0]["total"] is None
            assert costs["scenarios"][0]["historical_total"]["amount"] == "50.10"
            coupons = await get(
                client, f"/api/discovery/offers/{candidate['offers'][0]['id']}/coupons"
            )
            coupon = coupons["assessments"][0]
            assert coupon["state"] == "invalidated" and coupon["resulting_cost"] is None
            assert coupon["historical_resulting_cost"]["total"]["amount"] == "45.10"
            retained = await history(client, candidate)
            assert (
                retained["observations"][0]["configuration"]
                == original["observations"][0]["configuration"]
            )
            assert retained["observations"][0]["offer"]["item_price"] == "48.00"
            assert retained["observations"][0]["validity"] == "invalidated"
            intent = await get(client, f"/api/discovery/tracking/{saved['id']}")
            assert (
                intent["target_gbp"] == "60.00"
                and intent["configuration_id"] == saved["configuration_id"]
            )
            assert intent["assessment"]["state"] == "withheld"
            assert intent["intended_values"]["dial"] == "salmon"
        async with harness.session() as (client, _):
            assert await get(client, url(candidate)) == correction
            assert (await get(client, "/api/discovery/watches"))["candidates"][0][
                "public_delivered_total"
            ]["amount"] is None
            assert harness.deliveries == harness.blocked_edges == []


async def validation():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            _, feed = await capture(harness, client, priced_report(harness))
            candidate = feed["candidates"][0]
            for update in (
                {"field": "availability", "value": "in_stock"},
                {"field": "item_price", "value": "1"},
                {"actor": " "},
                {"rationale": " "},
                {"value": " "},
                {"field": "case_width_mm", "value": "NaN"},
                {"field": "product_kind", "value": "authentic"},
                {"configuration_revision": True},
                {"binding": {"state": "supported"}},
            ):
                response = await client.post(url(candidate), json={**edit(candidate), **update})
                assert response.status_code == 422, response.text
            for update in ({"configuration_revision": 999}, {"capture_id": "stale"}):
                assert (
                    await client.post(url(candidate), json={**edit(candidate), **update})
                ).status_code == 409
            assert (await get(client, url(candidate)))["revision"] == 0
            first = await client.post(url(candidate), json=edit(candidate, state="disputed"))
            assert first.status_code == 201
            assert first.json()["state"] == "disputed"
            feed = await get(client, "/api/discovery/watches")
            assert feed["candidates"][0]["identity_state"] == "conflicting"
            second = await client.post(url(candidate), json=edit(candidate, expected_revision=1))
            assert second.status_code == 201, second.text
            assert second.json()["state"] == "corrected"
            lineage = second.json()["lineage"]
            assert len(lineage) == 2 and lineage[1]["previous_correction_id"] == lineage[0]["id"]
            assert lineage[0] == first.json()["lineage"][0]
            assert harness.deliveries == harness.blocked_edges == []


async def overlap():
    from unittest.mock import patch

    with MonitoringHarness() as harness:
        from pricerecon import connectors

        async with harness.session() as (client, _):
            old = priced_report(harness, "68")
            _, feed = await capture(harness, client, old)
            candidate = feed["candidates"][0]
            saved = await track(client, candidate)
            started, release = asyncio.Event(), asyncio.Event()
            connector = connectors.discover_connectors()["cex"]

            class PausedConnector(connector):
                async def search_with_evidence(self, query, filters=None):
                    result = await super().search_with_evidence(query, filters)
                    started.set()
                    await release.wait()
                    return result

            harness.clock.advance(hours=0.1)
            stale_report = priced_report(harness, "40")
            with patch.object(connectors, "discover_connectors", lambda: {"cex": PausedConnector}):
                running = asyncio.create_task(capture(harness, client, stale_report))
                await asyncio.wait_for(started.wait(), 5)
                response = await client.post(url(candidate), json=edit(candidate))
                assert response.status_code == 201, response.text
                release.set()
                stale_capture, feed = await running
            assert feed["candidates"][0]["public_delivered_total"]["amount"] is None
            assert stale_capture.publication_state == "withdrawn", stale_capture
            assert (await history(client, candidate))["observations"][-1][
                "validity"
            ] == "invalidated"
            assert harness.deliveries == []
        async with harness.session() as (client, _):
            # A restart and a post-correction retrieval of the old assessment
            # must not lift the withdrawal or turn a stale £40 into a bargain.
            await capture(harness, client, stale_report)
            feed = await get(client, "/api/discovery/watches")
            assert feed["candidates"][0]["public_delivered_total"]["amount"] is None
            assert (await get(client, f"/api/discovery/tracking/{saved['id']}"))["assessment"][
                "state"
            ] == "withheld"
            assert harness.deliveries == harness.blocked_edges == []


def fresh_corrected(harness, price="68"):
    report = priced_report(harness, price)
    for claim in report.claims:
        if claim.field == "dial":
            claim.value = "salmon"
    return report


async def requalification():
    from unittest.mock import patch

    with MonitoringHarness() as harness:
        from pricerecon.core import notifications

        async with harness.session() as (client, _):
            _, feed = await capture(harness, client, priced_report(harness))
            candidate = feed["candidates"][0]
            saved = await track(client, candidate, notifications={"channels": ["webhook"]})
            before = await history(client, candidate)
            correction = await client.post(url(candidate), json=edit(candidate))
            assert correction.status_code == 201
            harness.clock.advance(hours=0.1)
            # A fully fresh wrong dial remains withheld.
            await capture(harness, client, priced_report(harness, "40"))
            assert (await get(client, "/api/discovery/watches"))["candidates"][0][
                "public_delivered_total"
            ]["amount"] is None
            harness.clock.advance(hours=0.1)
            _, feed = await capture(harness, client, fresh_corrected(harness))
            current = feed["candidates"][0]
            assert current["public_delivered_total"]["amount"] == "70.10"
            assert current["corrections"][0]["requalification"] == "supported_by_fresh_evidence"
            intent = await get(client, f"/api/discovery/tracking/{saved['id']}")
            assert (
                intent["target_gbp"] == "60.00" and intent["assessment"]["state"] == "above_target"
            ), intent
            assert intent["configuration_id"] == saved["configuration_id"]
            assert intent["assessment"]["configuration_id"] == current["configuration"]["id"]
            retained = await history(client, candidate)
            assert (
                retained["observations"][0]["configuration"]
                == before["observations"][0]["configuration"]
            )
            assert retained["observations"][0]["validity"] == "invalidated"
            assert retained["observations"][-1]["change"] == "initial"
            assert retained["observations"][-1]["configuration"]["values"]["dial"] == "salmon"
            assert harness.deliveries == []
            with patch.object(
                notifications,
                "get_global_notification_config",
                lambda: {"webhook_url": "https://synthetic.invalid/captured"},
            ):
                harness.clock.advance(hours=0.1)
                await capture(harness, client, fresh_corrected(harness, "56"))
                assert len(harness.deliveries) == 1
                assert (
                    harness.deliveries[0][2]["listing"]["configuration_id"]
                    == current["configuration"]["id"]
                )
                harness.clock.advance(hours=0.1)
                await capture(harness, client, fresh_corrected(harness, "56"))
                assert len(harness.deliveries) == 1
            assert harness.blocked_edges == []


async def recorrection():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            _, feed = await capture(harness, client, priced_report(harness))
            original = feed["candidates"][0]
            saved = await track(client, original)
            assert (await client.post(url(original), json=edit(original))).status_code == 201
            harness.clock.advance()
            _, feed = await capture(harness, client, fresh_corrected(harness))
            current = feed["candidates"][0]
            response = await client.post(
                url(original),
                json={
                    **edit(current, expected_revision=1, value="blue"),
                    "observed_configuration_id": current["configuration"]["id"],
                },
            )
            assert response.status_code == 201, response.text
            assert response.json()["values"]["dial"] == "blue"
            assert len(response.json()["lineage"]) == 2
            assert (await get(client, "/api/discovery/watches"))["candidates"][0][
                "public_delivered_total"
            ]["amount"] is None
            assert (await get(client, f"/api/discovery/tracking/{saved['id']}"))["assessment"][
                "state"
            ] == "withheld"
            retained = await history(client, current)
            assert all(o["validity"] == "invalidated" for o in retained["observations"])
            assert harness.deliveries == harness.blocked_edges == []


async def inflight():
    from unittest.mock import patch

    with MonitoringHarness() as harness:
        from pricerecon.core import notifications

        async with harness.session() as (client, _):
            _, feed = await capture(harness, client, priced_report(harness))
            saved = await track(
                client, feed["candidates"][0], notifications={"channels": ["webhook"]}
            )
            await capture(harness, client, priced_report(harness, "68"))
            started, release = asyncio.Event(), asyncio.Event()

            async def send(url, payload):
                harness.deliveries.append(("webhook", url, payload))
                started.set()
                await release.wait()
                return True

            harness.clock.advance(hours=0.1)
            with (
                patch.object(
                    notifications,
                    "get_global_notification_config",
                    lambda: {"webhook_url": "https://synthetic.invalid/captured"},
                ),
                patch.object(notifications, "send_webhook", send),
            ):
                running = asyncio.create_task(
                    capture(harness, client, priced_report(harness, "56"))
                )
                await asyncio.wait_for(started.wait(), 5)
                candidate = (await get(client, "/api/discovery/watches"))["candidates"][0]
                before = await history(client, candidate)
                response = await client.post(url(candidate), json=edit(candidate))
                assert response.status_code == 409, response.text
                assert "in flight" in response.json()["detail"]
                assert (await get(client, url(candidate)))["revision"] == 0
                assert await history(client, candidate) == before
                assert (await get(client, "/api/discovery/watches"))["candidates"][0][
                    "public_delivered_total"
                ]["amount"] == "58.10"
                assert (await get(client, f"/api/discovery/tracking/{saved['id']}"))[
                    "invalidation_revision"
                ] == 0
                release.set()
                await running
            accepted = list(harness.deliveries)
            response = await client.post(url(candidate), json=edit(candidate))
            assert response.status_code == 201, response.text
            assert harness.deliveries == accepted and len(accepted) == 1
            deliveries = await get(client, f"/api/discovery/tracking/{saved['id']}/deliveries")
            assert deliveries["items"][0]["channels"]["webhook"] == "sent"
            assert harness.blocked_edges == []


async def pending():
    from unittest.mock import patch

    class Interrupted(BaseException):
        pass

    with MonitoringHarness() as harness:
        from pricerecon.core import notifications
        from pricerecon.core.exact_tracking import deliver_pending_targets

        from .tracking_workflows import policy

        async with harness.session() as (client, _):
            _, feed = await capture(harness, client, priced_report(harness))
            saved = await track(
                client, feed["candidates"][0], notifications={"channels": ["webhook"]}
            )
            await capture(harness, client, priced_report(harness, "68"))

            def crash():
                raise Interrupted("Synthetic interruption before channel claim")

            harness.clock.advance(hours=0.1)
            with patch.object(notifications, "get_global_notification_config", crash):
                try:
                    await capture(harness, client, priced_report(harness, "56"))
                except Interrupted:
                    pass
                else:
                    raise AssertionError("Expected interrupted pending dispatch")
            candidate = (await get(client, "/api/discovery/watches"))["candidates"][0]
            assert (await client.post(url(candidate), json=edit(candidate))).status_code == 201
        async with harness.session() as (client, _):
            with patch.object(
                notifications,
                "get_global_notification_config",
                lambda: {"webhook_url": "https://synthetic.invalid/captured"},
            ):
                await deliver_pending_targets(policy=policy())
            deliveries = await get(client, f"/api/discovery/tracking/{saved['id']}/deliveries")
            assert deliveries["items"][0]["status"] == "withheld"
            assert harness.deliveries == harness.blocked_edges == []


async def derived_replay():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            original = priced_report(harness)
            _, feed = await capture(harness, client, original)
            candidate = feed["candidates"][0]
            assert (
                await client.post(url(candidate), json=edit(candidate, value="mint"))
            ).status_code == 201
            harness.clock.advance()
            replay = priced_report(harness, "40")
            for current, old in zip(replay.claims, original.claims, strict=True):
                if current.subject == "offer":
                    current.derived_from = [old.capture_id]
            _, feed = await capture(harness, client, replay)
            assert feed["candidates"][0]["public_delivered_total"]["amount"] is None
            assert (await get(client, url(candidate)))["requalification"] == "required"
            assert harness.deliveries == harness.blocked_edges == []


async def coupon_replay():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            original = priced_report(harness)
            original.coupons = reproduced_report(harness, "history").coupons
            _, feed = await capture(harness, client, original)
            candidate = feed["candidates"][0]
            assert (
                candidate["offers"][0]["coupons"][0]["resulting_cost"]["total"]["amount"] == "45.10"
            )
            assert (
                await client.post(url(candidate), json=edit(candidate, value="mint"))
            ).status_code == 201
            harness.clock.advance(hours=0.1)
            fresh = priced_report(harness)
            fresh.coupons = original.model_copy(deep=True).coupons
            application = fresh.coupons[0].application
            for name in (
                "expected_coupon_revision",
                "expected_offer_revision",
                "expected_binding_revision",
                "expected_configuration_revision",
                "expected_base_revision",
            ):
                setattr(application, name, 2)
                setattr(application.receipt.observation, name, 2)
            _, feed = await capture(harness, client, fresh)
            current = feed["candidates"][0]
            assert current["public_delivered_total"]["amount"] == "50.10"
            coupon = current["offers"][0]["coupons"][0]
            assert coupon["state"] == "invalidated" and coupon["resulting_cost"] is None, (
                coupon["state"],
                coupon["issues"],
            )
            assert "receipt_predates_correction" in coupon["issues"]
            harness.clock.advance(hours=0.1)
            fresh = priced_report(harness)
            fresh.coupons = reproduced_report(harness, "history", revision=3).coupons
            _, feed = await capture(harness, client, fresh)
            coupon = feed["candidates"][0]["offers"][0]["coupons"][0]
            assert coupon["state"] == "reproduced_at_observation", (
                coupon["state"],
                coupon["issues"],
            )
            assert coupon["resulting_cost"]["total"]["amount"] == "45.10"
            assert harness.deliveries == harness.blocked_edges == []


async def numeric_identity():
    with MonitoringHarness() as harness:
        async with harness.session() as (client, _):
            _, feed = await capture(harness, client, priced_report(harness))
            candidate = feed["candidates"][0]
            saved = await track(client, candidate)
            assert (
                await client.post(
                    url(candidate), json=edit(candidate, field="case_width_mm", value="36.0")
                )
            ).status_code == 201
            harness.clock.advance(hours=0.1)
            _, feed = await capture(harness, client, priced_report(harness, "68"))
            assert feed["candidates"][0]["public_delivered_total"]["amount"] == "70.10"
            intent = await get(client, f"/api/discovery/tracking/{saved['id']}")
            assert intent["assessment"]["state"] == "above_target", intent["assessment"]
            assert intent["intended_values"]["case_width_mm"] == "36.0"
            assert harness.deliveries == harness.blocked_edges == []


if __name__ == "__main__":
    asyncio.run(globals()[sys.argv[1]]())
