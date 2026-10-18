"""Unit tests for booking validation, slot inventory service, and slot resolver (UT-001, UT-002, UT-010..013)."""

import asyncio
import pytest

from app.booking.service import BookingService
from app.booking.slot_resolver import resolve_slot
from app.booking.validation import validate_email, validate_full_name


# --- Validation Boundary Tests ---

def test_validate_full_name_valid():
    """Valid names with 2+ tokens, letters, hyphens, dots, and Unicode are accepted."""
    assert validate_full_name("Alex Chen")[0] is True
    assert validate_full_name("Mary-Jane Watson")[0] is True
    assert validate_full_name("Dr. Sarah O'Connor")[0] is True
    assert validate_full_name("Zoë Müller")[0] is True
    assert validate_full_name("  John   Doe  ")[1] == "John Doe"


def test_validate_full_name_invalid():
    """Single tokens, numbers, HTML, SQL injections, and empty inputs are rejected."""
    # Single token (missing last name)
    assert validate_full_name("Alex")[0] is False
    # Empty / whitespace
    assert validate_full_name("")[0] is False
    assert validate_full_name("   ")[0] is False
    assert validate_full_name(None)[0] is False
    # Numbers in name
    assert validate_full_name("Alex 123")[0] is False
    # SQL injection attempt
    assert validate_full_name("Robert'); DROP TABLE--")[0] is False
    # HTML script tags
    assert validate_full_name("<b>Alex</b> Chen")[0] is False


def test_validate_email_valid():
    """Valid standard email addresses are accepted and normalized to lowercase."""
    valid, email = validate_email("Alex.Chen@Example.COM")
    assert valid is True
    assert email == "alex.chen@example.com"

    assert validate_email("user+tag@domain.co.in")[0] is True
    assert validate_email("first.last@company.org")[0] is True


def test_validate_email_invalid():
    """Malformed emails, missing @, missing dot, whitespace, and empty inputs are rejected."""
    assert validate_email("")[0] is False
    assert validate_email(None)[0] is False
    assert validate_email("not-an-email")[0] is False
    assert validate_email("user@domain")[0] is False
    assert validate_email("user @domain.com")[0] is False
    assert validate_email("@domain.com")[0] is False
    assert validate_email("user@" * 100)[0] is False


# --- BookingService Inventory Tests ---

def test_slot_inventory_generation():
    """Slot inventory generates 10 slots (5 weekdays x 2 times: 10:30 and 15:00)."""
    svc = BookingService()
    slots = svc.inventory
    assert len(slots) == 10

    # Verify times and slot ID pattern
    slot_ids = [s["slot_id"] for s in slots]
    assert len(set(slot_ids)) == 10
    assert all(s["slot_id"].startswith("slot-202610") for s in slots)
    assert all("10:30 AM" in s["label"] or "3:00 PM" in s["label"] for s in slots)
    assert all("IST" in s["label"] for s in slots)


def test_get_available_slots_and_limit():
    """get_available_slots returns unbooked slots and respects limit."""
    svc = BookingService()
    assert svc.get_total_available_count() == 10

    # Limit = 3
    offered = svc.get_available_slots(limit=3)
    assert len(offered) == 3
    assert svc.get_total_available_count() == 10


@pytest.mark.asyncio
async def test_booking_creation_lifecycle():
    """Booking creation validates details, generates reference #REV-NNNN, and marks slot unavailable."""
    svc = BookingService()
    slots = svc.get_available_slots()
    target_slot_id = slots[0]["slot_id"]

    # 1. Successful booking
    res = await svc.create_booking(
        full_name="Alex Chen",
        email="alex.chen@example.com",
        slot_id=target_slot_id,
    )
    assert res["ok"] is True
    assert res["reference"].startswith("#REV-")
    assert res["slot"]["slot_id"] == target_slot_id
    assert res["full_name"] == "Alex Chen"
    assert res["email"] == "alex.chen@example.com"
    assert res["simulated"] is True

    # Total available decrements to 9
    assert svc.get_total_available_count() == 9
    assert svc.is_slot_available(target_slot_id) is False

    # 2. Duplicate booking attempt on the same slot -> SLOT_UNAVAILABLE
    res_dup = await svc.create_booking(
        full_name="Sarah Smith",
        email="sarah@example.com",
        slot_id=target_slot_id,
    )
    assert res_dup["ok"] is False
    assert res_dup["code"] == "SLOT_UNAVAILABLE"

    # 3. Non-existent slot ID -> SLOT_NOT_FOUND
    res_none = await svc.create_booking(
        full_name="Sarah Smith",
        email="sarah@example.com",
        slot_id="slot-99999999-0000",
    )
    assert res_none["ok"] is False
    assert res_none["code"] == "SLOT_NOT_FOUND"


