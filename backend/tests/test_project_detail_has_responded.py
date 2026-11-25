"""Project detail has_responded: API contract, query budget, and UI rendering."""

import json
import shutil
import subprocess
import uuid
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from app.auth import get_current_user, get_current_user_optional
from app.database import SessionLocal, engine, init_db
from app.main import app
from app.models import Project, ProjectView, Question, Response, User

BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"
HARNESS = Path(__file__).resolve().parent / "frontend_render_harness.js"

pytestmark = [
    pytest.mark.frontend_render,
    pytest.mark.skipif(shutil.which("node") is None, reason="node is required"),
]

client = TestClient(app)


def _get_as(user, project_id):
    def _override():
        return user

    app.dependency_overrides[get_current_user] = _override
    app.dependency_overrides[get_current_user_optional] = _override
    try:
        return client.get(f"/api/projects/{project_id}")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_current_user_optional, None)


@pytest.fixture
def detail_fixture():
    """Create owner, reviewer, other user, project, and active question; clean up after."""
    init_db()
    db = SessionLocal()
    tag = uuid.uuid4().hex[:8]
    owner = User(username=f"detail_owner_{tag}")
    reviewer = User(username=f"detail_reviewer_{tag}")
    other = User(username=f"detail_other_{tag}")
    db.add_all([owner, reviewer, other])
    db.commit()

    project = Project(
        title=f"Detail Project {tag}",
        description="Test project for has_responded",
        url="https://example.com/detail",
        owner_id=owner.id,
    )
    db.add(project)
    db.commit()

    question = Question(
        text="Is this clear?",
        project_id=project.id,
        is_active=True,
        created_at=datetime(2025, 1, 1),
    )
    db.add(question)
    db.commit()
    db.refresh(owner)
    db.refresh(reviewer)
    db.refresh(other)
    db.refresh(project)
    db.refresh(question)

    yield {
        "db": db,
        "owner": owner,
        "reviewer": reviewer,
        "other": other,
        "project": project,
        "question": question,
    }

    q_ids = [
        row[0]
        for row in db.query(Question.id).filter(Question.project_id == project.id).all()
    ]
    if q_ids:
        db.query(Response).filter(Response.question_id.in_(q_ids)).delete(
            synchronize_session=False
        )
    db.query(ProjectView).filter(ProjectView.project_id == project.id).delete(
        synchronize_session=False
    )
    db.query(Question).filter(Question.project_id == project.id).delete(
        synchronize_session=False
    )
    db.query(Project).filter(Project.id == project.id).delete(synchronize_session=False)
    db.query(User).filter(User.id.in_([owner.id, reviewer.id, other.id])).delete(
        synchronize_session=False
    )
    db.commit()
    db.close()


def test_get_project_has_responded_true_when_user_answered_active_question(detail_fixture):
    db = detail_fixture["db"]
    reviewer = detail_fixture["reviewer"]
    project = detail_fixture["project"]
    question = detail_fixture["question"]

    db.add(
        Response(
            question_id=question.id,
            user_id=reviewer.id,
            clarity="very_clear",
            would_use="yes",
            ip_hash="a" * 64,
        )
    )
    db.commit()

    resp = _get_as(reviewer, project.id)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_owner"] is False
    assert data["has_responded"] is True


def test_get_project_has_responded_false_when_user_not_answered(detail_fixture):
    db = detail_fixture["db"]
    reviewer = detail_fixture["reviewer"]
    other = detail_fixture["other"]
    project = detail_fixture["project"]
    question = detail_fixture["question"]

    db.add(
        Response(
            question_id=question.id,
            user_id=other.id,
            clarity="very_clear",
            would_use="yes",
            ip_hash="b" * 64,
        )
    )
    db.commit()

    resp = _get_as(reviewer, project.id)
    assert resp.status_code == 200
    assert resp.json()["has_responded"] is False


def test_get_project_has_responded_false_when_user_answered_inactive_question(detail_fixture):
    db = detail_fixture["db"]
    reviewer = detail_fixture["reviewer"]
    project = detail_fixture["project"]
    old_question = detail_fixture["question"]

    db.add(
        Response(
            question_id=old_question.id,
            user_id=reviewer.id,
            clarity="mostly_clear",
            would_use="maybe",
            ip_hash="c" * 64,
        )
    )
    old_question.is_active = False
    new_question = Question(
        text="Updated active question?",
        project_id=project.id,
        is_active=True,
        created_at=datetime(2025, 2, 1),
    )
    db.add(new_question)
    db.commit()

    resp = _get_as(reviewer, project.id)
    assert resp.status_code == 200
    data = resp.json()
    assert data["question"]["id"] == new_question.id
    assert data["has_responded"] is False


def test_get_project_has_responded_accurate_for_owner(detail_fixture):
    db = detail_fixture["db"]
    owner = detail_fixture["owner"]
    project = detail_fixture["project"]
    question = detail_fixture["question"]

    before = _get_as(owner, project.id)
    assert before.status_code == 200
    assert before.json()["is_owner"] is True
    assert before.json()["has_responded"] is False

    db.add(
        Response(
            question_id=question.id,
            user_id=owner.id,
            clarity="very_clear",
            would_use="yes",
            ip_hash="d" * 64,
        )
    )
    db.commit()

    after = _get_as(owner, project.id)
    assert after.status_code == 200
    assert after.json()["is_owner"] is True
    assert after.json()["has_responded"] is True


