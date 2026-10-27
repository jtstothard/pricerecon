"""Read-only lead feed. Collection is deliberately not an HTTP action."""

from fastapi import APIRouter, HTTPException

from pricerecon.db.discovery import PreferenceConflict, get_feed, get_preferences, save_preferences
from pricerecon.models.discovery import DiscoveryFeed, PreferenceProfile, PreferenceUpdate

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
