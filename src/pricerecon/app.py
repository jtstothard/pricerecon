"""FastAPI application for PriceRecon REST API."""

import json
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pricerecon.api.auth import require_api_key
from pricerecon.api.events import router as events_router
from pricerecon.api.export import router as export_router
from pricerecon.api.health import router as health_router
from pricerecon.api.history import router as history_router
from pricerecon.api.listings import router as listings_router
from pricerecon.api.signals import router as signals_router
from pricerecon.api.sources import router as sources_router
from pricerecon.api.watches import router as watches_router
from pricerecon.config import get_settings
from pricerecon.core.scheduler import scheduler_lifespan
from pricerecon.db.schema import DB_PATH, init_db

settings = get_settings()
frontend_dist = Path(__file__).parent.parent.parent.parent / "frontend" / "dist"
APP_VERSION = "0.1.0"
_app_start_time = datetime.utcnow()


async def load_watches_from_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, config_json FROM watches")
        rows = cursor.fetchall()
        from pricerecon.core.scheduler import get_scheduler

        scheduler = get_scheduler()
        scheduled = 0
        for row in rows:
            watch_id = row["id"]
            config = json.loads(row["config_json"])
            if not config.get("enabled", True):
                continue
            schedule_config = config.get("schedule", {})
            try:
                scheduler.add_watch(
                    watch_id,
                    schedule_config.get("interval", "4h"),
                    schedule_config.get("timezone", "UTC"),
                    schedule_config.get("time_window"),
                )
                scheduled += 1
            except Exception as exc:
                print(f"Failed to schedule watch {watch_id}: {exc}")
        print(f"Loaded {scheduled} watches into scheduler")
    finally:
        conn.close()


async def check_watch(watch_id: int):
    """Scheduler callback: execute a watch and record results."""
    print(f"[scheduler] Executing watch {watch_id}")
    from pricerecon.core.watch_executor import execute_watch

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE watches SET last_check_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), watch_id),
        )
        conn.commit()
    finally:
        conn.close()

    try:
        result = await execute_watch(watch_id)
        events = result.get("events", [])
        notifications = result.get("notifications_sent", 0)
        listings = result.get("listings_found", 0)
        print(
            f"[scheduler] Watch {watch_id} done: "
            f"{listings} listings, {len(events)} events, "
            f"{notifications} notifications"
        )
    except Exception as exc:
        print(f"[scheduler] Watch {watch_id} failed: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    async with scheduler_lifespan() as scheduler:
        scheduler.set_watch_check_function(check_watch)
        await load_watches_from_db()
        yield


app = FastAPI(
    title="PriceRecon API",
    description="Self-hosted price tracking application for search-query-based multi-source monitoring",
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_deps = [Depends(require_api_key)] if settings.api_key else []
app.include_router(health_router, prefix="/api", tags=["Health"], dependencies=api_deps)
app.include_router(watches_router, prefix="/api", tags=["Watches"], dependencies=api_deps)
app.include_router(listings_router, prefix="/api", tags=["Listings"], dependencies=api_deps)
app.include_router(history_router, prefix="/api", tags=["History"], dependencies=api_deps)
app.include_router(events_router, prefix="/api", tags=["Events"], dependencies=api_deps)
app.include_router(sources_router, prefix="/api", tags=["Sources"], dependencies=api_deps)
app.include_router(signals_router, prefix="/api", tags=["Signals"], dependencies=api_deps)
app.include_router(export_router, prefix="/api", tags=["Export"], dependencies=api_deps)

if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        file_path = frontend_dist / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")
else:
    print(f"Warning: Frontend build directory not found at {frontend_dist}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
