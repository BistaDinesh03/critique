from http.cookies import SimpleCookie
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.database import SessionLocal
from app.models import Project, Question, Response, User
from app.auth import get_current_user
from app.csrf import CSRF_COOKIE_NAME


def cleanup_database():
    db = SessionLocal()
    try:
        # Delete in dependency order so foreign keys can be enforced.
        from app.models import AnalyticsEvent, ProjectView, Question, Response
        db.query(AnalyticsEvent).delete()
        db.query(ProjectView).delete()
        db.query(Response).delete()
        db.query(Question).delete()
        db.query(Project).delete()
        db.query(User).delete()
        db.commit()
    finally:
        db.close()


def create_authenticated_client():
    """Create a client with auth override but NO CSRF token."""
    db = SessionLocal()
    user = User(github_id=555555, username="csrf_test_user")
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app), user


def create_project_payload():
    return {
        "project_data": {
            "title": "CSRF Test",
            "description": None,
            "url": None,
            "image_url": None,
        },
        "question_data": {
            "text": "Test question?",
        },
    }


def test_missing_csrf_token_rejected():
    """Test that POST without CSRF token returns 403 and persists no project."""
    cleanup_database()
    client, _ = create_authenticated_client()
    
    try:
        response = client.post("/api/projects/", json=create_project_payload())
        assert response.status_code == 403
        with SessionLocal() as db:
            assert db.query(Project).count() == 0
    finally:
        app.dependency_overrides.clear()
    cleanup_database()


def test_invalid_csrf_token_rejected():
    """Test that POST with wrong CSRF token returns 403 and persists no project."""
    cleanup_database()
    client, _ = create_authenticated_client()
    client.cookies.set(CSRF_COOKIE_NAME, "correct_token")
    client.headers["X-CSRF-Token"] = "wrong_token"
    
    try:
        response = client.post("/api/projects/", json=create_project_payload())
        assert response.status_code == 403
        with SessionLocal() as db:
            assert db.query(Project).count() == 0
    finally:
        app.dependency_overrides.clear()
    cleanup_database()


def test_valid_csrf_token_accepted():
    """Test that POST with matching CSRF token works."""
    cleanup_database()
    client, _ = create_authenticated_client()
    client.cookies.set(CSRF_COOKIE_NAME, "same_token")
    client.headers["X-CSRF-Token"] = "same_token"
    
    try:
        response = client.post("/api/projects/", json=create_project_payload())
        assert response.status_code == 201
        with SessionLocal() as db:
            assert db.query(Project).count() == 1
    finally:
        app.dependency_overrides.clear()
    cleanup_database()


def test_delete_without_csrf_rejected():
    """Test that DELETE without CSRF token returns 403 and leaves project intact."""
    cleanup_database()
    client, _ = create_authenticated_client()
    client.cookies.set(CSRF_COOKIE_NAME, "correct_token")
    client.headers["X-CSRF-Token"] = "correct_token"
    
    # Create a project first
    create_resp = client.post("/api/projects/", json=create_project_payload())
    project_id = create_resp.json()["project"]["id"]
    
    # Now try DELETE without CSRF header
    client.headers.pop("X-CSRF-Token", None)
    
    try:
        response = client.delete(f"/api/projects/{project_id}")
        assert response.status_code == 403
        with SessionLocal() as db:
            assert db.query(Project).filter(Project.id == project_id).count() == 1
    finally:
        app.dependency_overrides.clear()
    cleanup_database()


def test_csrf_token_endpoint_sets_cookie_for_fresh_client():
    """Test that GET /auth/csrf-token sets the cookie it returns, and the pair passes CSRF."""
    cleanup_database()
    client, _ = create_authenticated_client()

    try:
        token_resp = client.get("/auth/csrf-token")
        assert token_resp.status_code == 200
        token = token_resp.json()["csrf_token"]
        assert f"{CSRF_COOKIE_NAME}={token}" in token_resp.headers.get("set-cookie", "")
        assert client.cookies.get(CSRF_COOKIE_NAME) == token

        # Reuse the cookie the endpoint set plus the matching header.
        client.headers["X-CSRF-Token"] = token
        response = client.post("/api/projects/", json=create_project_payload())
        assert response.status_code == 201
    finally:
        app.dependency_overrides.clear()
    cleanup_database()


def test_csrf_token_endpoint_echoes_existing_cookie():
    """Test that GET /auth/csrf-token echoes an existing cookie without rotating it."""
    client = TestClient(app)
    client.cookies.set(CSRF_COOKIE_NAME, "existing_token")

    response = client.get("/auth/csrf-token")
    assert response.status_code == 200
    assert response.json() == {"csrf_token": "existing_token"}
    assert CSRF_COOKIE_NAME not in response.headers.get("set-cookie", "")
    assert client.cookies.get(CSRF_COOKIE_NAME) == "existing_token"



