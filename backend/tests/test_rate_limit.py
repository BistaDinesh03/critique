from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import Project, Question, Response, User
from app.auth import get_current_user
from app.rate_limit import reset_rate_limits
from starlette.requests import Request
import app.rate_limit as limiter


def _request_from(ip: str) -> Request:
    return Request({
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"cf-connecting-ip", ip.encode())],
        "client": ("127.0.0.1", 1234),
    })


def test_stale_buckets_are_swept(monkeypatch):
    reset_rate_limits()
    monkeypatch.setattr(limiter, "SWEEP_INTERVAL", 2)
    now = [1000.0]
    monkeypatch.setattr(limiter.time, "time", lambda: now[0])

    limiter.rate_limit("auth")(_request_from("203.0.113.1"))
    assert "auth:203.0.113.1" in limiter._requests

    now[0] += limiter.RATE_LIMITS["auth"]["window"]
    limiter.rate_limit("auth")(_request_from("203.0.113.2"))
    assert "auth:203.0.113.1" not in limiter._requests
    assert "auth:203.0.113.2" in limiter._requests


def test_address_rotation_cannot_grow_buckets_past_cap(monkeypatch):
    reset_rate_limits()
    monkeypatch.setattr(limiter, "MAX_TRACKED_KEYS", 2)
    monkeypatch.setattr(limiter, "SWEEP_INTERVAL", 100)

    for ip in ("203.0.113.1", "203.0.113.2", "203.0.113.3"):
        limiter.rate_limit("auth")(_request_from(ip))

    assert len(limiter._requests) == 2
    assert "auth:203.0.113.1" not in limiter._requests
    assert "auth:203.0.113.3" in limiter._requests


def cleanup_database():
    db = SessionLocal()
    try:
        db.query(Response).delete()
        db.query(Question).delete()
        db.query(Project).delete()
        db.query(User).delete()
        db.commit()
    finally:
        db.close()


def create_authenticated_client():
    """Create a client with auth and CSRF."""
    db = SessionLocal()
    user = User(github_id=444444, username="ratelimit_test_user")
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)
    client.cookies.set("critique_csrf", "rate_test_token")
    client.headers["X-CSRF-Token"] = "rate_test_token"
    return client


def project_payload(title="Rate Test"):
    return {
        "project_data": {
            "title": title,
            "description": None,
            "url": None,
            "image_url": None,
        },
        "question_data": {"text": "Test?"},
    }


def test_rate_limit_allows_under_limit():
    """Test that requests under the limit are allowed."""
    reset_rate_limits()
    cleanup_database()
    client = create_authenticated_client()
    
    try:
        # 5 requests = limit for project_create
        for i in range(5):
            response = client.post("/api/projects/", json=project_payload(f"Test {i}"))
            assert response.status_code == 201, f"Request {i+1} failed with {response.status_code}"
    finally:
        app.dependency_overrides.clear()
    reset_rate_limits()
    cleanup_database()


def test_rate_limit_blocks_over_limit():
    """Test that requests over the limit return 429."""
    reset_rate_limits()
    cleanup_database()
    client = create_authenticated_client()
    
    try:
        # Send 5 requests (all should succeed)
        for i in range(5):
            response = client.post("/api/projects/", json=project_payload(f"Test {i}"))
            assert response.status_code == 201
        
        # 6th request should be blocked
        response = client.post("/api/projects/", json=project_payload("Blocked"))
        assert response.status_code == 429
    finally:
        app.dependency_overrides.clear()
    reset_rate_limits()
    cleanup_database()


def test_rate_limit_resets():
    """Test that rate limiter can be reset."""
    reset_rate_limits()
    cleanup_database()
    client = create_authenticated_client()
    
    try:
        # Exhaust the limit
        for i in range(5):
            client.post("/api/projects/", json=project_payload(f"Test {i}"))
        
        # Should be blocked
        response = client.post("/api/projects/", json=project_payload("Blocked"))
        assert response.status_code == 429
        
        # Reset and try again
        reset_rate_limits()
        response = client.post("/api/projects/", json=project_payload("After Reset"))
        assert response.status_code == 201
    finally:
        app.dependency_overrides.clear()
    reset_rate_limits()
    cleanup_database()

def test_cf_connecting_ip_separates_buckets():
    """Two clients with different CF-Connecting-IP values get separate buckets."""
    reset_rate_limits()
    cleanup_database()
    client = create_authenticated_client()
    try:
        for i in range(5):
            r = client.post("/api/projects/", json=project_payload(f"A{i}"), headers={"CF-Connecting-IP": "203.0.113.10"})
            assert r.status_code == 201
        r6 = client.post("/api/projects/", json=project_payload("A-blocked"), headers={"CF-Connecting-IP": "203.0.113.10"})
        assert r6.status_code == 429
        rB = client.post("/api/projects/", json=project_payload("B-allowed"), headers={"CF-Connecting-IP": "203.0.113.11"})
        assert rB.status_code == 201
    finally:
        app.dependency_overrides.clear()
    reset_rate_limits()
    cleanup_database()


def test_cf_connecting_ip_still_enforces_limit():
    """A single CF-Connecting-IP identity still hits the limit."""
    reset_rate_limits()
    cleanup_database()
    client = create_authenticated_client()
    try:
        for i in range(5):
            r = client.post("/api/projects/", json=project_payload(f"L{i}"), headers={"CF-Connecting-IP": "198.51.100.7"})
            assert r.status_code == 201
        r = client.post("/api/projects/", json=project_payload("L6"), headers={"CF-Connecting-IP": "198.51.100.7"})
        assert r.status_code == 429
    finally:
        app.dependency_overrides.clear()
    reset_rate_limits()
    cleanup_database()


def test_x_forwarded_for_does_not_change_identity():
    """A spoofed X-Forwarded-For header must not create a new bucket."""
    reset_rate_limits()
    cleanup_database()
    client = create_authenticated_client()
    try:
        for i in range(5):
            r = client.post("/api/projects/", json=project_payload(f"X{i}"), headers={"X-Forwarded-For": f"10.0.0.{i}"})
            assert r.status_code == 201
        r = client.post("/api/projects/", json=project_payload("X6"), headers={"X-Forwarded-For": "10.0.0.99"})
        assert r.status_code == 429, "X-Forwarded-For must not bypass the limit"
    finally:
        app.dependency_overrides.clear()
    reset_rate_limits()
    cleanup_database()


def test_missing_cf_header_falls_back_to_peer():
    """Without CF-Connecting-IP, the peer IP is used and limits still apply."""
    reset_rate_limits()
    cleanup_database()
    client = create_authenticated_client()
    try:
        for i in range(5):
            r = client.post("/api/projects/", json=project_payload(f"P{i}"))
            assert r.status_code == 201
        r = client.post("/api/projects/", json=project_payload("P6"))
        assert r.status_code == 429
    finally:
        app.dependency_overrides.clear()
    reset_rate_limits()
    cleanup_database()


def test_invalid_cf_header_falls_back_to_peer():
    """A malformed CF-Connecting-IP is ignored and falls back to the peer IP."""
    reset_rate_limits()
    cleanup_database()
    client = create_authenticated_client()
    try:
        for i in range(5):
            r = client.post("/api/projects/", json=project_payload(f"I{i}"), headers={"CF-Connecting-IP": "not-an-ip"})
            assert r.status_code == 201
        r = client.post("/api/projects/", json=project_payload("I6"), headers={"CF-Connecting-IP": "also-not-an-ip"})
        assert r.status_code == 429
    finally:
        app.dependency_overrides.clear()
    reset_rate_limits()
    cleanup_database()
