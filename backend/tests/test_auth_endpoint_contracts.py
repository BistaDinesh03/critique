
from fastapi.testclient import TestClient

from app.main import app
from app.csrf import generate_csrf_token


client = TestClient(app, follow_redirects=False)


def test_logout_redirects_to_home_and_deletes_auth_cookies():
    response = client.get(
        "/auth/logout",
        cookies={
            "critique_session": "existing-session",
            "critique_csrf": "existing-csrf",
        },
    )

    assert response.status_code == 307
    assert response.headers["location"] == "/"

    set_cookie_headers = response.headers.get_list("set-cookie")
    assert any(
        "critique_session=" in cookie and "Max-Age=0" in cookie
        for cookie in set_cookie_headers
    )
    assert any(
        "critique_csrf=" in cookie and "Max-Age=0" in cookie
        for cookie in set_cookie_headers
    )


def test_logout_works_without_an_active_session():
    response = client.get("/auth/logout")

    assert response.status_code == 307
    assert response.headers["location"] == "/"

    set_cookie_headers = response.headers.get_list("set-cookie")
    assert any("critique_session=" in cookie for cookie in set_cookie_headers)
    assert any("critique_csrf=" in cookie for cookie in set_cookie_headers)


def test_csrf_token_returns_existing_cookie_value():
    existing_token = "existing-csrf-token"

    response = client.get(
        "/auth/csrf-token",
        cookies={"critique_csrf": existing_token},
    )

    assert response.status_code == 200
    assert response.json() == {"csrf_token": existing_token}
    assert response.headers.get("set-cookie") is None


def test_csrf_token_generates_token_and_sets_cookie(monkeypatch):
    generated_token = "generated-csrf-token"
    monkeypatch.setattr(
        "app.auth.generate_csrf_token",
        lambda: generated_token,
    )

    response = client.get("/auth/csrf-token")

    assert response.status_code == 200
    assert response.json() == {"csrf_token": generated_token}
    assert "critique_csrf=generated-csrf-token" in response.headers.get(
        "set-cookie", ""
    )