def test_verify_csrf_rejects_non_ascii_header():
    """verify_csrf_token returns False for non-ASCII header (no TypeError)."""
    from app.csrf import verify_csrf_token
    from unittest.mock import MagicMock

    request = MagicMock()
    request.cookies.get.return_value = "valid_ascii_token"
    request.headers.get.return_value = "éinvalid"

    assert verify_csrf_token(request) is False


def test_verify_csrf_rejects_non_ascii_cookie():
    """verify_csrf_token returns False for non-ASCII cookie (no TypeError)."""
    from app.csrf import verify_csrf_token
    from unittest.mock import MagicMock

    request = MagicMock()
    request.cookies.get.return_value = "éinvalid"
    request.headers.get.return_value = "valid_ascii_token"

    assert verify_csrf_token(request) is False


def test_verify_csrf_accepts_matching_ascii():
    """Existing ASCII behavior is unchanged."""
    from app.csrf import verify_csrf_token
    from unittest.mock import MagicMock

    request = MagicMock()
    request.cookies.get.return_value = "same_token"
    request.headers.get.return_value = "same_token"

    assert verify_csrf_token(request) is True


def test_verify_csrf_rejects_mismatched_ascii():
    """Mismatched ASCII still returns False."""
    from app.csrf import verify_csrf_token
    from unittest.mock import MagicMock

    request = MagicMock()
    request.cookies.get.return_value = "correct"
    request.headers.get.return_value = "wrong"

    assert verify_csrf_token(request) is False


def test_csrf_token_rotated_on_login():
    """CSRF token must change across the authentication boundary to prevent session fixation (fixes #349)."""
    import secrets
    from datetime import datetime, timezone, timedelta
    from app.models import EmailLoginToken
    from app.auth import _hash_token
    from app.database import SessionLocal

    test_client = TestClient(app)
    initial_csrf = "pre_auth_csrf_token_1234567890"
    test_client.cookies.set(CSRF_COOKIE_NAME, initial_csrf, domain="testserver.local")

    email = "csrf_rotation_test@example.com"
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)

    db = SessionLocal()
    try:
        db.query(EmailLoginToken).filter(EmailLoginToken.email == email).delete()
        db.query(User).filter(User.email == email).delete()
        db.commit()

        elt = EmailLoginToken(
            email=email,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
            used_at=None,
            requester_ip_hash="testhash",
        )
        db.add(elt)
        db.commit()

        response = test_client.get(f"/auth/email/verify?token={raw_token}", follow_redirects=False)
        assert response.status_code in (302, 303, 307)
        new_csrf = test_client.cookies.get(CSRF_COOKIE_NAME, domain="testserver.local")
        assert new_csrf is not None
        assert new_csrf != initial_csrf
    finally:
        db.query(EmailLoginToken).filter(EmailLoginToken.email == email).delete()
        db.query(User).filter(User.email == email).delete()
        db.commit()
        db.close()


def test_csrf_token_expired_cookie_rejected():
    """When a CSRF cookie expires and is omitted by the client, 403 is returned."""
    cleanup_database()
    client, _ = create_authenticated_client()
    try:
        # Header token persists from stale client state, but cookie expired (dropped)
        client.headers["X-CSRF-Token"] = "expired_csrf_token"
        client.cookies.pop(CSRF_COOKIE_NAME, None)

        response = client.post("/api/projects/", json=create_project_payload())
        assert response.status_code == 403
        assert response.json() == {"detail": "Invalid or missing CSRF token"}
    finally:
        app.dependency_overrides.clear()
    cleanup_database()


def test_set_csrf_cookie_has_max_age_expiration():
    """Verify set_csrf_cookie sets Max-Age according to SESSION_COOKIE_MAX_AGE."""
    from fastapi import Response
    from app.csrf import set_csrf_cookie
    from app.config import settings

    response = Response()
    set_csrf_cookie(response, "test_token_123")
    cookie_header = response.headers.get("set-cookie", "")
    assert f"max-age={settings.SESSION_COOKIE_MAX_AGE}" in cookie_header.lower()


def test_analytics_track_is_exempt_from_csrf():
    """POST /api/analytics/track is exempt from CSRF double-submit cookies for beaconing.

    It is protected by IP rate-limiting and a strict server-side event allowlist instead.
    """
    client = TestClient(app)
    response = client.post("/api/analytics/track?event_name=page_view")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


@pytest.mark.parametrize("secure", [False, True])
def test_csrf_cookie_attributes(monkeypatch, secure):
    monkeypatch.setattr(settings, "SESSION_COOKIE_SECURE", secure)
    cleanup_database()
    client = TestClient(app)
    response = client.get("/auth/csrf-token")
    assert response.status_code == 200

    cookie = SimpleCookie()
    for header in response.headers.get_list("set-cookie"):
        cookie.load(header)
    assert CSRF_COOKIE_NAME in cookie
    csrf_cookie = cookie[CSRF_COOKIE_NAME]
    # Intentionally readable by JavaScript, not HttpOnly
    assert not csrf_cookie["httponly"]
    assert csrf_cookie["samesite"] == "lax"
    assert bool(csrf_cookie["secure"]) is secure
    assert csrf_cookie["path"] == "/"
