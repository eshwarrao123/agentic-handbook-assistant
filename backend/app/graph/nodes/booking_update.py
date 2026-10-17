"""Node: booking_update (TECHNICAL_DESIGN §6, Node 3).

TEMPORARY DEVELOPMENT IMPLEMENTATION:
Applies and validates updates to structured booking state according to the state machine.
Full slot inventory service and strict email/name validation functions are added in Phase 5.
"""

from typing import Any, Dict
from app.graph.state import AgentState, reset_booking_update


def booking_update(state: AgentState) -> Dict[str, Any]:
    """Execute booking_update node."""
    booking = dict(state.get("booking") or {})
    status = booking.get("status", "none")
    reply_parts = list(state.get("reply_parts") or [])
    visited = list(state.get("nodes_visited") or []) + ["booking_update"]

    cancel_requested = state.get("cancel_requested", False)
    booking_requested = state.get("booking_requested", False)
    name_candidate = state.get("name_candidate")
    email_candidate = state.get("email_candidate")
    slot_text = state.get("slot_text")

    booking_update_dict: Dict[str, Any] = {}

    # 1. Handle cancellation
    if cancel_requested:
        if status in ("collecting", "awaiting_slot"):
            booking_update_dict = reset_booking_update(status="cancelled")
            reply_parts.append("Okay, I've cancelled that booking request.")
            return {
                "booking": booking_update_dict,
                "reply_parts": reply_parts,
                "nodes_visited": visited,
            }
        else:
            reply_parts.append("There's no booking in progress to cancel.")
            return {
                "reply_parts": reply_parts,
                "nodes_visited": visited,
            }

    # 2. Handle starting a new booking
    if booking_requested and status in ("none", "cancelled", "confirmed"):
        booking_update_dict["status"] = "collecting"
        booking_update_dict["service_type"] = "performance_review"
        status = "collecting"

    # 3. Apply attendee name and email if booking is active
    if status in ("collecting", "awaiting_slot"):
        if name_candidate:
            booking_update_dict["full_name"] = name_candidate
            booking["full_name"] = name_candidate
        if email_candidate:
            booking_update_dict["email"] = email_candidate.lower()
            booking["email"] = email_candidate.lower()

        # 4. Advance status if both fields are populated
        if booking.get("full_name") and booking.get("email"):
            booking_update_dict["status"] = "awaiting_slot"
            status = "awaiting_slot"

    # 5. Handle slot selection if awaiting slot
    if status == "awaiting_slot" and slot_text:
        # Development placeholder: map option selection to mock slot ID
        booking_update_dict["selected_slot_id"] = "slot-20261019-1500"

    updates: Dict[str, Any] = {
        "nodes_visited": visited,
    }
    if booking_update_dict:
        updates["booking"] = booking_update_dict
    if reply_parts:
        updates["reply_parts"] = reply_parts

    return updates
