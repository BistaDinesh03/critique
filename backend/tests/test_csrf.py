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
