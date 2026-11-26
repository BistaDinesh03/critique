import os
import shutil
from pathlib import Path

# Isolate tests to a dedicated SQLite file so schema changes apply from a fresh build.
# This must run BEFORE importing app.config / app.database, which read DATABASE_URL at import time.
# Use an absolute path so pytest's chdir to rootdir cannot change the target file.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_TEST_DB_PATH = _BACKEND_DIR / "critique_test.db"
os.environ["DATABASE_URL"] = "sqlite:///" + _TEST_DB_PATH.as_posix()
os.environ.setdefault("GITHUB_CLIENT_ID", "ci-test-client-id")

import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db, SessionLocal
from app.models import User
from app.auth import get_current_user, get_current_user_optional
from app.csrf import generate_csrf_token, CSRF_COOKIE_NAME
from app.rate_limit import reset_rate_limits


@pytest.fixture(scope="session", autouse=True)
def _fresh_test_db():
    """Ensure a clean SQLite test database and schema before the test session runs."""
    if _TEST_DB_PATH.exists():
        _TEST_DB_PATH.unlink()
    init_db()
    yield
    # Leave the file in place after the run so it can be inspected if needed.


@pytest.fixture(autouse=True)
def reset_limits_before_test():
    """Reset rate limits before every test."""
    reset_rate_limits()
    from app.routes_stats import clear_stats_cache
    clear_stats_cache()
    yield


@pytest.fixture
def auth_client():
    """Create a test client with authentication and CSRF bypassed."""
    init_db()
    db = SessionLocal()
    unique_suffix = uuid.uuid4().hex[:8]
    user = User(github_id=hash(unique_suffix) % 100000000, username=f"testuser_{unique_suffix}")
    db.add(user)
    db.commit()
    db.refresh(user)

    user_id = user.id
    db.close()

    db2 = SessionLocal()
    db2.close()
    unique_suffix_copy = unique_suffix

    def _get_or_recreate_user():
        s = SessionLocal()
        try:
            u = s.query(User).filter(User.id == user_id).first()
            if u is None:
                # Test cleanup helpers may have deleted the fixture row; put it
                # back with the same id so foreign keys stay satisfiable.
                u = User(id=user_id, github_id=hash(unique_suffix_copy) % 100000000,
                         username=f"testuser_{unique_suffix_copy}")
                s.add(u)
                s.commit()
                s.refresh(u)
            s.expunge(u)
            return u
        finally:
            s.close()

    def mock_get_current_user():
        return _get_or_recreate_user()

    def mock_get_current_user_optional():
        return _get_or_recreate_user()

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_user_optional] = mock_get_current_user_optional
    client = TestClient(app)

    csrf_token = generate_csrf_token()
    client.cookies.set(CSRF_COOKIE_NAME, csrf_token)
    client.headers["X-CSRF-Token"] = csrf_token

    yield client

    app.dependency_overrides.clear()
    db2.close()

def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "frontend_render: tests that require the Node frontend rendering harness",
    )
    config.addinivalue_line(
        "markers",
        "benchmark: performance benchmarks excluded from default CI; set RUN_BENCHMARKS=1 to run",
    )

def pytest_collection_modifyitems(config, items):
    """Prevent CI from passing when frontend-render tests are skipped for no Node."""
    ci_value = os.environ.get("CI", "").strip().lower()
    if ci_value not in {"1", "true", "yes", "on"} or shutil.which("node") is not None:
        return

    render_items = [
        item for item in items
        if item.get_closest_marker("frontend_render") is not None
    ]

    if render_items:
        examples = ", ".join(sorted({item.nodeid.split("::", 1)[0] for item in render_items})[:3])
        pytest.exit(
            "CI requires Node.js for frontend-render tests, but 'node' was not "
            f"found on PATH. Refusing to silently skip these tests (e.g. {examples}).",
            returncode=1,
        )
