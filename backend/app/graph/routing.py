"""Pure routing functions for LangGraph conditional edges matching docs/TECHNICAL_DESIGN.md §7."""

from app.graph.state import AgentState


def booking_active(state: AgentState) -> bool:
    """Return True if a booking is currently in progress (collecting or awaiting_slot)."""
    booking = state.get("booking") or {}
    return booking.get("status") in ("collecting", "awaiting_slot")


def booking_step_target(state: AgentState) -> str:
    """Determine the next booking step node or compose_response if inactive (TECHNICAL_DESIGN §7.1)."""
    if not booking_active(state):
        return "compose_response"

    booking = state.get("booking") or {}
    # If attendee name or email is missing, ask for missing info
    if not booking.get("full_name") or not booking.get("email"):
        return "ask_missing_info"

    # If both name and email are present but no slot has been selected yet, offer slots
    if not booking.get("selected_slot_id"):
        return "offer_slots"

    # If a valid slot has been selected, proceed to confirmation
    return "confirm_booking"


def route_after_analysis(state: AgentState) -> str:
    """Route from analyze_turn based on detected intents (TECHNICAL_DESIGN §7.2, UT-014).
    
    Priority:
    - If booking intent is present (even if FAQ is also present): route to booking_update.
    - If only FAQ intent is present: route to faq_rag.
    - If no intents detected: route to fallback_reply.
    """
    intents = state.get("intents") or []
    if "booking" in intents:
        return "booking_update"
    elif "faq" in intents:
        return "faq_rag"
    else:
        return "fallback_reply"


def route_after_booking_update(state: AgentState) -> str:
    """Route from booking_update (TECHNICAL_DESIGN §7.2, UT-016).
    
    If an interleaved FAQ intent is also present on this turn, route to faq_rag
    first to answer the question before advancing booking steps.
    Otherwise, advance to the appropriate booking step node.
    """
    intents = state.get("intents") or []
    if "faq" in intents:
        return "faq_rag"
    return booking_step_target(state)


def route_resume_booking(state: AgentState) -> str:
    """Resume booking after faq_rag or fallback_reply (TECHNICAL_DESIGN §7.2, UT-016).
    
    Computes resumption from structured booking state, not conversation text.
    If a booking was active, returns the pending step node (ask_missing_info or offer_slots).
    If no booking is active, returns compose_response.
    """
    return booking_step_target(state)
