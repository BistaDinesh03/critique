"""Performance benchmarks for the Discover project-list endpoint (Issue #86).

These are MEASUREMENT-ONLY tests. They do not change ranking or endpoint
behaviour and must never be used to assert timing thresholds in CI.

Run explicitly with::

    RUN_BENCHMARKS=1 python -m pytest tests/test_discover_benchmark.py -v -s

They are skipped by default so they do not slow down or destabilise the normal
suite. Fixture setup queries are excluded from the endpoint measurements: the
SQL-capture listener is attached only around the request under test.
"""

import os
import random
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from app.auth import get_current_user, get_current_user_optional
from app.database import SessionLocal, engine, init_db
from app.main import app
from app.models import Project, Question, Response, User, ProjectView

client = TestClient(app)

RUN_BENCHMARKS = os.environ.get("RUN_BENCHMARKS") == "1"

pytestmark = [
    pytest.mark.benchmark,
    pytest.mark.skipif(not RUN_BENCHMARKS, reason="set RUN_BENCHMARKS=1 to run performance benchmarks"),
]


def _seed_dataset(db, n_projects, seed=20261126):
    """Deterministically seed ``n_projects`` projects with realistic spread.

    Returns (current_user, project_ids). Cleanup is the caller's responsibility
    via the returned ids, or use the fixture below.
    """
    rng = random.Random(seed)
    now = datetime.now(timezone.utc)

    n_owners = max(50, n_projects // 20)
    owners = [User(username=f"bench_owner_{i}_{uuid.uuid4().hex[:4]}") for i in range(n_owners)]
    db.add_all(owners)
    db.flush()

    viewer = User(username=f"bench_viewer_{uuid.uuid4().hex[:8]}")
    db.add(viewer)
    db.flush()

    # ~1% of projects are owned by the viewer (exercised by own-project exclusion).
    viewer_owned = set(rng.sample(range(n_projects), max(1, n_projects // 100)))

    projects = []
    for i in range(n_projects):
        owner = owners[rng.randrange(n_owners)] if i not in viewer_owned else viewer
        age_hours = rng.random() * 720.0  # up to 30 days
        created = now - timedelta(hours=age_hours)
        fb = rng.choice([0, 0, 0, 1, 2, 3, 5, 10])
        p = Project(
            title=f"Bench project {i}",
            description=f"Description for project {i} with several words for search realism",
            url=f"https://example.com/bench/{i}",
            owner_id=owner.id,
            feedback_count=fb,
            discover_impressions=0,
            created_at=created,
        )
        projects.append(p)
    db.add_all(projects)
    db.flush()

    # One active question per project, occasionally a superseded inactive one.
    questions = []
    active_q_by_project = {}
    for p in projects:
        q_active = Question(
            text=f"Is project {p.id} clear and useful to you?",
            project_id=p.id,
            is_active=True,
            created_at=p.created_at + timedelta(hours=1),
        )
        questions.append(q_active)
        active_q_by_project[p.id] = q_active
        if rng.random() < 0.25:
            q_old = Question(
                text=f"Old question for project {p.id}",
                project_id=p.id,
                is_active=False,
                created_at=p.created_at,
            )
            questions.append(q_old)
    db.add_all(questions)
    db.flush()

    # Responses for ~40% of projects, against the active question.
    responses = []
    for p in projects:
        if rng.random() < 0.4:
            n_resp = rng.randint(1, 8)
            for _ in range(n_resp):
                # pick a random responder (not the owner where possible)
                responder = owners[rng.randrange(n_owners)]
                r = Response(
                    clarity=rng.choice(["very_clear", "mostly_clear", "confusing"]),
                    would_use=rng.choice(["yes", "maybe", "no"]),
                    suggestion="Helpful feedback" if rng.random() < 0.5 else None,
                    question_id=active_q_by_project[p.id].id,
                    user_id=responder.id,
                    ip_hash=uuid.uuid4().hex.ljust(64, "0")[:64],
                )
                responses.append(r)
    if responses:
        db.add_all(responses)
        db.flush()

    # Recently viewed: viewer has viewed ~5% of projects in the last 24h.
    viewed = rng.sample(range(n_projects), max(1, n_projects // 20))
    for i in viewed:
        pv = ProjectView(user_id=viewer.id, project_id=projects[i].id, viewed_at=now - timedelta(hours=rng.random() * 12))
        db.add(pv)
    # viewer has answered ~10% of active questions.
    answered = rng.sample(range(n_projects), max(1, n_projects // 10))
    for i in answered:
        r = Response(
            clarity="very_clear",
            would_use="yes",
            question_id=active_q_by_project[projects[i].id].id,
            user_id=viewer.id,
            ip_hash=uuid.uuid4().hex.ljust(64, "0")[:64],
        )
        db.add(r)
    db.commit()

    project_ids = [p.id for p in projects]
    owner_ids = [u.id for u in owners]
    return viewer, project_ids, owner_ids


def _count_sql(captured):
    return len(captured)


def _measure_request(url, auth_user=None):
    """Run one GET and return (sql_count, elapsed_seconds, response)."""
    captured = []

    def _record(conn, cursor, statement, parameters, context, executemany):
        captured.append(" ".join(statement.split()))

    event.listen(engine, "before_cursor_execute", _record)
    try:
        if auth_user is not None:
            app.dependency_overrides[get_current_user] = lambda: auth_user
            app.dependency_overrides[get_current_user_optional] = lambda: auth_user
        t0 = time.perf_counter()
        resp = client.get(url)
        elapsed = time.perf_counter() - t0
        return len(captured), elapsed, resp
    finally:
        event.remove(engine, "before_cursor_execute", _record)
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_current_user_optional, None)


def _cleanup(db, project_ids, user_ids):
    if project_ids:
        # delete responses first
        db.query(Response).filter(Response.question_id.in_(
            db.query(Question.id).filter(Question.project_id.in_(project_ids))
        )).delete(synchronize_session=False)
        db.query(Question).filter(Question.project_id.in_(project_ids)).delete(synchronize_session=False)
        db.query(ProjectView).filter(ProjectView.project_id.in_(project_ids)).delete(synchronize_session=False)
        db.query(Project).filter(Project.id.in_(project_ids)).delete(synchronize_session=False)
    if user_ids:
        db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
    db.commit()


@pytest.mark.benchmark
def test_discover_benchmark_1k():
    _run_benchmark(1000)


@pytest.mark.benchmark
def test_discover_benchmark_10k():
    _run_benchmark(10000)


def _run_benchmark(n):
    init_db()
    db = SessionLocal()
    viewer, project_ids, owner_ids = _seed_dataset(db, n)
    viewer_id = viewer.id
    project_count_before = db.query(Project).count()

    page_size = 10
    print(f"\n=== Discover benchmark: {n} projects ===")
    print(f"environment: python, sqlite, {n} projects seeded")
    print(f"dataset: {project_count_before} project rows in DB")

    # Anonymous, page 1
    sql, elapsed, resp = _measure_request(f"/api/projects/?page=1&page_size={page_size}")
    assert resp.status_code == 200
    data = resp.json()
    print(f"anon page1: sql={sql} projects_loaded={project_count_before} returned={len(data['items'])} total={data['total']} total_pages={data['total_pages']} time={elapsed:.3f}s")

    # Later page
    later_page = max(1, (n // page_size) // 2)
    sql2, elapsed2, resp2 = _measure_request(f"/api/projects/?page={later_page}&page_size={page_size}")
    assert resp2.status_code == 200
    data2 = resp2.json()
    print(f"anon page{later_page}: sql={sql2} returned={len(data2['items'])} time={elapsed2:.3f}s")

    # Authenticated viewer with own projects + recently viewed
    sql3, elapsed3, resp3 = _measure_request(f"/api/projects/?page=1&page_size={page_size}", auth_user=viewer)
    assert resp3.status_code == 200
    data3 = resp3.json()
    print(f"auth page1: sql={sql3} returned={len(data3['items'])} time={elapsed3:.3f}s")

    # Authenticated with hide_answered
    sql4, elapsed4, resp4 = _measure_request(f"/api/projects/?page=1&page_size={page_size}&hide_answered=true", auth_user=viewer)
    assert resp4.status_code == 200
    data4 = resp4.json()
    print(f"auth hide_answered page1: sql={sql4} returned={len(data4['items'])} time={elapsed4:.3f}s")

    # Search query
    sql5, elapsed5, resp5 = _measure_request(f"/api/projects/?page=1&page_size={page_size}&search=project", auth_user=viewer)
    assert resp5.status_code == 200
    data5 = resp5.json()
    print(f"auth search='project' page1: sql={sql5} returned={len(data5['items'])} total={data5['total']} time={elapsed5:.3f}s")

    # Cleanup
    _cleanup(db, project_ids, [viewer_id] + owner_ids)
    db.close()
    app.dependency_overrides.clear()
