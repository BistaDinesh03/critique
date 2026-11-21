"""Backend tests for the Discover "Hide projects I've answered" filter (#840)."""

import math
import uuid
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from app.auth import get_current_user, get_current_user_optional
from app.database import SessionLocal, engine, init_db
from app.main import app
from app.models import Project, Question, Response, User

client = TestClient(app)

BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"


def _list_as(user, url):
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_user_optional] = lambda: user
    try:
        return client.get(url)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_current_user_optional, None)


@pytest.fixture
def sql_statements():
    captured = []

    def _record(conn, cursor, statement, parameters, context, executemany):
        captured.append(" ".join(statement.split()))

    event.listen(engine, "before_cursor_execute", _record)
    try:
        yield captured
    finally:
        event.remove(engine, "before_cursor_execute", _record)


@pytest.fixture
def seed_discover_data():
    """Seed owners, projects, questions, and responses; clean up afterwards."""
    init_db()
    db = SessionLocal()
    created_users = []
    created_projects = []
    created_questions = []
    created_responses = []

    def _make_user(prefix="u"):
        user = User(username=f"{prefix}_{uuid.uuid4().hex[:8]}")
        db.add(user)
        db.commit()
        created_users.append(user.id)
        return user

    def _make_project(owner, title="Project", question_text="Is this clear?", is_active=True, created_at=None):
        project = Project(
            title=title,
            description="Test description",
            url="https://example.com/project",
            owner_id=owner.id,
            feedback_count=0,
            discover_impressions=0,
        )
        db.add(project)
        db.commit()
        created_projects.append(project.id)

        q_kwargs = dict(text=question_text, project_id=project.id, is_active=is_active)
        if created_at is not None:
            q_kwargs["created_at"] = created_at
        question = Question(**q_kwargs)
        db.add(question)
        db.commit()
        created_questions.append(question.id)
        return project, question

    def _add_question(project, text, is_active=True, created_at=None):
        q_kwargs = dict(text=text, project_id=project.id, is_active=is_active)
        if created_at is not None:
            q_kwargs["created_at"] = created_at
        question = Question(**q_kwargs)
        db.add(question)
        db.commit()
        created_questions.append(question.id)
        return question

    def _add_response(question, user):
        resp = Response(
            clarity="very_clear",
            would_use="yes",
            suggestion="Helpful feedback",
            question_id=question.id,
            user_id=user.id,
            ip_hash=uuid.uuid4().hex.ljust(64, "0")[:64],
        )
        db.add(resp)
        db.commit()
        created_responses.append(resp.id)
        return resp

    try:
        yield {
            "db": db,
            "make_user": _make_user,
            "make_project": _make_project,
            "add_question": _add_question,
            "add_response": _add_response,
        }
    finally:
        if created_responses:
            db.query(Response).filter(Response.id.in_(created_responses)).delete(synchronize_session=False)
        if created_questions:
            db.query(Question).filter(Question.id.in_(created_questions)).delete(synchronize_session=False)
        if created_projects:
            db.query(Project).filter(Project.id.in_(created_projects)).delete(synchronize_session=False)
        if created_users:
            db.query(User).filter(User.id.in_(created_users)).delete(synchronize_session=False)
        db.commit()
        db.close()


# ---------------------------------------------------------------------------
# Backend API tests
# ---------------------------------------------------------------------------


def test_hide_answered_excludes_answered_projects_for_signed_in_user(seed_discover_data):
    owner = seed_discover_data["make_user"]("owner")
    viewer = seed_discover_data["make_user"]("viewer")
    other = seed_discover_data["make_user"]("other")

    p_answered, q_answered = seed_discover_data["make_project"](owner, "Answered by viewer")
    p_other, q_other = seed_discover_data["make_project"](owner, "Answered by other")
    p_unanswered, _ = seed_discover_data["make_project"](owner, "Unanswered")

    seed_discover_data["add_response"](q_answered, viewer)
    seed_discover_data["add_response"](q_other, other)

    # Default (hide_answered=false): includes answered project with has_responded=True
    default_resp = _list_as(viewer, "/api/projects/?page=1&page_size=50")
    assert default_resp.status_code == 200
    default_body = default_resp.json()
    default_by_id = {item["id"]: item for item in default_body["items"]}
    assert p_answered.id in default_by_id
    assert default_by_id[p_answered.id]["has_responded"] is True
    assert p_other.id in default_by_id
    assert default_by_id[p_other.id]["has_responded"] is False
    assert p_unanswered.id in default_by_id
    assert default_by_id[p_unanswered.id]["has_responded"] is False

    # With hide_answered=true: answered project excluded, others remain
    filtered_resp = _list_as(viewer, "/api/projects/?page=1&page_size=50&hide_answered=true")
    assert filtered_resp.status_code == 200
    filtered_body = filtered_resp.json()
    filtered_ids = {item["id"] for item in filtered_body["items"]}
    assert p_answered.id not in filtered_ids
    assert p_other.id in filtered_ids
    assert p_unanswered.id in filtered_ids
    assert all(item["has_responded"] is False for item in filtered_body["items"])
    assert filtered_body["total"] == default_body["total"] - 1


