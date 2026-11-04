from fastapi.testclient import TestClient
from app.main import app
from app.config import settings


def test_security_headers_present():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_hsts_omitted_outside_production(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "development")
    client = TestClient(app)
    response = client.get("/health")
    assert "Strict-Transport-Security" not in response.headers


def test_hsts_present_in_production(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    client = TestClient(app)
    response = client.get("/health")
    assert response.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"