def test_get_project_anonymous_has_responded_false_and_no_extra_query(detail_fixture):
    db = detail_fixture["db"]
    reviewer = detail_fixture["reviewer"]
    project = detail_fixture["project"]
    question = detail_fixture["question"]

    db.add_all([
        Response(
            question_id=question.id,
            user_id=None,
            clarity="very_clear",
            would_use="yes",
            ip_hash="e" * 64,
        ),
        Response(
            question_id=question.id,
            user_id=reviewer.id,
            clarity="mostly_clear",
            would_use="maybe",
            ip_hash="f" * 64,
        ),
    ])
    db.commit()

    captured = []

    def _record(conn, cursor, statement, parameters, context, executemany):
        captured.append(" ".join(statement.split()))

    event.listen(engine, "before_cursor_execute", _record)
    try:
        resp = client.get(f"/api/projects/{project.id}")
    finally:
        event.remove(engine, "before_cursor_execute", _record)

    assert resp.status_code == 200
    data = resp.json()
    assert data["is_owner"] is False
    assert data["has_responded"] is False
    user_response_queries = [
        stmt for stmt in captured if "responses.user_id" in stmt.lower()
    ]
    assert user_response_queries == []


# --- Frontend render tests ---------------------------------------------------

_BASE_PROJECT = {
    "id": 1,
    "title": "Pulse Tracker",
    "description": "Tracks build latency",
    "image_url": None,
    "url": None,
    "response_count": 3,
}

_BASE_QUESTION = {
    "id": 10,
    "text": "Is the setup guide clear?",
    "is_active": True,
    "project_id": 1,
}


def _render_detail(tmp_path, calls, fetch=None):
    scenario = {
        "page": (FRONTEND_DIR / "project_detail.html").as_posix(),
        "calls": calls,
        "read": {"byId": "content"},
        "fetch": fetch or {},
        "location": "/project/1",
    }
    scenario_file = tmp_path / "scenario.json"
    scenario_file.write_text(json.dumps(scenario), encoding="utf-8")
    proc = subprocess.run(
        ["node", str(HARNESS), str(scenario_file)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["errors"] == [], result["errors"]
    return result


def test_project_detail_has_responded_shows_already_responded_state_without_form(tmp_path):
    payload = {
        "project": _BASE_PROJECT,
        "question": _BASE_QUESTION,
        "is_owner": False,
        "has_responded": True,
    }
    fetch = {
        "/api/projects/?": {
            "status": 200,
            "body": {"total": 1, "items": [{"id": 2, "title": "Next App"}]},
        },
    }
    result = _render_detail(
        tmp_path,
        [
            {"fn": "setCurrentUserId", "args": ["42"]},
            {"fn": "renderProject", "args": [payload, []]},
        ],
        fetch=fetch,
    )

    assert 'id="response-form"' not in result["html"]
    lines = {
        m["className"]: m["text"]
        for m in result["createdMeta"]
        if m.get("className") and m.get("text")
    }
    assert lines.get("response-done-title", "").endswith(
        "You already gave feedback on this project."
    )
    assert lines.get("response-done-note", "") == "Thanks for helping this builder."
    explore = [
        m
        for m in result["createdMeta"]
        if m.get("id") == "explore-another-project"
    ]
    assert explore
    assert "Explore another project" in explore[0]["text"]
    assert explore[0]["href"] == "/project/2"
    assert result["storage"]["session"].get("critique_responded_42_1") == "1"
    assert "critique_responded_1" not in result["storage"]["session"]


def test_project_detail_guest_still_sees_response_form(tmp_path):
    payload = {
        "project": _BASE_PROJECT,
        "question": _BASE_QUESTION,
        "is_owner": False,
        "has_responded": False,
    }
    result = _render_detail(
        tmp_path,
        [{"fn": "renderProject", "args": [payload, []]}],
    )

    assert 'id="response-form"' in result["html"]
    assert "You already gave feedback" not in " ".join(result["created"])


def test_project_detail_owner_sees_owner_view_even_when_has_responded_true(tmp_path):
    payload = {
        "project": _BASE_PROJECT,
        "question": _BASE_QUESTION,
        "is_owner": True,
        "has_responded": True,
    }
    result = _render_detail(
        tmp_path,
        [{"fn": "renderProject", "args": [payload, []]}],
    )

    assert 'id="response-form"' not in result["html"]
    assert 'id="feedback-thanks"' not in result["html"]
    assert 'id="owner-response-count"' in result["html"]
    # Issue #814 owns the owner markup: an explanatory banner plus the
    # results link (no form, no "already responded" state) -- #846 only
    # asserts the behavioural part above (form and thanks states absent).
    assert 'Project owner' in result["html"]
    assert 'href="/project/1/results"' in result["html"]
    assert "You already gave feedback" not in " ".join(result["created"])
