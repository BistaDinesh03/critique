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


def create_project(client, title="Test Project"):
    payload = {
        "project_data": {
            "title": title,
            "description": "A test project",
            "url": None,
            "image_url": None,
        },
        "question_data": {
            "text": "Test question?",
        },
    }
    return client.post("/api/projects/", json=payload)


def test_delete_own_project(auth_client):
    """Test that owner can delete their project."""
    create_resp = create_project(auth_client)
    project_id = create_resp.json()["project"]["id"]

    response = auth_client.delete(f"/api/projects/{project_id}")
    assert response.status_code == 204
    cleanup_database()


def test_delete_other_users_project(auth_client):
    """Test that non-owner cannot delete someone else's project."""
    # Create a project as the current user (fixture user)
    create_resp = create_project(auth_client)
    project_id = create_resp.json()["project"]["id"]
    
    # Get the owner_id of the project
    db = SessionLocal()
    project = db.query(Project).filter(Project.id == project_id).first()
    owner_id = project.owner_id
    
    # Create a second user
    second_user = User(github_id=777777, username="other_user_test")
    db.add(second_user)
    db.commit()
    db.refresh(second_user)
    second_user_id = second_user.id
    db.close()
    
    # Verify second user has different ID
    assert second_user_id != owner_id, f"Test setup error: owner_id={owner_id}, second_user_id={second_user_id}"
    
    # Create a second client with the second user
    from fastapi.testclient import TestClient
    from app.main import app
    from app.auth import get_current_user
    from app.database import SessionLocal as SL
    
    db2 = SL()
    fresh_second_user = db2.query(User).filter(User.id == second_user_id).first()
    db2.close()
    
    app.dependency_overrides[get_current_user] = lambda: fresh_second_user
    client2 = TestClient(app)
    
    try:
        response = client2.delete(f"/api/projects/{project_id}")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    finally:
        app.dependency_overrides.clear()
    
    cleanup_database()


def test_delete_nonexistent_project(auth_client):
    """Test that deleting nonexistent project returns 404."""
    response = auth_client.delete("/api/projects/99999")
    assert response.status_code == 404
    cleanup_database()
