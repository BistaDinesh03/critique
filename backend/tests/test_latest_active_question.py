"""Regression coverage for selecting the latest active question in project lists."""

from datetime import datetime
import uuid

from fastapi.testclient import TestClient

from app.auth import get_current_user, get_current_user_optional
from app.database import SessionLocal, init_db
from app.main import app
from app.models import Project, Question, User


def test_project_lists_use_latest_active_question_without_duplicates(monkeypatch):
    """Creation time, not alphabetical text, selects one question per project."""
    init_db()
    db = SessionLocal()
    owner = User(username="latest_question_" + uuid.uuid4().hex[:8])
    db.add(owner)
    db.commit()

    project = Project(
        title="Latest question regression " + uuid.uuid4().hex[:8],
        description="Regression coverage for active question selection.",
        owner_id=owner.id,
        feedback_count=0,
        discover_impressions=0,
    )
    db.add(project)
    db.commit()

    older = Question(
        text="zzzz-asked-first-but-alphabetically-last",
        project_id=project.id,
        is_active=True,
        created_at=datetime(2020, 1, 1),
    )
    newer = Question(
        text="aaaa-asked-last-but-alphabetically-first",
        project_id=project.id,
        is_active=True,
        created_at=datetime(2021, 1, 1),
    )
    db.add_all([older, newer])
    db.commit()

    monkeypatch.setitem(app.dependency_overrides, get_current_user_optional, lambda: None)
    client = TestClient(app)
    project_id = project.id
    expected_text = newer.text

    try:
        discover = client.get("/api/projects/?page=1&page_size=50")
        assert discover.status_code == 200, discover.text
        discover_items = [
            item for item in discover.json()["items"] if item["id"] == project_id
        ]
        assert len(discover_items) == 1
        assert discover_items[0]["question_text"] == expected_text

        monkeypatch.setitem(app.dependency_overrides, get_current_user, lambda: owner)
        my_projects = client.get("/api/projects/my/list")
        assert my_projects.status_code == 200, my_projects.text
        owned_items = [
            item for item in my_projects.json() if item["id"] == project_id
        ]
        assert len(owned_items) == 1
        assert owned_items[0]["question_text"] == expected_text
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_current_user_optional, None)
        db.query(Question).filter(Question.project_id == project_id).delete(
            synchronize_session=False
        )
        db.query(Project).filter(Project.id == project_id).delete(
            synchronize_session=False
        )
        db.query(User).filter(User.id == owner.id).delete(synchronize_session=False)
        db.commit()
        db.close()
