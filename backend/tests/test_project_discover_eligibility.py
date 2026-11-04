"""Regression coverage for Discover eligibility and view tracking."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.auth import get_current_user_optional
from app.database import SessionLocal, init_db
from app.main import app
from app.models import Project, ProjectView, Question, Response, User


@pytest.fixture
def discover_context():
    init_db()
    db = SessionLocal()
    suffix = uuid.uuid4().hex[:8]
    viewer = User(username=f"discover_viewer_{suffix}")
    db.add(viewer)
    db.commit()
    db.refresh(viewer)
    created_user_ids = [viewer.id]
    created_project_ids = []

    def seed_project(owner, title):
        project = Project(
            title=title,
            description="Discover eligibility regression test",
            url=f"https://example.com/{uuid.uuid4().hex}",
            owner_id=owner.id,
            feedback_count=0,
            discover_impressions=0,
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        question = Question(
            text=f"Is {title} clear?",
            project_id=project.id,
            is_active=True,
        )
        db.add(question)
        db.commit()
        created_project_ids.append(project.id)
        return project

    def seed_owner(name):
        owner = User(username=f"{name}_{suffix}_{len(created_user_ids)}")
        db.add(owner)
        db.commit()
        db.refresh(owner)
        created_user_ids.append(owner.id)
        return owner

    app.dependency_overrides[get_current_user_optional] = lambda: viewer
    client = TestClient(app)
    try:
        yield {"db": db, "viewer": viewer, "client": client,
               "seed_owner": seed_owner, "seed_project": seed_project}
    finally:
        app.dependency_overrides.pop(get_current_user_optional, None)
        db.query(ProjectView).filter(
            ProjectView.project_id.in_(created_project_ids)
        ).delete(synchronize_session=False)
        db.query(Response).filter(
            Response.question_id.in_(
                db.query(Question.id).filter(Question.project_id.in_(created_project_ids))
            )
        ).delete(synchronize_session=False)
        db.query(Question).filter(
            Question.project_id.in_(created_project_ids)
        ).delete(synchronize_session=False)
        db.query(Project).filter(Project.id.in_(created_project_ids)).delete(
            synchronize_session=False
        )
        db.query(ProjectView).filter(
            ProjectView.user_id.in_(created_user_ids)
        ).delete(synchronize_session=False)
        db.query(User).filter(User.id.in_(created_user_ids)).delete(
            synchronize_session=False
        )
        db.commit()
        db.close()


def test_discover_excludes_current_users_own_projects(discover_context):
    ctx = discover_context
    own = ctx["seed_project"](ctx["viewer"], "Viewer owned project")
    other = ctx["seed_project"](ctx["seed_owner"]("other_owner"), "Another owner's project")

    response = ctx["client"].get("/api/projects/?page=1&page_size=10")

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert own.id not in ids
    assert other.id in ids


def test_discover_excludes_recently_viewed_projects_and_records_view(discover_context):
    ctx = discover_context
    project = ctx["seed_project"](ctx["seed_owner"]("viewed_owner"), "Recently viewed project")

    detail = ctx["client"].get(f"/api/projects/{project.id}")
    assert detail.status_code == 200

    view = ctx["db"].query(ProjectView).filter(
        ProjectView.user_id == ctx["viewer"].id,
        ProjectView.project_id == project.id,
    ).first()
    assert view is not None
    assert view.viewed_at.replace(tzinfo=timezone.utc) >= datetime.now(timezone.utc) - timedelta(hours=24)

    response = ctx["client"].get("/api/projects/?page=1&page_size=10")
    assert response.status_code == 200
    assert project.id not in {item["id"] for item in response.json()["items"]}


def test_discover_limits_each_owner_to_one_project_in_first_six(discover_context):
    ctx = discover_context
    repeat_owner = ctx["seed_owner"]("repeat_owner")
    repeated = [
        ctx["seed_project"](repeat_owner, f"Repeated owner project {index}")
        for index in range(2)
    ]
    for index in range(6):
        ctx["seed_project"](ctx["seed_owner"](f"unique_owner_{index}"), f"Unique project {index}")

    response = ctx["client"].get("/api/projects/?page=1&page_size=50")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 8
    first_six_owner_ids = [item["owner_id"] for item in items[:6]]
    assert len(first_six_owner_ids) == len(set(first_six_owner_ids))
    repeated_positions = [
        index for index, item in enumerate(items) if item["id"] in {p.id for p in repeated}
    ]
    assert len(repeated_positions) == 2
    assert sum(position < 6 for position in repeated_positions) == 1
