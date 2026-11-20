import pytest
from fastapi.testclient import TestClient

from app import routes_analytics_dashboard
from app.auth import get_current_user
from app.config import Settings
from app.main import app
from app.models import User

@pytest.mark.parametrize(
    ("env_value", "expected"),
    [
        pytest.param(None, {"BistaDinesh03"}, id="unset"),
        pytest.param("", set(), id="empty"),
        pytest.param("alice,bob", {"alice", "bob"}, id="list"),
        pytest.param(" alice, , bob, ", {"alice", "bob"}, id="whitespace-and-empty-entries"),
        pytest.param("Alice, BOB", {"Alice", "BOB"}, id="preserves-case"),
    ],
)
def test_analytics_owner_usernames(monkeypatch, env_value, expected):
    if env_value is None:
        monkeypatch.delenv("ANALYTICS_OWNER_USERNAMES", raising=False)
    else:
        monkeypatch.setenv("ANALYTICS_OWNER_USERNAMES", env_value)

    assert Settings().ANALYTICS_OWNER_USERNAMES == expected

@pytest.mark.parametrize(
    ("env_value", "username", "expected_status"),
    [
        pytest.param("Alice,bob", "Alice", 200, id="allowed"),
        pytest.param("Alice,bob", "aLiCe", 200, id="case-insensitive"),
        pytest.param("Alice,bob", "charlie", 403, id="outside-allowlist"),
        pytest.param("", "BistaDinesh03", 403, id="empty-allowlist"),
    ],
)
def test_analytics_dashboard_authorization(
    monkeypatch, env_value, username, expected_status
):
    monkeypatch.setenv("ANALYTICS_OWNER_USERNAMES", env_value)
    monkeypatch.setattr(
        routes_analytics_dashboard,
        "OWNER_USERNAMES",
        Settings().ANALYTICS_OWNER_USERNAMES,
    )

    def mock_get_current_user():
        return User(username=username)

    monkeypatch.setitem(
        app.dependency_overrides, get_current_user, mock_get_current_user
    )

    with TestClient(app) as client:
        response = client.get("/api/analytics/dashboard")

    assert response.status_code == expected_status
