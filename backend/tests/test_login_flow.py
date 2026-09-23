from fastapi.testclient import TestClient
from app.main import app
from app.auth import _is_safe_return_path

client = TestClient(app)


def test_safe_return_path_accepts_valid():
    assert _is_safe_return_path("/") is True
    assert _is_safe_return_path("/project/1") is True
    assert _is_safe_return_path("/discover") is True


def test_safe_return_path_rejects_empty():
    assert _is_safe_return_path("") is False
    assert _is_safe_return_path(None) is False


def test_safe_return_path_rejects_external():
    assert _is_safe_return_path("https://evil.com") is False
    assert _is_safe_return_path("http://evil.com/path") is False
    assert _is_safe_return_path("//evil.com") is False
    assert _is_safe_return_path("javascript:alert(1)") is False


def test_safe_return_path_rejects_protocol_relative():
    assert _is_safe_return_path("//evil.com/path") is False


def test_safe_return_path_rejects_backslash_trick():
    assert _is_safe_return_path("/\\evil.com") is False


def test_safe_return_path_rejects_scheme_in_path():
    assert _is_safe_return_path("/path?next=https://evil.com") is False


def test_safe_return_path_rejects_long_input():
    assert _is_safe_return_path("/" + "a" * 600) is False


def test_login_route_ignores_external_return_to():
    """External return_to URLs must not be stored."""
    response = client.get(
        "/auth/login?return_to=https://evil.com",
        follow_redirects=False,
    )
    assert response.status_code in (302, 307)
    # Cookie should NOT be set for an unsafe URL
    assert "critique_return_to" not in response.cookies


def test_login_route_accepts_safe_return_to():
    """Safe same-origin return_to is stored in a cookie."""
    response = client.get(
        "/auth/login?return_to=/project/5",
        follow_redirects=False,
    )
    assert response.status_code in (302, 307)
    # Starlette wraps cookie values in quotes for encoding; strip them.
    raw = response.cookies.get("critique_return_to")
    assert raw is not None
    assert raw.strip('"') == "/project/5"


def test_analytics_accepts_new_login_events():
    """New login events are in the allowlist."""
    for event in ["login_prompt_shown", "login_started", "login_success"]:
        response = client.post(f"/api/analytics/track?event_name={event}")
        assert response.status_code == 200, f"Event {event} rejected"


def test_safe_return_path_accepts_feedback_resume():
    """New feedback resume URL is accepted as safe."""
    assert _is_safe_return_path("/project/5?resume=feedback") is True


def test_dashboard_defines_owner_allowlist():
    """Dashboard module defines owner allowlist."""
    from app.routes_analytics_dashboard import OWNER_USERNAMES
    assert "BistaDinesh03" in OWNER_USERNAMES


def test_analytics_accepts_feedback_resume_event():
    """feedback_resume is in the backend allowlist."""
    response = client.post("/api/analytics/track?event_name=feedback_resume")
    assert response.status_code == 200
