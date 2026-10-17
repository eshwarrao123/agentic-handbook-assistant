"""Unit tests for LangGraph state schemas and merge_booking reducer (UT-003, UT-004, UT-005)."""

import pytest
from app.graph.state import (
    default_booking_state,
    merge_booking,
    reset_booking_update,
)


def test_merge_booking_preserves_unmodified_fields():
    """UT-003: merge_booking retains existing fields when given a partial update."""
    current = default_booking_state()
    current["status"] = "collecting"
    current["full_name"] = "Alex Chen"
    current["email"] = "alex.chen@example.com"

    update = {"status": "awaiting_slot"}
    result = merge_booking(current, update)

    assert result["status"] == "awaiting_slot"
    assert result["full_name"] == "Alex Chen"
    assert result["email"] == "alex.chen@example.com"
    assert result["offered_slots"] == []


def test_merge_booking_rejects_unknown_fields():
    """UT-004: merge_booking raises KeyError on unknown fields, preventing typo corruption."""
    current = default_booking_state()
    with pytest.raises(KeyError) as exc_info:
        merge_booking(current, {"nme": "Alex"})
    assert "Unknown booking field: 'nme'" in str(exc_info.value)


def test_merge_booking_none_current_uses_default():
    """UT-005: merge_booking(None, update) treats missing current as default booking state."""
    update = {"status": "collecting", "full_name": "Alex Chen"}
    result = merge_booking(None, update)

    assert result["status"] == "collecting"
    assert result["full_name"] == "Alex Chen"
    assert result["email"] is None
    assert result["offered_slots"] == []
    assert result["booking_reference"] is None


def test_reset_booking_update_clears_all_fields_explicitly():
    """Verify reset_booking_update clears fields while applying new status."""
    reset = reset_booking_update(status="cancelled")
    assert reset["status"] == "cancelled"
    assert reset["full_name"] is None
    assert reset["email"] is None
    assert reset["offered_slots"] == []
    assert reset["booking_reference"] is None
