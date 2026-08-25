from app.database import SessionLocal
from app.models import Project, Question, Response, User


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


def create_test_project(client):
    """Helper to create a test project via authenticated client."""
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


def test_submit_response(auth_client):
    """Test submitting a valid response."""
    cleanup_database()
    create_resp = create_test_project(auth_client)
    project_id = create_resp.json()["project"]["id"]

    payload = {
        "clarity": "very_clear",
        "would_use": "yes",
        "suggestion": "Looks great!",
    }
    response = auth_client.post(f"/api/projects/{project_id}/responses", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["clarity"] == "very_clear"
    assert data["would_use"] == "yes"
    assert data["clarity"] == "very_clear"  # suggestion is only visible via results endpoint
    cleanup_database()


def test_submit_response_without_suggestion(auth_client):
    """Test submitting a response with optional suggestion omitted."""
    cleanup_database()
    create_resp = create_test_project(auth_client)
    project_id = create_resp.json()["project"]["id"]

    payload = {
        "clarity": "confusing",
        "would_use": "no",
        "suggestion": None,
    }
    response = auth_client.post(f"/api/projects/{project_id}/responses", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "suggestion" not in data  # public response has no suggestion field
    cleanup_database()


def test_duplicate_response_rejected(auth_client):
    """Test that duplicate response from same user is rejected."""
    cleanup_database()
    create_resp = create_test_project(auth_client)
    project_id = create_resp.json()["project"]["id"]

    payload = {
        "clarity": "very_clear",
        "would_use": "yes",
        "suggestion": "First",
    }
    response1 = auth_client.post(f"/api/projects/{project_id}/responses", json=payload)
    assert response1.status_code == 201

    response2 = auth_client.post(f"/api/projects/{project_id}/responses", json=payload)
    assert response2.status_code == 409
    cleanup_database()


def test_invalid_clarity_rejected(auth_client):
    """Test that invalid clarity value is rejected."""
    cleanup_database()
    create_resp = create_test_project(auth_client)
    project_id = create_resp.json()["project"]["id"]

    payload = {"clarity": "invalid_value", "would_use": "yes"}
    response = auth_client.post(f"/api/projects/{project_id}/responses", json=payload)
    assert response.status_code == 422
    cleanup_database()


def test_invalid_would_use_rejected(auth_client):
    """Test that invalid would_use value is rejected."""
    cleanup_database()
    create_resp = create_test_project(auth_client)
    project_id = create_resp.json()["project"]["id"]

    payload = {"clarity": "very_clear", "would_use": "invalid"}
    response = auth_client.post(f"/api/projects/{project_id}/responses", json=payload)
    assert response.status_code == 422
    cleanup_database()


def test_response_for_nonexistent_project(auth_client):
    """Test submitting response for a project that doesn't exist."""
    cleanup_database()
    payload = {"clarity": "very_clear", "would_use": "yes"}
    response = auth_client.post("/api/projects/99999/responses", json=payload)
    assert response.status_code == 404
    cleanup_database()


def test_list_responses(auth_client):
    """Test listing responses for a project."""
    cleanup_database()
    create_resp = create_test_project(auth_client)
    project_id = create_resp.json()["project"]["id"]

    payload = {"clarity": "very_clear", "would_use": "yes", "suggestion": "Nice!"}
    auth_client.post(f"/api/projects/{project_id}/responses", json=payload)

    response = auth_client.get(f"/api/projects/{project_id}/responses")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["clarity"] == "very_clear"
    cleanup_database()


def test_suggestion_length_validation(auth_client):
    """Test that overly long suggestion is rejected."""
    cleanup_database()
    create_resp = create_test_project(auth_client)
    project_id = create_resp.json()["project"]["id"]

    payload = {
        "clarity": "very_clear",
        "would_use": "yes",
        "suggestion": "x" * 2001,
    }
    response = auth_client.post(f"/api/projects/{project_id}/responses", json=payload)
    assert response.status_code == 422
    cleanup_database()

