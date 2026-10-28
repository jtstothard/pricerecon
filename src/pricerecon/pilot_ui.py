"""Existing discovery/product UI, read-only, no application startup/scheduler."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

DIST = Path(__file__).resolve().parents[2] / "frontend/dist"


def create_ui(*, deadline: float | None = None) -> FastAPI:
    from pricerecon.api.discovery import router

    if not (DIST / "index.html").is_file():
        raise RuntimeError("pilot_frontend_build_required")
    deadline = deadline or time.monotonic() + 1200
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    # Reuse only ordinary reads. No mutation, acquisition, scheduler, exports,
    # notifications or production startup routes are mounted.
    from fastapi import APIRouter

    reads = APIRouter()
    reads.routes.extend(
        route for route in router.routes if getattr(route, "methods", set()) == {"GET"}
    )
    app.include_router(reads, prefix="/api")

    @app.middleware("http")
    async def private_session(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if time.monotonic() >= deadline:
            return Response(status_code=410, headers={"Cache-Control": "no-store"})
        if request.headers.get("host") not in {"127.0.0.1", "127.0.0.1:8878"}:
            return Response(status_code=403)
        if request.method != "GET" or request.headers.get("origin") not in {
            None,
            "http://127.0.0.1:8878",
        }:
            return Response(status_code=403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Clear-Site-Data"] = '"cache", "storage"'
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'none'; connect-src 'self'; "
            "style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; object-src 'none'"
        )
        return response

    @app.get("/api/pilot/session")
    async def session() -> dict[str, float]:
        return {"remaining_seconds": max(0, deadline - time.monotonic())}

    @app.get("/pilot-session.js")
    async def expiry_script() -> Response:
        # Clear the page on deadline or lost server, including a disconnected
        # session. Never leave merchant records presented as fresh after stop.
        return Response(
            "let expires=0; async function check(){try{"
            "const r=await fetch('/api/pilot/session',{cache:'no-store'});"
            "if(!r.ok)throw Error();const s=await r.json();"
            "if(!expires)expires=Date.now()+s.remaining_seconds*1000;"
            "if(Date.now()>=expires)throw Error();"
            "}catch{location.replace('about:blank')}};check();setInterval(check,1000);",
            media_type="text/javascript",
        )

    @app.get("/api/watches")
    async def watches() -> dict[str, object]:
        return {"items": [], "total": 0, "page": 1, "page_size": 100}

    @app.get("/api/sources")
    async def sources() -> list[object]:
        return []

    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/api/{path:path}")
    async def unavailable(path: str) -> Response:
        return JSONResponse({"detail": "Unavailable in one-off pilot"}, status_code=404)

    @app.get("/{path:path}")
    async def frontend(path: str) -> Response:
        return HTMLResponse(
            (DIST / "index.html")
            .read_text()
            .replace("<head>", '<head><script src="/pilot-session.js"></script>')
        )

    return app


async def check_ui(app: FastAPI) -> None:
    """Offline integration proof through the same read-only HTTP application."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1"
    ) as client:
        feed = await client.get("/api/discovery/watches")
        assert feed.status_code == 200
        assert len(feed.json()["candidates"]) == 2
        assert all(c["identity_state"] != "supported" for c in feed.json()["candidates"])
        assert (await client.get("/discover")).status_code == 200
        assert (await client.get("/discover/product/fixture")).status_code == 200
        assert (await client.put("/api/discovery/watches/preferences", json={})).status_code == 403
        assert (await client.get("/api/exports")).status_code == 404
        assert (
            await client.get("/api/discovery/watches", headers={"Host": "evil.example"})
        ).status_code == 403
        assert feed.headers["cache-control"].startswith("no-store")


async def serve_ui(app: FastAPI, port: int, seconds: float) -> None:
    import uvicorn

    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            loop="asyncio",
            lifespan="off",
            access_log=False,
            log_config=None,
        )
    )

    async def stop() -> None:
        await asyncio.sleep(seconds)
        server.should_exit = True

    timer = asyncio.create_task(stop())
    try:
        await server.serve()
    finally:
        timer.cancel()
        await asyncio.gather(timer, return_exceptions=True)
