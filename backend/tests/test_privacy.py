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


def test_owner_sees_suggestion_public_does_not(auth_client):
    """Test that owner sees suggestion but public response has no suggestion field."""
    reset_rate_limits()
    cleanup_database()
    
    # Create project using auth_client
    payload = {
        "project_data": {"title": "Privacy Test", "description": None, "url": None, "image_url": None},
        "question_data": {"text": "Test?"},
    }
    create_resp = auth_client.post("/api/projects/", json=payload)
    project_id = create_resp.json()["project"]["id"]
    owner_id = create_resp.json()["project"]["owner_id"]
    
    # Submit response with suggestion
    response_payload = {
        "clarity": "very_clear",
        "would_use": "yes",
        "suggestion": "Owner should see this.",
    }
    submit_resp = auth_client.post(f"/api/projects/{project_id}/responses", json=response_payload)
    assert submit_resp.status_code == 201
    
    # Owner gets responses (with X-Owner-ID header)
    owner_headers = {"X-Owner-ID": str(owner_id)}
    response = auth_client.get(f"/api/projects/{project_id}/responses", headers=owner_headers)
    data = response.json()
    assert len(data) == 1
    assert data[0]["suggestion"] == "Owner should see this."
    
    # Public (no X-Owner-ID header) — no suggestion
    public_client = TestClient(app)
    public_response = public_client.get(f"/api/projects/{project_id}/responses")
    public_data = public_response.json()
    assert len(public_data) == 1
    assert "suggestion" not in public_data[0]
    assert public_data[0]["clarity"] == "very_clear"
    
    cleanup_database()


def test_results_privacy(auth_client):
    """Test that results endpoint respects privacy."""
    reset_rate_limits()
    cleanup_database()
    
    # Create project
    payload = {
        "project_data": {"title": "Results Privacy", "description": None, "url": None, "image_url": None},
        "question_data": {"text": "Test?"},
    }
    create_resp = auth_client.post("/api/projects/", json=payload)
    project_id = create_resp.json()["project"]["id"]
    owner_id = create_resp.json()["project"]["owner_id"]
    
    # Submit response with suggestion
    response_payload = {
        "clarity": "very_clear",
        "would_use": "yes",
        "suggestion": "Private written feedback.",
    }
    auth_client.post(f"/api/projects/{project_id}/responses", json=response_payload)
    
    # Owner gets full results
    owner_headers = {"X-Owner-ID": str(owner_id)}
    response = auth_client.get(f"/api/projects/{project_id}/results", headers=owner_headers)
    data = response.json()
    assert data["is_owner"] == True
    assert len(data["responses"]) == 1
    assert data["responses"][0]["suggestion"] == "Private written feedback."
    
    # Public gets stats only
    public_client = TestClient(app)
    public_response = public_client.get(f"/api/projects/{project_id}/results")
    public_data = public_response.json()
    assert public_data["is_owner"] == False
    assert public_data["responses"] == []
    assert public_data["stats"]["total"] == 1
    
    cleanup_database()
