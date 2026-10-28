"""Real depiction bytes through the guarded buyer API and normal execution."""

import asyncio
import hashlib

from .harness import MonitoringHarness
from .watch_workflow import candidates, cost_edges, seed
from .workflows import get


async def verify():
    with MonitoringHarness() as harness:
        from .watch_images import ASSETS, install_images

        install_images(harness.application.app)
        async with harness.session() as (client, scheduler):
            feed = await seed(harness, client)
            by = candidates(feed)
            image = by["casio"]["image"]
            assert image["kind"] == "photo"
            assert image["source_listing_id"] == "casio"
            assert "CASIO COMPUTER CO., LTD." in image["attribution"]
            assert by["casio"]["public_delivered_total"]["amount"] is None
            assert not by["casio"]["alert_eligible"]
            assert all(
                by[key]["image"]["kind"] == "original_placeholder"
                for key in ("militado", "addies", "san", "merkur")
            )
            manifest = await get(client, "/api/offline-watch-images")
            assert manifest["fixture"] == "ticket12-private-images-v1"
            assert len(manifest["assets"]) == 2
            for asset in ASSETS:
                response = await client.get(asset["local_url"])
                assert response.status_code == 200
                assert hashlib.sha256(response.content).hexdigest() == asset["sha256"]
                assert response.headers["content-type"] == asset["media_type"]
                assert response.headers["cache-control"] == "no-store"
            assert (
                await client.get("/api/offline-watch-images/not-registered.png")
            ).status_code == 404
            assert (
                await client.get("/api/offline-watch-images/%2e%2e%2fmanifest.json")
            ).status_code == 404
            await cost_edges(harness, client)
            assert (
                candidates(await get(client, "/api/discovery/watches"))["casio"]["image"] == image
            )
            assert scheduler.list_watches() == []
            assert harness.deliveries == harness.blocked_edges == []
        async with harness.session() as (client, _):
            assert (
                candidates(await get(client, "/api/discovery/watches"))["casio"]["image"] == image
            )


if __name__ == "__main__":
    asyncio.run(verify())
