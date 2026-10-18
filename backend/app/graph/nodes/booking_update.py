"""Node: booking_update (TECHNICAL_DESIGN §6, Node 3).

Applies deterministic validation and state machine transitions to structured booking state.
Validation boundaries and state machine rules (TECHNICAL_DESIGN §12.3 & §12.4):
1. Invariant: Partial dictionary updates only; never clobbers untouched fields.
2. Name & email validated via strict Python validators (never trusting LLM for validation).
3. Slot selection resolved via deterministic resolve_slot rule hierarchy.
"""

from typing import Any, Dict
from app.booking.service import get_booking_service
from app.booking.slot_resolver import resolve_slot
from app.booking.validation import validate_email, validate_full_name
from app.graph.state import AgentState, reset_booking_update


def booking_update(state: AgentState) -> Dict[str, Any]:
    """Execute booking_update state machine node."""
    booking = dict(state.get("booking") or {})
    status = booking.get("status", "none")
    reply_parts = list(state.get("reply_parts") or [])
    visited = list(state.get("nodes_visited") or []) + ["booking_update"]

    cancel_requested = state.get("cancel_requested", False)
    booking_requested = state.get("booking_requested", False)
    name_candidate = state.get("name_candidate")
    email_candidate = state.get("email_candidate")
    slot_text = state.get("slot_text")
    user_text = state.get("user_text", "")

    booking_update_dict: Dict[str, Any] = {}
    svc = get_booking_service()

    # 1. Handle explicit cancellation
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

    # 3. Apply attendee name and email validation if booking is active
    if status in ("collecting", "awaiting_slot"):
        if name_candidate:
            is_valid_name, clean_name_or_err = validate_full_name(name_candidate)
            if is_valid_name:
                booking_update_dict["full_name"] = clean_name_or_err
                booking["full_name"] = clean_name_or_err
            elif not booking.get("full_name"):
                reply_parts.append(clean_name_or_err)

        if email_candidate:
            is_valid_email, clean_email_or_err = validate_email(email_candidate)
            if is_valid_email:
                booking_update_dict["email"] = clean_email_or_err
                booking["email"] = clean_email_or_err
            elif not booking.get("email"):
                reply_parts.append("That doesn't look like a valid email address. Please provide a valid email (e.g. name@example.com).")

        # Advance status to awaiting_slot once both name and email are populated
        if booking.get("full_name") and booking.get("email"):
            if status != "awaiting_slot":
                booking_update_dict["status"] = "awaiting_slot"
                status = "awaiting_slot"

    # 4. Handle slot selection if awaiting slot
    if status == "awaiting_slot":
        selection_input = slot_text or (user_text if not booking_requested and not state.get("faq_question") else None)
        if selection_input:
            offered = booking.get("offered_slots") or svc.get_available_slots(limit=3)
            available = svc.get_available_slots()
            resolution = resolve_slot(selection_input, offered_slots=offered, available_inventory=available)

            if resolution["result"] == "MATCH":
                slot = resolution["slot"]
                booking_update_dict["selected_slot_id"] = slot["slot_id"]
            elif resolution["result"] == "OUT_OF_RANGE":
                reply_parts.append(
                    f"Option {selection_input} is outside the offered options (1 to {len(offered)}). "
                    "Please choose one of the options listed below or specify an available day and time."
                )
                booking_update_dict["selected_slot_id"] = None
            elif resolution["result"] == "AMBIGUOUS":
                candidates = resolution.get("candidates") or []
                labels = ", ".join(f"'{c['label']}'" for c in candidates[:3])
                reply_parts.append(
                    f"I found multiple matching slots ({labels}). "
                    "Please specify the exact time or reply with the option number."
                )
                booking_update_dict["selected_slot_id"] = None
            elif resolution["result"] == "UNAVAILABLE":
                reply_parts.append(
                    "That slot is no longer available. Please select another slot from the list below."
                )
                booking_update_dict["selected_slot_id"] = None
            elif resolution["result"] == "NO_MATCH" and slot_text:
                reply_parts.append(
                    "I couldn't match that to an available appointment slot. "
                    "Please reply with an option number (e.g. '1', '2') or an available day and time."
                )
                booking_update_dict["selected_slot_id"] = None

    updates: Dict[str, Any] = {
        "nodes_visited": visited,
    }
    if booking_update_dict:
        updates["booking"] = booking_update_dict
    if reply_parts:
        updates["reply_parts"] = reply_parts

    return updates
