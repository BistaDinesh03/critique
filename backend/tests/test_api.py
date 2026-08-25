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


def test_create_project_with_question():
    """Test creating a project with a question via API."""
    cleanup_database()

    payload = {
        "project_data": {
            "title": "Akiya Scout",
            "description": "Find abandoned houses in Japan",
            "url": "https://akiya-scout.example.com",
            "image_url": None,
        },
        "question_data": {
            "text": "Can you understand what this website does within 10 seconds?",
        },
    }

    response = client.post("/api/projects/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["project"]["title"] == "Akiya Scout"
    assert data["question"]["text"] == "Can you understand what this website does within 10 seconds?"
    assert data["question"]["is_active"] == True

    cleanup_database()


def test_list_projects():
    """Test listing projects via API."""
    cleanup_database()

    # Create a project first
    payload = {
        "project_data": {
            "title": "Akiya Scout",
            "description": "Find abandoned houses in Japan",
            "url": "https://akiya-scout.example.com",
            "image_url": None,
        },
        "question_data": {
            "text": "Can you understand what this website does within 10 seconds?",
        },
    }
    client.post("/api/projects/", json=payload)

    # List projects
    response = client.get("/api/projects/")
    assert response.status_code == 200
    projects = response.json()
    assert len(projects) == 1
    assert projects[0]["title"] == "Akiya Scout"

    cleanup_database()


def test_get_project_with_question():
    """Test getting a project with its active question via API."""
    cleanup_database()

    # Create a project first
    payload = {
        "project_data": {
            "title": "Akiya Scout",
            "description": "Find abandoned houses in Japan",
            "url": "https://akiya-scout.example.com",
            "image_url": None,
        },
        "question_data": {
            "text": "Can you understand what this website does within 10 seconds?",
        },
    }
    create_response = client.post("/api/projects/", json=payload)
    project_id = create_response.json()["project"]["id"]

    # Get the project
    response = client.get(f"/api/projects/{project_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["project"]["id"] == project_id
    assert data["project"]["title"] == "Akiya Scout"
    assert data["question"]["text"] == "Can you understand what this website does within 10 seconds?"

    cleanup_database()


def test_validation_rejects_empty_title():
    """Test that empty title is rejected."""
    cleanup_database()

    payload = {
        "project_data": {
            "title": "",
            "description": "Test",
            "url": "https://example.com",
            "image_url": None,
        },
        "question_data": {
            "text": "Test question?",
        },
    }

    response = client.post("/api/projects/", json=payload)
    assert response.status_code == 422  # Validation error

    cleanup_database()
