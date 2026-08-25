from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import Project, Question, Response, User
from app.auth import get_current_user
from app.rate_limit import reset_rate_limits


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
