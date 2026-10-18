"""LangChain tool wrappers over BookingService matching TECHNICAL_DESIGN.md §12.2."""

from typing import Any, Dict
from langchain_core.tools import tool

from app.booking.service import get_booking_service


@tool
def list_available_slots(limit: int = 3) -> Dict[str, Any]:
    """List currently available appointment slots for booking a performance review.
    
    Args:
        limit: Maximum number of slots to return (1-10, default 3).
        
    Returns:
        Dict containing available slots list, total count, and timezone.
    """
    svc = get_booking_service()
    clamped_limit = max(1, min(limit, 10))
    slots = svc.get_available_slots(limit=clamped_limit)
    return {
        "slots": slots,
        "total_available": svc.get_total_available_count(),
        "timezone": svc.timezone,
    }


@tool
async def create_booking(full_name: str, email: str, slot_id: str) -> Dict[str, Any]:
    """Book a performance review appointment for an attendee with validated details.
    
    Args:
        full_name: Attendee's validated first and last name.
        email: Attendee's validated email address.
        slot_id: Unique slot ID (e.g., slot-20261019-1500).
        
    Returns:
        Dict with booking confirmation details or failure reason code.
    """
    svc = get_booking_service()
    return await svc.create_booking(
        full_name=full_name,
        email=email,
        slot_id=slot_id,
    )
