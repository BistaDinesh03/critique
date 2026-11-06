from fastapi.testclient import TestClient
import pytest
from app.main import app, lifespan
from app.database import engine

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


@pytest.mark.anyio
async def test_lifespan_startup_and_shutdown():
    """Test that lifespan initializes DB on startup and disposes connection pool on shutdown."""
    disposed = []
    orig_dispose = engine.dispose
    try:
        def mock_dispose():
            disposed.append(True)
            orig_dispose()
        engine.dispose = mock_dispose
        async with lifespan(app):
            assert len(disposed) == 0
        assert len(disposed) == 1
    finally:
        engine.dispose = orig_dispose
