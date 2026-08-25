from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db, SessionLocal
from app.models import Project, Question, Response, User

client = TestClient(app)


def setup_function():
    """Initialize database before each test."""
    init_db()


def cleanup_database():
    """Remove test data from database."""
    db = SessionLocal()
    try:
        db.query(Response).delete()
        db.query(Question).delete()
        db.query(Project).delete()
        db.query(User).delete()
        db.commit()
    finally:
        db.close()


def create_test_project():
    """Helper to create a test project via API."""
    payload = {
        "project_data": {
            "title": "Test Project",
            "description": "A test project",
            "url": "https://example.com",
            "image_url": None,
        },
        "question_data": {
            "text": "Is this clear?",
        },
    }
    return client.post("/api/projects/", json=payload)


def test_submit_response():
    """Test submitting a valid response."""
    cleanup_database()

    # Create project
    create_resp = create_test_project()
    project_id = create_resp.json()["project"]["id"]

    # Submit response
    payload = {
        "clarity": "very_clear",
        "would_use": "yes",
        "suggestion": "Looks great!",
    }
    response = client.post(f"/api/projects/{project_id}/responses", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["clarity"] == "very_clear"
    assert data["would_use"] == "yes"
    assert data["suggestion"] == "Looks great!"
    assert data["question_id"] is not None

    cleanup_database()


def test_submit_response_without_suggestion():
    """Test submitting a response with optional suggestion omitted."""
    cleanup_database()

    create_resp = create_test_project()
    project_id = create_resp.json()["project"]["id"]

    payload = {
        "clarity": "confusing",
        "would_use": "no",
        "suggestion": None,
    }
    response = client.post(f"/api/projects/{project_id}/responses", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["suggestion"] is None

    cleanup_database()


def test_duplicate_response_rejected():
    """Test that duplicate response from same IP is rejected."""
    cleanup_database()

    create_resp = create_test_project()
    project_id = create_resp.json()["project"]["id"]

    payload = {
        "clarity": "very_clear",
        "would_use": "yes",
        "suggestion": "First",
    }

    # First submission
    response1 = client.post(f"/api/projects/{project_id}/responses", json=payload)
    assert response1.status_code == 201

    # Duplicate submission
    response2 = client.post(f"/api/projects/{project_id}/responses", json=payload)
    assert response2.status_code == 409

    cleanup_database()


def test_invalid_clarity_rejected():
    """Test that invalid clarity value is rejected."""
    cleanup_database()

    create_resp = create_test_project()
    project_id = create_resp.json()["project"]["id"]

    payload = {
        "clarity": "invalid_value",
        "would_use": "yes",
    }
    response = client.post(f"/api/projects/{project_id}/responses", json=payload)
    assert response.status_code == 422

    cleanup_database()


def test_invalid_would_use_rejected():
    """Test that invalid would_use value is rejected."""
    cleanup_database()

    create_resp = create_test_project()
    project_id = create_resp.json()["project"]["id"]

    payload = {
        "clarity": "very_clear",
        "would_use": "invalid",
    }
    response = client.post(f"/api/projects/{project_id}/responses", json=payload)
    assert response.status_code == 422

    cleanup_database()


def test_response_for_nonexistent_project():
    """Test submitting response for a project that doesn't exist."""
    cleanup_database()

    payload = {
        "clarity": "very_clear",
        "would_use": "yes",
    }
    response = client.post("/api/projects/99999/responses", json=payload)
    assert response.status_code == 404

    cleanup_database()


def test_list_responses():
    """Test listing responses for a project."""
    cleanup_database()

    create_resp = create_test_project()
    project_id = create_resp.json()["project"]["id"]

    # Submit response
    payload = {
        "clarity": "very_clear",
        "would_use": "yes",
        "suggestion": "Nice!",
    }
    client.post(f"/api/projects/{project_id}/responses", json=payload)

    # List responses
    response = client.get(f"/api/projects/{project_id}/responses")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["clarity"] == "very_clear"

    cleanup_database()


def test_suggestion_length_validation():
    """Test that overly long suggestion is rejected."""
    cleanup_database()

    create_resp = create_test_project()
    project_id = create_resp.json()["project"]["id"]

    payload = {
        "clarity": "very_clear",
        "would_use": "yes",
        "suggestion": "x" * 2001,  # 2001 chars, max is 2000
    }
    response = client.post(f"/api/projects/{project_id}/responses", json=payload)
    assert response.status_code == 422

    cleanup_database()
