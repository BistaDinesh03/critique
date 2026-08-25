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


def create_project():
    """Helper to create a project via API."""
    payload = {
        "project_data": {
            "title": "Test Results",
            "description": "Testing results",
            "url": "https://example.com",
            "image_url": None,
        },
        "question_data": {
            "text": "Is this clear?",
        },
    }
    return client.post("/api/projects/", json=payload)


def submit_response(project_id, clarity, would_use, suggestion=None):
    """Helper to submit a response via API."""
    payload = {
        "clarity": clarity,
        "would_use": would_use,
        "suggestion": suggestion,
    }
    return client.post(f"/api/projects/{project_id}/responses", json=payload)


def test_results_zero_responses():
    """Test results endpoint with no responses."""
    cleanup_database()
    create_resp = create_project()
    project_id = create_resp.json()["project"]["id"]

    response = client.get(f"/api/projects/{project_id}/results")
    assert response.status_code == 200
    data = response.json()
    assert data["stats"]["total"] == 0
    assert data["responses"] == []

    cleanup_database()


def test_results_one_response():
    """Test results endpoint with one response."""
    cleanup_database()
    create_resp = create_project()
    project_id = create_resp.json()["project"]["id"]

    submit_response(project_id, "very_clear", "yes", "Great!")

    response = client.get(f"/api/projects/{project_id}/results")
    assert response.status_code == 200
    data = response.json()
    assert data["stats"]["total"] == 1
    assert data["stats"]["clarity"]["very_clear"] == 100.0
    assert data["stats"]["would_use"]["yes"] == 100.0
    assert len(data["responses"]) == 1

    cleanup_database()


def test_results_many_responses():
    """Test results endpoint with multiple responses (direct DB insert to bypass IP check)."""
    cleanup_database()
    create_resp = create_project()
    project_id = create_resp.json()["project"]["id"]

    # Insert responses directly into database to bypass IP duplicate check
    db = SessionLocal()
    try:
        question = db.query(Question).filter(Question.project_id == project_id).first()
        user = db.query(User).first()
        
        responses = [
            Response(clarity="very_clear", would_use="yes", suggestion="Nice!", question_id=question.id, user_id=user.id, ip_hash="hash1"),
            Response(clarity="mostly_clear", would_use="maybe", suggestion="Could be better", question_id=question.id, user_id=user.id, ip_hash="hash2"),
            Response(clarity="confusing", would_use="no", suggestion=None, question_id=question.id, user_id=user.id, ip_hash="hash3"),
        ]
        db.add_all(responses)
        db.commit()
    finally:
        db.close()

    response = client.get(f"/api/projects/{project_id}/results")
    assert response.status_code == 200
    data = response.json()
    assert data["stats"]["total"] == 3
    assert len(data["responses"]) == 3

    cleanup_database()


def test_results_nonexistent_project():
    """Test results endpoint for nonexistent project."""
    cleanup_database()
    response = client.get("/api/projects/99999/results")
    assert response.status_code == 404
    cleanup_database()
