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


def create_project(client):
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


def submit_response(client, project_id, clarity, would_use, suggestion=None):
    payload = {
        "clarity": clarity,
        "would_use": would_use,
        "suggestion": suggestion,
    }
    return client.post(f"/api/projects/{project_id}/responses", json=payload)


def test_results_zero_responses(auth_client):
    create_resp = create_project(auth_client)
    project_id = create_resp.json()["project"]["id"]
    response = auth_client.get(f"/api/projects/{project_id}/results")
    assert response.status_code == 200
    data = response.json()
    assert data["stats"]["total"] == 0
    cleanup_database()


def test_results_one_response(auth_client):
    create_resp = create_project(auth_client)
    project_id = create_resp.json()["project"]["id"]
    submit_response(auth_client, project_id, "very_clear", "yes", "Great!")
    response = auth_client.get(f"/api/projects/{project_id}/results")
    assert response.status_code == 200
    data = response.json()
    assert data["stats"]["total"] == 1
    assert data["stats"]["clarity"]["very_clear"] == 100.0
    assert data["stats"]["would_use"]["yes"] == 100.0
    cleanup_database()


def test_results_many_responses(auth_client):
    create_resp = create_project(auth_client)
    project_id = create_resp.json()["project"]["id"]
    
    # Submit one response via API
    submit_response(auth_client, project_id, "very_clear", "yes", "Nice!")
    
    # Create a second user and insert two more responses directly
    db = SessionLocal()
    try:
        question = db.query(Question).filter(Question.project_id == project_id).first()
        existing_user = db.query(User).first()
        
        # Create second user
        second_user = User(github_id=888888, username="second_test_user")
        db.add(second_user)
        db.commit()
        db.refresh(second_user)
        
        if question:
            # Second response from second user
            r2 = Response(
                clarity="mostly_clear",
                would_use="maybe",
                suggestion="Could be better",
                question_id=question.id,
                user_id=second_user.id,
                ip_hash="hash2",
            )
            db.add(r2)
            
            # Third response from first user (different IP - but same user would be caught by duplicate check)
            # So use second user with different IP
            r3 = Response(
                clarity="confusing",
                would_use="no",
                suggestion=None,
                question_id=question.id,
                user_id=second_user.id,
                ip_hash="hash3",
            )
            db.add(r3)
            db.commit()
    finally:
        db.close()

    response = auth_client.get(f"/api/projects/{project_id}/results")
    assert response.status_code == 200
    data = response.json()
    assert data["stats"]["total"] == 3
    assert len(data["responses"]) == 3
    cleanup_database()


def test_results_nonexistent_project(auth_client):
    response = auth_client.get("/api/projects/99999/results")
    assert response.status_code == 404
