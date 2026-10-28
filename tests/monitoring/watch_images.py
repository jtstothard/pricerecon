"""Private, non-commercial buyer walkthrough assets. Never mounted in production.

Original HTTPS depiction evidence still crosses the normal execution seam.
The opt-in UI resolves only registered originals to these local immutable bytes.
"""

import hashlib
import json
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import Response

ASSET_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "watch-images"
MANIFEST = json.loads((ASSET_ROOT / "manifest.json").read_text())
ASSETS = MANIFEST["assets"]


def depiction():
    asset = ASSETS[0]
    return {
        "kind": "photo",
        "url": asset["source_url"],
        "attribution": MANIFEST["attribution"],
        "provenance": "Official Casio Europe product image; retained unchanged for a private personal walkthrough. Photo identity is independent of all synthetic price/selection evidence.",
        "permission_reference": MANIFEST["terms_url"],
        "identity_reference": MANIFEST["product_url"],
        "source_listing_id": "casio",
        "depicts_exact_watch": True,
    }


def install_images(app: FastAPI):
    router = APIRouter()
    # Read/verify before serving. No caller-supplied file paths, fetch or proxy.
    retained = {}
    for asset in ASSETS:
        content = (ASSET_ROOT / asset["filename"]).read_bytes()
        if hashlib.sha256(content).hexdigest() != asset["sha256"]:
            raise RuntimeError("Walkthrough image differs from its rights manifest")
        retained[asset["local_url"].rsplit("/", 1)[1]] = (content, asset["media_type"])

    @router.get("/api/offline-watch-images")
    async def manifest():
        return {
            "fixture": "ticket12-private-images-v1",
            "assets": ASSETS,
            "attribution": MANIFEST["attribution"],
            "scope": MANIFEST["use_scope"],
        }

    @router.get("/api/offline-watch-images/{name:path}")
    async def image(name: str):
        if name not in retained:
            raise HTTPException(404, "Unregistered walkthrough asset")
        content, media_type = retained[name]
        return Response(content, media_type=media_type, headers={"Cache-Control": "no-store"})

    app.router.routes[0:0] = router.routes
