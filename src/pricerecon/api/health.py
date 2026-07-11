"""Health check endpoint."""

from fastapi import APIRouter

from pricerecon.core.connector_health import list_connector_health
from pricerecon.models import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok", connector_states=list_connector_health())
