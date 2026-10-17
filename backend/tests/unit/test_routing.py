"""Unit tests for LangGraph routing functions (UT-014, UT-015, UT-016)."""

from app.graph.routing import (
    booking_active,
    booking_step_target,
    route_after_analysis,
    route_after_booking_update,
    route_resume_booking,
)


def test_route_after_analysis_table():
    """UT-014: route_after_analysis table-driven test."""
    # Booking only -> booking_update
    assert route_after_analysis({"intents": ["booking"]}) == "booking_update"

    # FAQ only -> faq_rag
    assert route_after_analysis({"intents": ["faq"]}) == "faq_rag"

    # Interleaved booking + FAQ -> booking_update (booking processed first)
    assert route_after_analysis({"intents": ["booking", "faq"]}) == "booking_update"
    assert route_after_analysis({"intents": ["faq", "booking"]}) == "booking_update"

    # Neither -> fallback_reply
    assert route_after_analysis({"intents": []}) == "fallback_reply"
    assert route_after_analysis({}) == "fallback_reply"


def test_booking_step_target_table():
    """UT-015: booking_step_target table-driven test."""
    # Inactive bookings always target compose_response
    assert booking_step_target({"booking": {"status": "none"}}) == "compose_response"
    assert booking_step_target({"booking": {"status": "confirmed"}}) == "compose_response"
    assert booking_step_target({"booking": {"status": "cancelled"}}) == "compose_response"
    assert booking_step_target({}) == "compose_response"

    # Active booking with missing name
    assert booking_step_target({
        "booking": {"status": "collecting", "full_name": None, "email": "alex@example.com"}
    }) == "ask_missing_info"

    # Active booking with missing email
    assert booking_step_target({
        "booking": {"status": "collecting", "full_name": "Alex Chen", "email": None}
    }) == "ask_missing_info"

    # Active booking with both details present but no slot selected yet -> offer_slots
    assert booking_step_target({
        "booking": {"status": "awaiting_slot", "full_name": "Alex Chen", "email": "alex@example.com", "selected_slot_id": None}
    }) == "offer_slots"

    # Active booking with a selected slot -> confirm_booking
    assert booking_step_target({
        "booking": {"status": "awaiting_slot", "full_name": "Alex Chen", "email": "alex@example.com", "selected_slot_id": "slot-123"}
    }) == "confirm_booking"


def test_route_after_booking_update():
    """UT-016: route_after_booking_update routes to faq_rag if interleaved, else step target."""
    # Interleaved turn with FAQ -> routes to faq_rag
    state_interleaved = {
        "intents": ["booking", "faq"],
        "booking": {"status": "awaiting_slot", "full_name": "Alex Chen", "email": "alex@example.com"},
    }
    assert route_after_booking_update(state_interleaved) == "faq_rag"

    # Booking only -> routes to step node (offer_slots)
    state_booking_only = {
        "intents": ["booking"],
        "booking": {"status": "awaiting_slot", "full_name": "Alex Chen", "email": "alex@example.com"},
    }
    assert route_after_booking_update(state_booking_only) == "offer_slots"


def test_route_resume_booking():
    """UT-016: route_resume_booking resumes booking if active, otherwise compose_response."""
    # Active booking awaiting slot resumes to offer_slots
    active_state = {
        "booking": {"status": "awaiting_slot", "full_name": "Alex Chen", "email": "alex@example.com"}
    }
    assert route_resume_booking(active_state) == "offer_slots"

    # Inactive booking resumes to compose_response
    inactive_state = {"booking": {"status": "none"}}
    assert route_resume_booking(inactive_state) == "compose_response"


def test_booking_active_helper():
    """Verify booking_active returns True only for collecting and awaiting_slot."""
    assert booking_active({"booking": {"status": "collecting"}}) is True
    assert booking_active({"booking": {"status": "awaiting_slot"}}) is True
    assert booking_active({"booking": {"status": "none"}}) is False
    assert booking_active({"booking": {"status": "confirmed"}}) is False
    assert booking_active({"booking": {"status": "cancelled"}}) is False
    assert booking_active({}) is False