@pytest.mark.asyncio
async def test_concurrent_booking_locking():
    """Lock prevents two concurrent requests from taking the same slot."""
    svc = BookingService()
    slot_id = svc.get_available_slots()[0]["slot_id"]

    # Launch two concurrent booking requests
    res1, res2 = await asyncio.gather(
        svc.create_booking("User One", "user1@example.com", slot_id),
        svc.create_booking("User Two", "user2@example.com", slot_id),
    )

    # Exactly one succeeded and one failed
    results = [res1["ok"], res2["ok"]]
    assert results.count(True) == 1
    assert results.count(False) == 1
    failed_res = res1 if not res1["ok"] else res2
    assert failed_res["code"] == "SLOT_UNAVAILABLE"


# --- Slot Resolver Tests ---

def test_resolve_slot_option_numbers():
    """Option numbers like '1', 'option 2', '#3' resolve to correct offered slots."""
    svc = BookingService()
    offered = svc.get_available_slots(limit=3)
    available = svc.get_available_slots()

    # Option 1
    r1 = resolve_slot("1", offered, available)
    assert r1["result"] == "MATCH"
    assert r1["slot"]["slot_id"] == offered[0]["slot_id"]

    # Option 2 with prefix
    r2 = resolve_slot("option 2", offered, available)
    assert r2["result"] == "MATCH"
    assert r2["slot"]["slot_id"] == offered[1]["slot_id"]

    # Option 3 with hash
    r3 = resolve_slot("#3", offered, available)
    assert r3["result"] == "MATCH"
    assert r3["slot"]["slot_id"] == offered[2]["slot_id"]


def test_resolve_slot_out_of_range():
    """Option numbers outside 1..len(offered) return OUT_OF_RANGE."""
    svc = BookingService()
    offered = svc.get_available_slots(limit=3)
    available = svc.get_available_slots()

    assert resolve_slot("0", offered, available)["result"] == "OUT_OF_RANGE"
    assert resolve_slot("4", offered, available)["result"] == "OUT_OF_RANGE"
    assert resolve_slot("option 7", offered, available)["result"] == "OUT_OF_RANGE"


def test_resolve_slot_day_and_time():
    """Day and time expressions match unique slots or detect ambiguity."""
    svc = BookingService()
    offered = svc.get_available_slots(limit=3)
    available = svc.get_available_slots()

    # Specific day + time -> MATCH
    r_mon_pm = resolve_slot("Mon 3pm", offered, available)
    assert r_mon_pm["result"] == "MATCH"
    assert r_mon_pm["slot"]["weekday"] == "Monday"
    assert r_mon_pm["slot"]["time"] == "15:00"

    r_tue_am = resolve_slot("Tuesday at 10:30 am", offered, available)
    assert r_tue_am["result"] == "MATCH"
    assert r_tue_am["slot"]["weekday"] == "Tuesday"
    assert r_tue_am["slot"]["time"] == "10:30"

    # Ambiguous: "Monday" matches both 10:30 and 15:00
    r_mon = resolve_slot("Monday", offered, available)
    assert r_mon["result"] == "AMBIGUOUS"
    assert len(r_mon["candidates"]) >= 2

    # Ambiguous: "10:30" matches 10:30 on multiple weekdays
    r_time = resolve_slot("10:30", offered, available)
    assert r_time["result"] == "AMBIGUOUS"

    # No match: Sunday (no inventory on Sunday)
    assert resolve_slot("Sunday 3pm", offered, available)["result"] == "NO_MATCH"
    assert resolve_slot("whenever works", offered, available)["result"] == "NO_MATCH"
