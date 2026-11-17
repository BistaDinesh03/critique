import pytest
from fastapi.testclient import TestClient
from app.main import app


def test_security_headers_present():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    csp = response.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "frame-src 'none'" in csp
    assert "form-action 'self'" in csp


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


@pytest.mark.parametrize("path", [
    "/",
    "/discover",
    "/my-projects",
    "/api/stats",
    "/static/shared.css",
    "/nonexistent-page-for-404",
])
def test_x_frame_options_clickjacking_protection_across_routes(path):
    """Every page, API, static file, and error response enforces X-Frame-Options: DENY and baseline security headers (fixes #347)."""
    client = TestClient(app)
    response = client.get(path)
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    csp = response.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "frame-src 'none'" in csp
    assert "form-action 'self'" in csp


def test_csp_contains_required_directives():
    """CSP header includes all required directives (fixes #346)."""
    client = TestClient(app)
    response = client.get("/")
    csp = response.headers.get("Content-Security-Policy", "")
    required = [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: https:",
        "font-src 'self' data:",
        "connect-src 'self'",
        "frame-ancestors 'none'",
        "frame-src 'none'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
    ]
    for directive in required:
        assert directive in csp, f"Missing CSP directive: {directive}"


def test_csp_on_error_responses():
    """CSP header is present on error responses."""
    client = TestClient(app)
    response = client.get("/nonexistent-path-12345")
    assert "Content-Security-Policy" in response.headers
    csp = response.headers.get("Content-Security-Policy", "")
    assert "form-action 'self'" in csp
    assert "frame-src 'none'" in csp
