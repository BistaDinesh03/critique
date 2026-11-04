from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_response_includes_request_id():
    """Every response contains an X-Request-ID header."""
    response = client.get("/health")
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0


def test_preserves_incoming_request_id():
    """Incoming X-Request-ID is echoed back on the response."""
    custom_id = "req-custom-trace-12345"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.headers.get("X-Request-ID") == custom_id