def test_hide_answered_does_not_hide_on_inactive_or_superseded_question(seed_discover_data):
    owner = seed_discover_data["make_user"]("owner")
    viewer = seed_discover_data["make_user"]("viewer")

    # Project 1: answered an inactive question; has a newer active question
    p_inactive, q_inactive = seed_discover_data["make_project"](
        owner, "Inactive question project", "Old inactive?", is_active=False, created_at=datetime(2020, 1, 1)
    )
    seed_discover_data["add_question"](
        p_inactive, "Current active?", is_active=True, created_at=datetime(2021, 1, 1)
    )
    seed_discover_data["add_response"](q_inactive, viewer)

    # Project 2: answered an older active question superseded by a newer active question
    p_superseded, q_old_active = seed_discover_data["make_project"](
        owner, "Superseded question project", "Old active?", is_active=True, created_at=datetime(2020, 1, 1)
    )
    seed_discover_data["add_question"](
        p_superseded, "New active?", is_active=True, created_at=datetime(2021, 1, 1)
    )
    seed_discover_data["add_response"](q_old_active, viewer)

    # Project 3: answered the latest active question -> should be hidden
    p_current, q_current = seed_discover_data["make_project"](owner, "Current answered")
    seed_discover_data["add_response"](q_current, viewer)

    resp = _list_as(viewer, "/api/projects/?page=1&page_size=50&hide_answered=true")
    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()["items"]}
    assert p_inactive.id in ids
    assert p_superseded.id in ids
    assert p_current.id not in ids


def test_hide_answered_ignored_for_anonymous_with_no_extra_queries(sql_statements, seed_discover_data):
    owner = seed_discover_data["make_user"]("owner")
    viewer = seed_discover_data["make_user"]("viewer")

    p1, q1 = seed_discover_data["make_project"](owner, "Anon project 1")
    p2, _ = seed_discover_data["make_project"](owner, "Anon project 2")
    seed_discover_data["add_response"](q1, viewer)

    baseline = client.get("/api/projects/?page=1&page_size=50").json()
    baseline_ids = [item["id"] for item in baseline["items"]]

    sql_statements.clear()
    resp = client.get("/api/projects/?page=1&page_size=50&hide_answered=true")
    assert resp.status_code == 200
    body = resp.json()

    selects = [s for s in sql_statements if s.upper().startswith("SELECT")]
    assert len(selects) == 1, f"expected 1 SELECT for anonymous hide_answered=true, got {len(selects)}: {selects}"
    assert [item["id"] for item in body["items"]] == baseline_ids
    assert {p1.id, p2.id} <= set(baseline_ids)


def test_hide_answered_multipage_pagination_accurate_without_gaps(seed_discover_data):
    viewer = seed_discover_data["make_user"]("viewer")
    seeded = []
    for i in range(10):
        owner = seed_discover_data["make_user"](f"owner_{i}")
        proj, q = seed_discover_data["make_project"](owner, f"Paged project {i}")
        seeded.append((proj, q))

    # Viewer answers 4 projects spread across the seeded set
    answered_indices = {0, 2, 5, 8}
    answered_ids = set()
    unanswered_ids = set()
    for idx, (proj, q) in enumerate(seeded):
        if idx in answered_indices:
            seed_discover_data["add_response"](q, viewer)
            answered_ids.add(proj.id)
        else:
            unanswered_ids.add(proj.id)

    unfiltered = _list_as(viewer, "/api/projects/?page=1&page_size=3").json()
    expected_total = unfiltered["total"] - len(answered_ids)
    expected_pages = max(1, math.ceil(expected_total / 3))

    collected_ids = []
    for page in range(1, expected_pages + 1):
        resp = _list_as(viewer, f"/api/projects/?page={page}&page_size=3&hide_answered=true")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == expected_total
        assert body["total_pages"] == expected_pages
        assert body["page"] == page
        if page < expected_pages:
            assert len(body["items"]) == 3, f"page {page} was short: {len(body['items'])}"
        else:
            expected_last = expected_total - 3 * (expected_pages - 1)
            assert len(body["items"]) == expected_last
        collected_ids.extend(item["id"] for item in body["items"])

    assert len(collected_ids) == expected_total
    assert len(set(collected_ids)) == expected_total, "duplicate projects across pages"
    assert not (set(collected_ids) & answered_ids), "answered projects leaked into filtered pages"
    assert unanswered_ids <= set(collected_ids), "some unanswered projects missing"


def test_discover_filter_markup_and_mobile_touch_target():
    source = (FRONTEND_DIR / "discover.html").read_text(encoding="utf-8")
    assert 'for="hide-answered-toggle"' in source
    assert "Hide projects I've answered" in source
    assert "Sign in to skip projects you've already answered." in source
    assert "min-height: 44px;" in source
