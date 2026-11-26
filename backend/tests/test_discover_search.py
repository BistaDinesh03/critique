"""Backend tests for Discover keyword search (#277)."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth import get_current_user, get_current_user_optional
from app.database import SessionLocal, init_db
from app.main import app
from app.models import Project, Question, User

client = TestClient(app)


def _cleanup(db, user_ids, project_ids, question_ids):
    if question_ids:
        db.query(Question).filter(Question.id.in_(question_ids)).delete(synchronize_session=False)
    if project_ids:
        db.query(Project).filter(Project.id.in_(project_ids)).delete(synchronize_session=False)
    if user_ids:
        db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
    db.commit()


@pytest.fixture
def search_seed():
    init_db()
    db = SessionLocal()
    user_ids = []
    project_ids = []
    question_ids = []

    def make_user():
        u = User(username=f"searcher_{uuid.uuid4().hex[:8]}")
        db.add(u)
        db.commit()
        user_ids.append(u.id)
        return u

    def make_project(owner, title, description, question_text):
        p = Project(title=title, description=description, url="https://example.com", owner_id=owner.id)
        db.add(p)
        db.commit()
        project_ids.append(p.id)
        q = Question(text=question_text, project_id=p.id, is_active=True)
        db.add(q)
        db.commit()
        question_ids.append(q.id)
        return p

    owner = make_user()
    make_project(owner, "Weather Forecast App", "A tiny forecast tool", "Is the forecast clear?")
    make_project(owner, "Notes CLI", "Plain-text note manager", "Does the CLI feel intuitive?")
    make_project(owner, "Budget Tracker", "Track monthly expenses", "Is the chart readable?")
    make_project(owner, "Underscore_Project", "Has an underscore", "Question with underscore")
    make_project(owner, "Backslash\\Project", "Has a backslash", "Question with backslash")

    try:
        yield db
    finally:
        _cleanup(db, user_ids, project_ids, question_ids)
        db.close()


def _titles(resp):
    return [item["title"] for item in resp.json()["items"]]


def test_search_matches_title(search_seed):
    r = client.get("/api/projects/?search=weather")
    assert r.status_code == 200
    assert "Weather Forecast App" in _titles(r)
    assert "Notes CLI" not in _titles(r)


def test_search_matches_description(search_seed):
    r = client.get("/api/projects/?search=expenses")
    assert r.status_code == 200
    assert "Budget Tracker" in _titles(r)


def test_search_matches_question(search_seed):
    r = client.get("/api/projects/?search=intuitive")
    assert r.status_code == 200
    assert "Notes CLI" in _titles(r)


def test_search_is_case_insensitive(search_seed):
    r = client.get("/api/projects/?search=WEATHER")
    assert r.status_code == 200
    assert "Weather Forecast App" in _titles(r)


def test_search_no_results(search_seed):
    r = client.get("/api/projects/?search=zzzznotfound")
    assert r.status_code == 200
    assert r.json()["items"] == []
    assert r.json()["total"] == 0


def test_search_empty_query_behaves_like_unfiltered(search_seed):
    r = client.get("/api/projects/?search=")
    assert r.status_code == 200
    assert r.json()["total"] == 5


def test_search_whitespace_only_behaves_like_unfiltered(search_seed):
    r = client.get("/api/projects/?search=%20%20")
    assert r.status_code == 200
    assert r.json()["total"] == 5


def test_search_pagination(search_seed):
    r = client.get("/api/projects/?search=Project&page_size=1&page=1")
    assert r.status_code == 200
    assert r.json()["page_size"] == 1
    # Two titles contain "Project"; pagination should split them.
    assert len(r.json()["items"]) == 1
    r2 = client.get("/api/projects/?search=Project&page_size=1&page=2")
    assert r2.status_code == 200
    assert len(r2.json()["items"]) == 1


def test_search_wildcard_is_literal(search_seed):
    # A search for "%" should not match everything.
    r = client.get("/api/projects/?search=%25")
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_search_underscore_is_literal(search_seed):
    # "_" must not act as a single-character wildcard.
    r = client.get("/api/projects/?search=_")
    assert r.status_code == 200
    assert "Underscore_Project" in _titles(r)
    # A title without an underscore must not be matched by the wildcard.
    assert "Weather Forecast App" not in _titles(r)


def test_search_backslash_is_literal(search_seed):
    # A backslash must be matched literally, not as an escape that breaks parsing.
    r = client.get("/api/projects/?search=%5C")
    assert r.status_code == 200
    assert "Backslash\\Project" in _titles(r)


def test_search_max_length_rejected():
    long_q = "a" * 101
    r = client.get(f"/api/projects/?search={long_q}")
    assert r.status_code == 422