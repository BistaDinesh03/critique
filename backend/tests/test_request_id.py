from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_request_id_generated_when_absent():
    """Verify that responses include an X-Request-ID when not provided by client."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) >= 16


def test_request_id_propagated_when_provided():
    """Verify that client-provided X-Request-ID is preserved and returned."""
    custom_id = "req-custom-trace-12345"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id


def test_unique_request_ids_per_call():
    """Verify that distinct requests generate distinct request IDs."""
    r1 = client.get("/health")
    r2 = client.get("/health")
    assert r1.headers["X-Request-ID"] != r2.headers["X-Request-ID"]


def test_request_id_present_on_error_responses():
    """Verify that X-Request-ID is present even on 404 or error responses."""
    response = client.get("/nonexistent-endpoint-404")
    assert response.status_code == 404
    assert "X-Request-ID" in response.headers
