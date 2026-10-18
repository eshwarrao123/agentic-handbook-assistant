"""Tests for GET /api/slots endpoint (API-003, API-004, FR-023)."""

from app.booking.service import get_booking_service


def test_get_slots_default_returns_full_inventory(client):
    """API-003: GET /api/slots returns available slots with default limit=10."""
    svc = get_booking_service()
    svc.reset()

    response = client.get("/api/slots")
    assert response.status_code == 200
    data = response.json()

    assert data["service_type"] == "performance_review"
    assert data["timezone"] == "Asia/Kolkata"
    assert data["total_available"] == 10
    assert len(data["slots"]) == 10

    # Verify first slot structure
    s0 = data["slots"][0]
    assert "slot_id" in s0
    assert s0["slot_id"].startswith("slot-202610")
    assert "start" in s0
    assert "label" in s0
    assert "IST" in s0["label"]

    # Header verification
    assert "x-request-id" in response.headers
    assert response.headers["x-request-id"].startswith("req-")


def test_get_slots_custom_limit(client):
    """API-003: Query parameter limit=3 returns exactly 3 slots."""
    svc = get_booking_service()
    svc.reset()

    response = client.get("/api/slots?limit=3")
    assert response.status_code == 200
    data = response.json()

    assert len(data["slots"]) == 3
    assert data["total_available"] == 10


def test_get_slots_invalid_limit_zero_returns_422(client):
    """API-004: limit=0 returns HTTP 422 with VALIDATION_ERROR envelope."""
    response = client.get("/api/slots?limit=0")
    assert response.status_code == 422
    data = response.json()

    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert data["error"]["retryable"] is False
    assert any(d.get("field") == "limit" for d in (data["error"]["details"] or []))


def test_get_slots_invalid_limit_too_large_returns_422(client):
    """API-004: limit=11 returns HTTP 422 with VALIDATION_ERROR envelope."""
    response = client.get("/api/slots?limit=11")
    assert response.status_code == 422
    data = response.json()

    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_get_slots_invalid_limit_non_integer_returns_422(client):
    """API-004: limit=abc returns HTTP 422 with VALIDATION_ERROR envelope."""
    response = client.get("/api/slots?limit=abc")
    assert response.status_code == 422
    data = response.json()

    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_get_slots_reflects_booked_slots(client):
    """API-003: Booked slots are excluded from GET /api/slots and total_available decrements."""
    svc = get_booking_service()
    svc.reset()

    available = svc.get_available_slots()
    first_slot_id = available[0]["slot_id"]

    # Direct booking through service
    import asyncio
    asyncio.run(svc.create_booking("Alex Chen", "alex@example.com", first_slot_id))

    # REST endpoint call
    response = client.get("/api/slots")
    assert response.status_code == 200
    data = response.json()

    assert data["total_available"] == 9
    assert len(data["slots"]) == 9
    assert all(s["slot_id"] != first_slot_id for s in data["slots"])

    # Reset service state
    svc.reset()
