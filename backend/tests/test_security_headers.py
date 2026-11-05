from fastapi.testclient import TestClient
from app.main import app


def test_security_headers_present():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_hsts_header_in_production(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "HSTS_ENABLED", True)
    monkeypatch.setattr(settings, "HSTS_MAX_AGE", 31536000)
    monkeypatch.setattr(settings, "HSTS_INCLUDE_SUBDOMAINS", True)
    monkeypatch.setattr(settings, "HSTS_PRELOAD", False)

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"


def test_hsts_header_with_preload(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "HSTS_ENABLED", True)
    monkeypatch.setattr(settings, "HSTS_MAX_AGE", 63072000)
    monkeypatch.setattr(settings, "HSTS_INCLUDE_SUBDOMAINS", True)
    monkeypatch.setattr(settings, "HSTS_PRELOAD", True)

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("Strict-Transport-Security") == "max-age=63072000; includeSubDomains; preload"


def test_hsts_header_omitted_in_development_by_default(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "HSTS_ENABLED", False)
    monkeypatch.setattr(settings, "APP_ENV", "development")

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert "Strict-Transport-Security" not in response.headers
