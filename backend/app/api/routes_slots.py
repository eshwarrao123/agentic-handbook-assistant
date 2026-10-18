"""REST routes for slot listing matching docs/API_CONTRACT.md §5."""

from fastapi import APIRouter, Query

from app.api.schemas import Slot, SlotsResponse
from app.booking.service import get_booking_service

router = APIRouter(tags=["slots"])


@router.get(
    "/slots",
    response_model=SlotsResponse,
    summary="List available appointment slots",
    description="List currently available appointment slots from the deterministic booking service.",
)
async def get_slots(
    limit: int = Query(
        default=10,
        ge=1,
        le=10,
        description="Maximum number of available slots to return (integer between 1 and 10).",
    ),
) -> SlotsResponse:
    """Retrieve available appointment slots (API_CONTRACT §5)."""
    svc = get_booking_service()
    raw_slots = svc.get_available_slots(limit=limit)

    slots = [
        Slot(
            slot_id=s["slot_id"],
            start=s["start"],
            label=s["label"],
        )
        for s in raw_slots
    ]

    return SlotsResponse(
        service_type="performance_review",
        timezone=svc.timezone,
        total_available=svc.get_total_available_count(),
        slots=slots,
    )
