from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Test that the health check endpoint returns ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_homepage():
    """Test that the homepage returns the expected content."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Critique" in response.text
    assert "Ask one question. Get real answers." in response.text
