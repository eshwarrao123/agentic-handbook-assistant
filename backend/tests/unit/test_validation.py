"""Unit tests for input validation functions (UT-020)."""

from app.api.errors import validate_thread_id


def test_thread_id_validation_accepts_valid_uuids():
    """UT-020: Valid UUID strings are accepted."""
    assert validate_thread_id("3f2b8c1e-6a4d-4e0b-9d57-1c2a7f9e5b10") is True
    assert validate_thread_id("a1c4e7d2-3b58-4f6a-8c91-0e2d5b7f4a63") is True
    assert validate_thread_id("00000000-0000-4000-8000-000000000000") is True


def test_thread_id_validation_rejects_malformed_inputs():
    """UT-020: Empty strings, malformed strings, injection attempts, and braced UUIDs are rejected."""
    # Empty and whitespace
    assert validate_thread_id("") is False
    assert validate_thread_id("   ") is False

    # Short and random strings
    assert validate_thread_id("abc") is False
    assert validate_thread_id("not-a-uuid") is False

    # SQL injection attempt
    assert validate_thread_id("3f2b8c1e' OR 1=1;--") is False

    # Oversized string
    assert validate_thread_id("3f2b8c1e-6a4d-4e0b-9d57-1c2a7f9e5b10" * 10) is False

    # UUID enclosed in braces
    assert validate_thread_id("{3f2b8c1e-6a4d-4e0b-9d57-1c2a7f9e5b10}") is False

    # Non-string types
    assert validate_thread_id(None) is False
    assert validate_thread_id(12345) is False
