"""Tests for POST /api/chat endpoint and error envelope (API-005, API-007, API-008, API-009, API-011)."""

from unittest.mock import patch
from starlette.testclient import TestClient
from app.api.errors import validate_thread_id
from app.main import app


def test_chat_new_thread_returns_contract_schema(client):
    """Test API-005: POST /api/chat without thread_id initializes a new thread with contract schema."""
    payload = {
        "thread_id": None,
        "message": "Hi, I need to book a 1-on-1 Performance Review session.",
    }
    response = client.post("/api/chat", json=payload)

    assert response.status_code == 200
    data = response.json()

    # Thread ID assertions
    assert "thread_id" in data
    assert validate_thread_id(data["thread_id"]) is True
    assert data["is_new_thread"] is True

    # Reply assertions
    reply = data["reply"]
    assert reply["role"] == "assistant"
    assert "message_id" in reply
    assert "content" in reply
    assert len(reply["content"]) > 0
    assert "created_at" in reply

    # Booking assertions
    booking = data["booking"]
    assert booking["status"] == "collecting"
    assert booking["service_type"] == "performance_review"

    # Agent info assertions
    agent = data["agent"]
    assert agent["status"] == "ok"
    assert "start_turn" in agent["route"]
    assert "booking_update" in agent["route"]
    assert "ask_missing_info" in agent["route"]
    assert "compose_response" in agent["route"]

    # Request ID assertion
    assert "x-request-id" in response.headers
    assert response.headers["x-request-id"].startswith("req-")


def test_chat_reuses_existing_thread(client):
    """Test API-006: Second turn with returned thread_id continues thread with is_new_thread=False."""
    # Turn 1
    t1_resp = client.post("/api/chat", json={
        "thread_id": None,
        "message": "Hi, I need to book a 1-on-1 Performance Review session.",
    })
    assert t1_resp.status_code == 200
    thread_id = t1_resp.json()["thread_id"]

    # Turn 2
    t2_resp = client.post("/api/chat", json={
        "thread_id": thread_id,
        "message": "Alex Chen (alex.chen@example.com)",
    })
    assert t2_resp.status_code == 200
    data_t2 = t2_resp.json()

    assert data_t2["thread_id"] == thread_id
    assert data_t2["is_new_thread"] is False
    assert data_t2["booking"]["status"] == "awaiting_slot"
    assert data_t2["booking"]["full_name"] == "Alex Chen"
    assert data_t2["booking"]["email"] == "alex.chen@example.com"


def test_chat_malformed_thread_id_returns_400_envelope(client):
    """Test API-007: Malformed thread_id returns HTTP 400 with INVALID_THREAD_ID envelope."""
    response = client.post("/api/chat", json={
        "thread_id": "not-a-uuid",
        "message": "Hello",
    })

    assert response.status_code == 400
    data = response.json()

    assert "error" in data
    error = data["error"]
    assert error["code"] == "INVALID_THREAD_ID"
    assert "thread_id must be a valid UUID" in error["message"]
    assert error["retryable"] is False
    assert error["request_id"] == response.headers["x-request-id"]


def test_chat_empty_or_whitespace_message_returns_422_envelope(client):
    """Test API-008: Empty or whitespace message returns HTTP 422 with VALIDATION_ERROR envelope."""
    # Empty string
    r1 = client.post("/api/chat", json={"message": ""})
    assert r1.status_code == 422
    data1 = r1.json()
    assert data1["error"]["code"] == "VALIDATION_ERROR"
    assert data1["error"]["retryable"] is False
    assert any(d.get("field") == "message" for d in (data1["error"]["details"] or []))

    # Whitespace only string
    r2 = client.post("/api/chat", json={"message": "    "})
    assert r2.status_code == 422
    data2 = r2.json()
    assert data2["error"]["code"] == "VALIDATION_ERROR"


def test_chat_message_length_boundary_validation(client):
    """Test API-009: 2001 chars returns HTTP 422; 2000 chars is accepted with HTTP 200."""
    # 2001 chars -> 422
    oversized = "a" * 2001
    r_over = client.post("/api/chat", json={"message": oversized})
    assert r_over.status_code == 422
    assert r_over.json()["error"]["code"] == "VALIDATION_ERROR"

    # 2000 chars -> 200
    valid_max = "I want to schedule an appointment. " + ("a" * 1950)
    r_valid = client.post("/api/chat", json={"message": valid_max[:2000]})
    assert r_valid.status_code == 200


def test_forced_internal_exception_returns_500_envelope():
    """Test API-011: Unhandled exceptions return HTTP 500 with INTERNAL_ERROR envelope without leaking traces."""
    safe_client = TestClient(app, raise_server_exceptions=False)
    with patch("app.services.chat_service.chat_service.handle_chat", side_effect=RuntimeError("Secret database failed")):
        response = safe_client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    error = data["error"]
    assert error["code"] == "INTERNAL_ERROR"
    assert error["message"] == "Something went wrong on our side."
    assert error["retryable"] is True
    assert "Secret database failed" not in response.text
