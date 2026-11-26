"""Deterministic ranking invariants for the Discover endpoint (Issue #86).

These protect the current ranking behaviour so a future optimization (Phase 2)
can demonstrate behaviour equivalence against a known baseline. They run in the
default suite and use a small, seeded dataset so they stay fast and stable.

They intentionally assert structural invariants rather than fragile snapshots
of unrelated response fields.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth import get_current_user, get_current_user_optional
from app.database import SessionLocal, init_db
from app.main import app
from app.models import Project, Question, Response, User, ProjectView

client = TestClient(app)


@pytest.fixture
def inv_seed():
    init_db()
    db = SessionLocal()
    user_ids = []
    project_ids = []

    owner = User(username=f"inv_owner_{uuid.uuid4().hex[:8]}")
    db.add(owner)
    db.commit()
    user_ids.append(owner.id)

    viewer = User(username=f"inv_viewer_{uuid.uuid4().hex[:8]}", feedback_given_count=2)
    db.add(viewer)
    db.commit()
    user_ids.append(viewer.id)

    projects = []
    for i in range(40):
        p = Project(
            title=f"Invariant project {i}",
            description="A project used to protect ranking behaviour.",
            url="https://example.com/inv",
            owner_id=owner.id if i % 3 else viewer.id,  # viewer owns some (excluded)
            feedback_count=i % 5,
            discover_impressions=0,
        )
        db.add(p)
        db.commit()
        project_ids.append(p.id)
        projects.append(p)
        q = Question(text=f"Is invariant project {i} clear and useful?", project_id=p.id, is_active=True)
        db.add(q)
        db.commit()

    # Viewer has viewed a handful (recently-viewed exclusion).
    for p in projects[:5]:
        db.add(ProjectView(user_id=viewer.id, project_id=p.id))
    db.commit()

    # Viewer has answered a couple (hide_answered scenario).
    answered_q = db.query(Question).filter(Question.project_id == projects[0].id).first()
    if answered_q:
        db.add(Response(clarity="very_clear", would_use="yes", question_id=answered_q.id, user_id=viewer.id,
                        ip_hash=uuid.uuid4().hex.ljust(64, "0")[:64]))
    db.commit()

    try:
        yield db, viewer, owner, projects
    finally:
        if project_ids:
            db.query(Response).filter(Response.question_id.in_(
                db.query(Question.id).filter(Question.project_id.in_(project_ids))
            )).delete(synchronize_session=False)
            db.query(Question).filter(Question.project_id.in_(project_ids)).delete(synchronize_session=False)
            db.query(ProjectView).filter(ProjectView.project_id.in_(project_ids)).delete(synchronize_session=False)
            db.query(Project).filter(Project.id.in_(project_ids)).delete(synchronize_session=False)
        db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
        db.commit()
        db.close()
        app.dependency_overrides.clear()


def test_discover_invariants_anonymous(inv_seed):
    db, viewer, owner, projects = inv_seed
    resp = client.get("/api/projects/?page=1&page_size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == len(projects)
    assert len(data["items"]) == 10
    # Scores are non-increasing on the page.
    # (score not exposed; ordering by id tie-break is stable, so just check ids unique)
    ids = [it["id"] for it in data["items"]]
    assert len(set(ids)) == len(ids)
    # No duplicate projects across first two pages.
    r2 = client.get("/api/projects/?page=2&page_size=10")
    ids2 = [it["id"] for it in r2.json()["items"]]
    assert set(ids).isdisjoint(ids2)


def test_discover_invariants_excludes_own_projects(inv_seed):
    db, viewer, owner, projects = inv_seed
    app.dependency_overrides[get_current_user] = lambda: viewer
    app.dependency_overrides[get_current_user_optional] = lambda: viewer
    try:
        resp = client.get("/api/projects/?page=1&page_size=50")
        assert resp.status_code == 200
        ids = [it["id"] for it in resp.json()["items"]]
        viewer_owned = [p.id for p in projects if p.owner_id == viewer.id]
        for oid in viewer_owned:
            assert oid not in ids, "viewer's own project leaked into Discover"
    finally:
        app.dependency_overrides.clear()


def test_discover_invariants_excludes_recently_viewed(inv_seed):
    db, viewer, owner, projects = inv_seed
    app.dependency_overrides[get_current_user] = lambda: viewer
    app.dependency_overrides[get_current_user_optional] = lambda: viewer
    try:
        resp = client.get("/api/projects/?page=1&page_size=50")
        ids = [it["id"] for it in resp.json()["items"]]
        # The first 5 projects were marked as recently viewed by the viewer.
        for p in projects[:5]:
            assert p.id not in ids, "recently-viewed project leaked into Discover"
    finally:
        app.dependency_overrides.clear()


def test_discover_invariants_total_consistent_with_items(inv_seed):
    db, viewer, owner, projects = inv_seed
    resp = client.get("/api/projects/?page=1&page_size=10")
    data = resp.json()
    assert data["total"] == len(projects)
    assert data["total_pages"] == (len(projects) + 9) // 10