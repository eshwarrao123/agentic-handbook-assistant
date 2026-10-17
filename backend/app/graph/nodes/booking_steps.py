"""Nodes: ask_missing_info, offer_slots, confirm_booking (TECHNICAL_DESIGN §6, Nodes 6, 7, 8).

TEMPORARY DEVELOPMENT IMPLEMENTATION:
Provides structured step logic for gathering details, offering slots, and confirming.
Full deterministic slot resolution and tool integration are added in Phase 5.
"""

from typing import Any, Dict
from app.graph.state import AgentState


def ask_missing_info(state: AgentState) -> Dict[str, Any]:
    """Execute ask_missing_info node (Node 6)."""
    booking = state.get("booking") or {}
    full_name = booking.get("full_name")
    email = booking.get("email")

    reply_parts = list(state.get("reply_parts") or [])
    visited = list(state.get("nodes_visited") or []) + ["ask_missing_info"]

    if not full_name and not email:
        reply_parts.append(
            "I'd be happy to help schedule a Performance Review session. "
            "May I have your full name and email address?"
        )
    elif not full_name:
        reply_parts.append("Could you please provide your full name for the booking?")
    elif not email:
        first_name = full_name.split()[0] if full_name else "there"
        reply_parts.append(f"Thanks, {first_name}. What is your email address?")

    return {
        "reply_parts": reply_parts,
        "nodes_visited": visited,
    }


def offer_slots(state: AgentState) -> Dict[str, Any]:
    """Execute offer_slots node (Node 7)."""
    booking = state.get("booking") or {}
    full_name = booking.get("full_name") or ""
    first_name = full_name.split()[0] if full_name else ""

    reply_parts = list(state.get("reply_parts") or [])
    visited = list(state.get("nodes_visited") or []) + ["offer_slots"]

    sample_slots = [
        {"slot_id": "slot-20261019-1030", "start": "2026-10-19T10:30:00+05:30", "label": "Mon, 19 Oct 2026, 10:30 AM IST"},
        {"slot_id": "slot-20261019-1500", "start": "2026-10-19T15:00:00+05:30", "label": "Mon, 19 Oct 2026, 3:00 PM IST"},
        {"slot_id": "slot-20261020-1030", "start": "2026-10-20T10:30:00+05:30", "label": "Tue, 20 Oct 2026, 10:30 AM IST"},
    ]

    has_preceding_reply = bool(reply_parts)
    prefix = (
        f"Returning to your booking, {first_name} — here are the available slots:\n"
        if has_preceding_reply and first_name
        else "Here are the available slots for your Performance Review session:\n"
    )

    slot_list_str = "\n".join(f"{i + 1}) {s['label']}" for i, s in enumerate(sample_slots))
    prompt = f"{prefix}{slot_list_str}\nWhich one works best? You can reply with the option number or the day and time."
    reply_parts.append(prompt)

    return {
        "booking": {"offered_slots": sample_slots},
        "reply_parts": reply_parts,
        "nodes_visited": visited,
    }


def confirm_booking(state: AgentState) -> Dict[str, Any]:
    """Execute confirm_booking node (Node 8)."""
    booking = state.get("booking") or {}
    full_name = booking.get("full_name") or "Alex Chen"
    email = booking.get("email") or "alex.chen@example.com"

    reply_parts = list(state.get("reply_parts") or [])
    visited = list(state.get("nodes_visited") or []) + ["confirm_booking"]

    confirmed_slot = {
        "slot_id": "slot-20261019-1500",
        "start": "2026-10-19T15:00:00+05:30",
        "label": "Mon, 19 Oct 2026, 3:00 PM IST",
    }
    reference_id = "#REV-4081"

    confirmation_text = (
        f"Confirmed! Your Performance Review is scheduled for {confirmed_slot['label']} for {full_name}.\n"
        f"Reference ID: {reference_id}.\n"
        "(This is a simulated booking; no real calendar entry was created.)"
    )
    reply_parts.append(confirmation_text)

    booking_update_dict = {
        "status": "confirmed",
        "booking_reference": reference_id,
        "confirmed_slot": confirmed_slot,
        "selected_slot_id": None,
        "offered_slots": [],
    }

    return {
        "booking": booking_update_dict,
        "reply_parts": reply_parts,
        "nodes_visited": visited,
    }
