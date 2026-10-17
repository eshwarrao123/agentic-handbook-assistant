"""Tests for the GET /api/health endpoint (API-001, API-012, API-015)."""


def test_health_check_returns_ok_schema(client):
    """Test API-001: GET /api/health returns HTTP 200 with required schema structure."""
    response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()

    # Core top-level contract assertions (API_CONTRACT §4)
    assert data["status"] in ("ok", "degraded", "unavailable")
    assert data["status"] == "ok"
    assert "version" in data
    assert "time" in data
    assert "components" in data

    # Component structure assertions (API_CONTRACT §4)
    components = data["components"]
    assert "vector_store" in components
    assert "checkpointer" in components
    assert "llm" in components

    assert "status" in components["vector_store"]
    assert "status" in components["checkpointer"]
    assert "status" in components["llm"]


def test_health_check_includes_request_id(client):
    """Test API-012: Response includes X-Request-ID header, echoing or generating."""
    # Auto-generated ID
    response = client.get("/api/health")
    assert response.status_code == 200
    assert "x-request-id" in response.headers
    assert response.headers["x-request-id"].startswith("req-")

    # Echo client-provided ID
    custom_id = "req-client-test-1234"
    custom_response = client.get("/api/health", headers={"X-Request-ID": custom_id})
    assert custom_response.status_code == 200
    assert custom_response.headers.get("x-request-id") == custom_id


def test_health_check_cors_headers(client):
    """Test API-015: Allowed origin http://localhost:5173 receives Access-Control-Allow-Origin."""
    response = client.get(
        "/api/health",
        headers={"Origin": "http://localhost:5173"}
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
