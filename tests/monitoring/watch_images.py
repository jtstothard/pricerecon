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


REMOTE_REFERENCES = {
    "addies": {
        "url": "https://www.addiesdivewatches.com/cdn/shop/files/AD2066-green_600x.jpg?v=1776245650",
        "source_context_url": "https://www.addiesdivewatches.com/products/addiesdive-36mm-luxury-vh31-quartz-watch-ad2066?variant=44195491578021",
        "attribution": "ADDIESDIVE manufacturer product photography",
        "configuration_note": "AD2066 Mint Green / VH31 manufacturer reference; merchant selection and delivered cost independently unverified.",
    },
    "militado": {
        "url": "https://www.militadowatch.com/cdn/shop/files/1_eea45bf9-f2de-43c1-b41e-78eaccbcb327.jpg?v=1773631826&width=800",
        "source_context_url": "https://www.militadowatch.com/products/militado-vh31-vintage-military-watch-ml05-blue-dial",
        "attribution": "Militado manufacturer product photography",
        "configuration_note": "Original ML05 blue VH31 reference; ML05B Miyota target/configuration unresolved. These are not interchangeable.",
    },
    "san": {
        "url": "https://images.squarespace-cdn.com/content/v1/5c9cb86ec46f6d68c6b63267/900e9538-ee8c-461b-bd02-ed7c41712017/san-martin-new-gada-watch.jpg?format=1500w",
        "source_context_url": "https://www.benswatchclub.com/blog/san-martin-jian-zhan-review",
        "attribution": "Ben’s Watch Club — San Martin Jian Zhan review photography",
        "configuration_note": "39mm blue SN0144-GX / Miyota 9015 review reference. Buyer target size/dial/revision unresolved; not the 42mm Green FKM offer.",
    },
}


def remote_depiction(key):
    reference = REMOTE_REFERENCES.get(key)
    if reference is None:
        return None
    return {
        **reference,
        "kind": "remote_reference",
        "source_listing_id": key,
        "depicts_exact_watch": False,
        "provenance": "Original public source URL displayed directly by user approval for private walkthrough; no image licence asserted. Not price or configuration qualification evidence.",
    }
