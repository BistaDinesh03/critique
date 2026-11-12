"""Tests for security headers on all responses."""

from fastapi.testclient import TestClient
from app.main import app


def test_security_headers_present():
    client = TestClient(app)
    response = client.get("/")
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    csp = response.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "frame-src 'none'" in csp
    assert "form-action 'self'" in csp
    assert "object-src 'none'" in csp
    assert "base-uri 'self'" in csp


def test_security_headers_on_api_responses():
    client = TestClient(app)
    response = client.get("/auth/check")
    # Should still have security headers even on error responses
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert "Content-Security-Policy" in response.headers


def test_security_headers_on_404():
    client = TestClient(app)
    response = client.get("/nonexistent-path-12345")
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert "Content-Security-Policy" in response.headers


def test_csp_contains_required_directives():
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
