"""Exact intent edits never collect, schedule or send notifications."""

from fastapi import APIRouter, HTTPException

from pricerecon.db.tracking import (
    TrackingConflict,
    TrackingMissing,
    create_tracking,
    get_tracking,
    list_deliveries,
    list_tracking,
    resolve_delivery,
    update_tracking,
)
from pricerecon.models.tracking import (
    DeliveryResolution,
    ExactTracking,
    TrackingCreate,
    TrackingDeliveries,
    TrackingList,
    TrackingUpdate,
)

router = APIRouter()


@router.post("/discovery/tracking", response_model=ExactTracking, status_code=201)
async def create_exact_tracking(request: TrackingCreate) -> ExactTracking:
    try:
        return create_tracking(request)
    except TrackingMissing as exc:
        raise HTTPException(404, "Retained configuration not found.") from exc
    except TrackingConflict as exc:
        raise HTTPException(409, "Reload configuration and tracking before saving.") from exc


@router.get("/discovery/tracking", response_model=TrackingList)
async def exact_tracking_list() -> TrackingList:
    return list_tracking()


@router.get("/discovery/tracking/{tracking_id}", response_model=ExactTracking)
async def exact_tracking(tracking_id: int) -> ExactTracking:
    try:
        return get_tracking(tracking_id)
    except TrackingMissing as exc:
        raise HTTPException(404, "Tracking intent not found.") from exc


@router.get("/discovery/tracking/{tracking_id}/deliveries", response_model=TrackingDeliveries)
async def exact_tracking_deliveries(tracking_id: int) -> TrackingDeliveries:
    try:
        return list_deliveries(tracking_id)
    except TrackingMissing as exc:
        raise HTTPException(404, "Tracking intent not found.") from exc


@router.post(
    "/discovery/tracking/{tracking_id}/deliveries/{event_id}/resolve", response_model=ExactTracking
)
async def resolve_exact_delivery(
    tracking_id: int,
    event_id: int,
    request: DeliveryResolution,
) -> ExactTracking:
    try:
        return resolve_delivery(tracking_id, event_id, request)
    except TrackingMissing as exc:
        raise HTTPException(404, "Delivery not found for this intent.") from exc
    except TrackingConflict as exc:
        raise HTTPException(
            409, "Tracking or delivery changed; reload before reconciling."
        ) from exc


@router.put("/discovery/tracking/{tracking_id}", response_model=ExactTracking)
async def edit_exact_tracking(tracking_id: int, request: TrackingUpdate) -> ExactTracking:
    try:
        return update_tracking(tracking_id, request)
    except TrackingMissing as exc:
        raise HTTPException(404, "Tracking intent not found.") from exc
    except TrackingConflict as exc:
        raise HTTPException(
            409, "Tracking changed or delivery needs reconciliation; reload."
        ) from exc
