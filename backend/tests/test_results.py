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
    assert data["is_owner"] is True
    assert len(data["responses"]) == 3
    cleanup_database()


def test_results_nonexistent_project(auth_client):
    response = auth_client.get("/api/projects/99999/results")
    assert response.status_code == 404


def test_results_owner_sees_is_owner_true_with_no_active_question(auth_client):
    create_resp = create_project(auth_client)
    project_id = create_resp.json()["project"]["id"]

    # Delete the question to simulate project without an active question
    db = SessionLocal()
    try:
        db.query(Question).filter(Question.project_id == project_id).delete()
        db.commit()
    finally:
        db.close()

    response = auth_client.get(f"/api/projects/{project_id}/results")
    assert response.status_code == 200
    data = response.json()
    assert data["is_owner"] is True
    assert data["question_text"] is None
    assert data["stats"]["total"] == 0
    assert data["responses"] == []
    cleanup_database()


def test_results_non_owner_sees_is_owner_false_with_no_active_question():
    from fastapi.testclient import TestClient
    from app.main import app

    cleanup_database()
    db = SessionLocal()
    try:
        user = User(github_id=777777, username="owner_user")
        db.add(user)
        db.commit()
        db.refresh(user)
        project = Project(title="No Question Project", description="Test", owner_id=user.id)
        db.add(project)
        db.commit()
        db.refresh(project)
        project_id = project.id
    finally:
        db.close()

    client = TestClient(app)
    response = client.get(f"/api/projects/{project_id}/results")
    assert response.status_code == 200
    data = response.json()
    assert data["is_owner"] is False
    assert data["question_text"] is None
    assert data["stats"]["total"] == 0
    assert data["responses"] == []
    cleanup_database()


def test_export_csv_requires_owner_and_escapes_formulas(auth_client):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.auth import get_current_user

    create_resp = create_project(auth_client)
    project_id = create_resp.json()["project"]["id"]

    # Submit response containing formula trigger characters (=, +, -, @)
    submit_response(auth_client, project_id, "very_clear", "yes", "=cmd|' /C calc'!A0")

    # Anonymous user gets 401 when get_current_user is not overridden
    mock_user = app.dependency_overrides.pop(get_current_user, None)
    try:
        anon_client = TestClient(app)
        anon_resp = anon_client.get(f"/api/projects/{project_id}/results.csv")
        assert anon_resp.status_code == 401
    finally:
        if mock_user:
            app.dependency_overrides[get_current_user] = mock_user

    # Nonexistent project gets 404
    assert auth_client.get("/api/projects/999999/results.csv").status_code == 404

    # Non-owner user gets 403
    db = SessionLocal()
    try:
        non_owner = User(github_id=555555, username="other_user")
        db.add(non_owner)
        db.commit()
        db.refresh(non_owner)
    finally:
        db.close()

    try:
        app.dependency_overrides[get_current_user] = lambda: non_owner
        assert anon_client.get(f"/api/projects/{project_id}/results.csv").status_code == 403
    finally:
        app.dependency_overrides[get_current_user] = mock_user

    # Owner gets 200 with text/csv, attachment header, and neutralized formulas
    resp = auth_client.get(f"/api/projects/{project_id}/results.csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert f'filename="project-{project_id}-feedback.csv"' in resp.headers["content-disposition"]
    lines = resp.text.strip().splitlines()
    assert lines[0] == "created_at,clarity,would_use,suggestion"
    assert len(lines) == 2
    # The formula =cmd... must be neutralized with a leading single quote
    assert "'=cmd|' /C calc'!A0" in lines[1]
    cleanup_database()




