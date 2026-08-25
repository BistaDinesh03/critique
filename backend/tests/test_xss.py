from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import Project, Question, Response, User
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


def test_xss_in_project_title(auth_client):
    """Test that script tags in project title are not executed (stored as text)."""
    reset_rate_limits()
    cleanup_database()
    
    # Submit project with XSS payload in title
    xss_payload = '<script>alert("XSS")</script>'
    payload = {
        "project_data": {
            "title": xss_payload,
            "description": "Test",
            "url": None,
            "image_url": None,
        },
        "question_data": {"text": "Test?"},
    }
    response = auth_client.post("/api/projects/", json=payload)
    assert response.status_code == 201
    
    # Get the project and verify the title is stored as-is (not sanitized server-side)
    project_id = response.json()["project"]["id"]
    get_resp = auth_client.get(f"/api/projects/{project_id}")
    data = get_resp.json()
    assert data["project"]["title"] == xss_payload
    
    # The frontend should escape this when rendering (tested by frontend)
    cleanup_database()


def test_xss_in_suggestion(auth_client):
    """Test that script tags in suggestion are accepted but not executed."""
    reset_rate_limits()
    cleanup_database()
    
    # Create project
    payload = {
        "project_data": {"title": "XSS Test", "description": None, "url": None, "image_url": None},
        "question_data": {"text": "Test?"},
    }
    create_resp = auth_client.post("/api/projects/", json=payload)
    project_id = create_resp.json()["project"]["id"]
    
    # Submit response with XSS payload
    xss_payload = '<img src="x" onerror="alert(1)">'
    response_payload = {
        "clarity": "very_clear",
        "would_use": "yes",
        "suggestion": xss_payload,
    }
    response = auth_client.post(f"/api/projects/{project_id}/responses", json=response_payload)
    assert response.status_code == 201
    
    # The suggestion should be stored as-is but escaped on render
    cleanup_database()


def test_invalid_url_rejected(auth_client):
    """Test that invalid URL is rejected."""
    reset_rate_limits()
    cleanup_database()
    
    payload = {
        "project_data": {
            "title": "Invalid URL Test",
            "description": None,
            "url": "not-a-valid-url",
            "image_url": None,
        },
        "question_data": {"text": "Test?"},
    }
    response = auth_client.post("/api/projects/", json=payload)
    assert response.status_code == 422
    
    cleanup_database()


def test_long_suggestion_rejected(auth_client):
    """Test that overly long suggestion is rejected."""
    reset_rate_limits()
    cleanup_database()
    
    payload = {
        "project_data": {"title": "Long Suggestion", "description": None, "url": None, "image_url": None},
        "question_data": {"text": "Test?"},
    }
    create_resp = auth_client.post("/api/projects/", json=payload)
    project_id = create_resp.json()["project"]["id"]
    
    # 2001 chars - exceeds limit
    long_text = "x" * 2001
    response_payload = {
        "clarity": "very_clear",
        "would_use": "yes",
        "suggestion": long_text,
    }
    response = auth_client.post(f"/api/projects/{project_id}/responses", json=response_payload)
    assert response.status_code == 422
    
    cleanup_database()


def test_long_title_rejected(auth_client):
    """Test that overly long title is rejected."""
    reset_rate_limits()
    cleanup_database()
    
    long_title = "x" * 201  # 201 chars, limit is 200
    payload = {
        "project_data": {"title": long_title, "description": None, "url": None, "image_url": None},
        "question_data": {"text": "Test?"},
    }
    response = auth_client.post("/api/projects/", json=payload)
    assert response.status_code == 422
    
    cleanup_database()
