"""Read-only lead feed. Collection is deliberately not an HTTP action."""

from fastapi import APIRouter, HTTPException

from pricerecon.db.discovery import (
    PreferenceConflict,
    get_cost_history,
    get_feed,
    get_preferences,
    save_preferences,
)
from pricerecon.models.costs import CostHistory
from pricerecon.models.discovery import DiscoveryFeed, PreferenceProfile, PreferenceUpdate
from pricerecon.models.history import ObservationHistory

router = APIRouter()


@router.get("/discovery/watches", response_model=DiscoveryFeed)
async def discovery_feed() -> DiscoveryFeed:
    return get_feed()


@router.get("/discovery/watches/preferences", response_model=PreferenceProfile)
async def discovery_preferences() -> PreferenceProfile:
    return get_preferences()


@router.put("/discovery/watches/preferences", response_model=PreferenceProfile)
async def update_discovery_preferences(update: PreferenceUpdate) -> PreferenceProfile:
    try:
        return save_preferences(update)
    except PreferenceConflict as exc:
        raise HTTPException(
            status_code=409, detail="Preferences changed; reload before saving."
        ) from exc


@router.get("/discovery/offers/{offer_id}/costs", response_model=CostHistory)
async def discovery_cost_history(offer_id: str) -> CostHistory:
    return get_cost_history(offer_id)


@router.get("/discovery/candidates/{candidate_id}/history", response_model=ObservationHistory)
async def discovery_observation_history(candidate_id: str) -> ObservationHistory:
    from pricerecon.db.history import get_history

    history = get_history(candidate_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Candidate history not found")
    return history
