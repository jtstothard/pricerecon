"""Human identity edits never provide acquisition, price or stock evidence."""

from fastapi import APIRouter, HTTPException

from pricerecon.db.corrections import (
    CorrectionConflict,
    CorrectionMissing,
    get_corrections,
    save_correction,
)
from pricerecon.db.tracking import TrackingConflict
from pricerecon.models.corrections import CorrectionHistory, CorrectionWrite

router = APIRouter()
PATH = "/discovery/candidates/{candidate_id}/corrections/{configuration_id}"


@router.get(PATH, response_model=CorrectionHistory)
async def correction_history(candidate_id: str, configuration_id: str) -> CorrectionHistory:
    try:
        return get_corrections(candidate_id, configuration_id)
    except CorrectionMissing as exc:
        raise HTTPException(404, "Retained configuration not found on this candidate.") from exc


@router.post(PATH, response_model=CorrectionHistory, status_code=201)
async def correct_identity(
    candidate_id: str,
    configuration_id: str,
    request: CorrectionWrite,
) -> CorrectionHistory:
    try:
        return save_correction(candidate_id, configuration_id, request)
    except CorrectionMissing as exc:
        raise HTTPException(404, "Retained configuration not found on this candidate.") from exc
    except CorrectionConflict as exc:
        raise HTTPException(409, "Identity or correction changed; reload before saving.") from exc
    except TrackingConflict as exc:
        raise HTTPException(
            409,
            "Delivery is in flight or interrupted; reconcile it before correcting identity. No correction was saved.",
        ) from exc
