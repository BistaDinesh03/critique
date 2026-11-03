from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import Project, Question, Response, User
from app.auth import get_current_user
from app.csrf import CSRF_COOKIE_NAME


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
    """Test that POST without CSRF token returns 403."""
    cleanup_database()
    client, _ = create_authenticated_client()
    
    try:
        response = client.post("/api/projects/", json=create_project_payload())
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
    cleanup_database()


def test_invalid_csrf_token_rejected():
    """Test that POST with wrong CSRF token returns 403."""
    cleanup_database()
    client, _ = create_authenticated_client()
    client.cookies.set(CSRF_COOKIE_NAME, "correct_token")
    client.headers["X-CSRF-Token"] = "wrong_token"
    
    try:
        response = client.post("/api/projects/", json=create_project_payload())
        assert response.status_code == 403
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
    finally:
        app.dependency_overrides.clear()
    cleanup_database()


def test_delete_without_csrf_rejected():
    """Test that DELETE without CSRF token returns 403."""
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
