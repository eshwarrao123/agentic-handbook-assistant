"""Nodes: ask_missing_info, offer_slots, confirm_booking (TECHNICAL_DESIGN §6, Nodes 6, 7, 8).

Authoritative step nodes for gathering details, listing available slots from BookingService,
and confirming simulated performance review bookings.
Invariants:
1. Availability and confirmations are strictly validated in Python, never invented by LLM.
2. Partial dictionary updates preserve all existing state fields.
"""

from typing import Any, Dict
from app.booking.service import get_booking_service
from app.graph.state import AgentState


def ask_missing_info(state: AgentState) -> Dict[str, Any]:
    """Execute ask_missing_info node (Node 6).
    
    Prompts user specifically for missing name, missing email, or both.
    """
    booking = state.get("booking") or {}
    full_name = booking.get("full_name")
    email = booking.get("email")

    reply_parts = list(state.get("reply_parts") or [])
    visited = list(state.get("nodes_visited") or []) + ["ask_missing_info"]

    # If booking_update already added a validation message, keep that specific error message
    if any("valid email" in p.lower() or "valid name" in p.lower() or "at least" in p.lower() for p in reply_parts):
        return {
            "reply_parts": reply_parts,
            "nodes_visited": visited,
        }

    if not full_name and not email:
        prompt = (
            "I'd be happy to help schedule a Performance Review session. "
            "May I have your full name and email address?"
        )
        if prompt not in reply_parts:
            reply_parts.append(prompt)
    elif not full_name:
        prompt = "Could you please provide your full name for the booking?"
        if prompt not in reply_parts:
            reply_parts.append(prompt)
    elif not email:
        first_name = full_name.split()[0] if full_name else "there"
        prompt = f"Thanks, {first_name}. What is your email address?"
        if prompt not in reply_parts:
            reply_parts.append(prompt)

    return {
        "reply_parts": reply_parts,
        "nodes_visited": visited,
    }


def offer_slots(state: AgentState) -> Dict[str, Any]:
    """Execute offer_slots node (Node 7).
    
    Pulls actual available slots from BookingService and formats the numbered slot list.
    """
    booking = state.get("booking") or {}
    full_name = booking.get("full_name") or ""
    first_name = full_name.split()[0] if full_name else ""

    reply_parts = list(state.get("reply_parts") or [])
    visited = list(state.get("nodes_visited") or []) + ["offer_slots"]

    svc = get_booking_service()
    available_slots = svc.get_available_slots(limit=3)

    if not available_slots:
        reply_parts.append(
            "There are currently no available slots for scheduling. Please check back later."
        )
        return {
            "reply_parts": reply_parts,
            "nodes_visited": visited,
        }

    has_preceding_reply = bool(reply_parts)
    prefix = (
        f"Returning to your booking, {first_name} — here are the available slots:\n"
        if has_preceding_reply and first_name
        else "Here are the available slots for your Performance Review session:\n"
    )

    slot_list_str = "\n".join(f"{i + 1}) {s['label']}" for i, s in enumerate(available_slots))
    prompt = (
        f"{prefix}{slot_list_str}\n\n"
        "Which one works best? You can reply with the option number (e.g. '1', '2') or the day and time."
    )
    reply_parts.append(prompt)

    return {
        "booking": {"offered_slots": available_slots},
        "reply_parts": reply_parts,
        "nodes_visited": visited,
    }


async def confirm_booking(state: AgentState) -> Dict[str, Any]:
    """Execute confirm_booking node (Node 8).
    
    Calls BookingService to reserve the slot and generate an authoritative #REV-NNNN reference.
    """
    booking = state.get("booking") or {}
    full_name = booking.get("full_name") or ""
    email = booking.get("email") or ""
    selected_slot_id = booking.get("selected_slot_id")

    reply_parts = list(state.get("reply_parts") or [])
    visited = list(state.get("nodes_visited") or []) + ["confirm_booking"]

    svc = get_booking_service()

    if not selected_slot_id:
        reply_parts.append("No slot was selected. Please choose an available slot from the list.")
        return {
            "reply_parts": reply_parts,
            "nodes_visited": visited,
        }

    # Authoritative reservation through BookingService
    result = await svc.create_booking(
        full_name=full_name,
        email=email,
        slot_id=selected_slot_id,
    )

    if result["ok"]:
        confirmed_slot = result["slot"]
        reference = result["reference"]
        confirmation_text = (
            f"Confirmed! Your Performance Review is scheduled for {confirmed_slot['label']} for {full_name}.\n"
            f"Reference ID: {reference}.\n"
            "(This is a simulated booking; no real calendar entry was created.)"
        )
        reply_parts.append(confirmation_text)

        booking_update_dict = {
            "status": "confirmed",
            "booking_reference": reference,
            "confirmed_slot": confirmed_slot,
            "selected_slot_id": None,
            "offered_slots": [],
        }

        return {
            "booking": booking_update_dict,
            "reply_parts": reply_parts,
            "nodes_visited": visited,
        }
    else:
        # Slot failed validation or was already taken
        reply_parts.append(f"{result['message']}")
        booking_update_dict = {
            "status": "awaiting_slot",
            "selected_slot_id": None,
        }
        return {
            "booking": booking_update_dict,
            "reply_parts": reply_parts,
            "nodes_visited": visited,
        }
