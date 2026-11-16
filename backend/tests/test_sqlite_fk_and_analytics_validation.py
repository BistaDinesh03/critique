"""Analytics project_id validation and SQLite foreign-key enforcement (#109)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal, init_db
from app.main import app
from app.models import AnalyticsEvent, Project, Question, User

client = TestClient(app)


@pytest.fixture
def db():
    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _unique_username(prefix):
    return prefix + uuid.uuid4().hex[:12]


def test_sqlite_foreign_keys_are_enabled(db):
    """SQLite connections must enforce foreign keys."""
    result = db.execute(text("PRAGMA foreign_keys")).scalar()
    assert result == 1, "PRAGMA foreign_keys is not ON"


def test_sqlite_rejects_dangling_question_reference(db):
    """A child row pointing at a missing parent must be rejected."""
    question = Question(text="Orphan?", project_id=999999)
    db.add(question)
    try:
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()


def test_track_event_rejects_unknown_project_id(db):
    response = client.post(
        "/api/analytics/track?event_name=page_view&project_id=999999"
    )
    assert response.status_code == 200
    assert response.json()["ok"] is False


def test_track_event_accepts_existing_project_id(db):
    owner = User(username=_unique_username("track_owner_"))
    db.add(owner)
    db.commit()
    db.refresh(owner)
    project = Project(title="Track Test", owner_id=owner.id)
    db.add(project)
    db.commit()
    db.refresh(project)

    try:
        response = client.post(
            f"/api/analytics/track?event_name=page_view&project_id={project.id}"
        )
        assert response.status_code == 200
        assert response.json()["ok"] is True
    finally:
        db.query(AnalyticsEvent).filter(AnalyticsEvent.project_id == project.id).delete()
        db.query(Project).filter(Project.id == project.id).delete()
        db.delete(owner)
        db.commit()


def test_track_event_accepts_no_project_id(db):
    response = client.post("/api/analytics/track?event_name=page_view")
    assert response.status_code == 200
    assert response.json()["ok"] is True
