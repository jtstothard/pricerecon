"""FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from pricerecon.api.health import router as health_router
from pricerecon.config import get_settings
from pricerecon.db.schema import init_db


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    init_db()
    yield
    # Shutdown
    pass


app = FastAPI(title="PriceRecon", version="0.1.0", lifespan=lifespan)

# Include routers
app.include_router(health_router, prefix="/api", tags=["health"])