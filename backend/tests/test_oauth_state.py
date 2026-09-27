"""Regression tests for GitHub OAuth `state` (login CSRF) protection.

Covers the real /auth/login -> /auth/callback boundary. No network I/O:
httpx.AsyncClient is replaced with a stub that plays the role of GitHub.

Design notes:
- `follow_redirects=False` so Location headers and cookies are inspectable.
- Users created by these tests are removed afterwards so the rest of the suite
  (which asserts on table contents) is unaffected.
"""

import uuid
from urllib.parse import parse_qs, quote, urlparse

import pytest
from fastapi.testclient import TestClient

from app import auth as auth_module
from app.auth import OAUTH_STATE_COOKIE_NAME, RETURN_TO_COOKIE_NAME
from app.database import SessionLocal, init_db
from app.main import app
from app.models import EmailLoginToken, User


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _cleanup_oauth_test_users():
    """Remove any user/token rows these tests create."""
    yield
    db = SessionLocal()
    try:
        # Only rows created here (test-only github_id range / email prefix).
        db.query(User).filter(User.github_id >= 900_000_000).delete()
        db.query(User).filter(User.email.like("oauth_boundary_%")).delete()
        db.query(EmailLoginToken).filter(EmailLoginToken.email.like("oauth_boundary_%")).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def client():
    init_db()
    return TestClient(app, follow_redirects=False)


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class GithubStub:
    """Stands in for httpx.AsyncClient so no GitHub request is ever made."""

    def __init__(self, *, access_token="ghs_test_token", github_id, login):
        self.access_token = access_token
        self.github_id = github_id
        self.login = login
        self.token_calls = []
        self.user_calls = []

    def install(self, monkeypatch):
        outer = self

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def post(self, url, **kwargs):
                outer.token_calls.append({"url": url, "json": kwargs.get("json")})
                if outer.access_token is None:
                    return _FakeResponse({"error": "bad_verification_code"})
                return _FakeResponse({"access_token": outer.access_token})

            async def get(self, url, **kwargs):
                outer.user_calls.append({"url": url, "headers": kwargs.get("headers")})
                return _FakeResponse(
                    {
                        "id": outer.github_id,
                        "login": outer.login,
                        "avatar_url": "https://avatars.example/u.png",
                    }
                )

        monkeypatch.setattr("httpx.AsyncClient", FakeAsyncClient)


@pytest.fixture
def github(monkeypatch):
    """GitHub stub with a unique identity per test."""
    stub = GithubStub(
        github_id=900_000_000 + uuid.uuid4().int % 100_000_000,
        login=f"oauth_tester_{uuid.uuid4().hex[:10]}",
    )
    stub.install(monkeypatch)
    return stub


def start_login(browser, return_to=None):
    """Initiate OAuth in `browser` and return (authorize_url, state, cookie)."""
    url = "/auth/login"
    if return_to is not None:
        url += "?return_to=" + quote(return_to, safe="/?")
    response = browser.get(url, follow_redirects=False)
    assert response.status_code in (302, 307), response.text

    location = response.headers["location"]
    query = parse_qs(urlparse(location).query)
    assert "state" in query, "authorize URL must carry a state parameter"
    state = query["state"][0]
    cookie = browser.cookies.get(OAUTH_STATE_COOKIE_NAME)
    if cookie:
        cookie = cookie.strip('"')
    return location, state, cookie


def callback(browser, state=None, code="test-code"):
    query = "code=" + code
    if state is not None:
        query += "&state=" + quote(state, safe="")
    return browser.get("/auth/callback?" + query, follow_redirects=False)


# ---------------------------------------------------------------------------
# 1. Normal login with the correct state succeeds
# ---------------------------------------------------------------------------


def test_login_sends_state_to_github(client, github):
    location, state, cookie = start_login(client)

    parsed = urlparse(location)
    assert parsed.netloc == "github.com"
    assert parsed.path == "/login/oauth/authorize"
    query = parse_qs(parsed.query)
    # Existing authorization contract is unchanged.
    assert query["client_id"] == [auth_module.settings.GITHUB_CLIENT_ID]
    assert query["redirect_uri"] == [auth_module.settings.GITHUB_REDIRECT_URI]
    assert query["scope"] == ["read:user"]
    # New: state is sent to GitHub.
    assert query["state"] == [state]

    # The twin is bound to this browser: httponly, same-site=lax, short-lived.
    assert cookie, "state cookie must be set on the initiating browser"
    assert len(state) >= 40, "state must be a long random value"


def test_callback_with_correct_state_succeeds(client, github):
    _, state, _ = start_login(client)
    response = callback(client, state=state)

    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/"
    assert "critique_session" in response.cookies
    assert "critique_csrf" in response.cookies
    # GitHub was consulted exactly the way it was before the fix.
    assert len(github.token_calls) == 1
    assert github.token_calls[0]["url"].endswith("/login/oauth/access_token")
    assert github.token_calls[0]["json"]["code"] == "test-code"
    assert github.token_calls[0]["json"]["redirect_uri"] == auth_module.settings.GITHUB_REDIRECT_URI

    # And the resulting session really authenticates the browser.
    check = client.get("/auth/check", follow_redirects=False)
    assert check.status_code == 200
    assert check.json()["authenticated"] is True


def test_state_cookie_is_httponly_and_same_site_lax(client, github):
    response = client.get("/auth/login", follow_redirects=False)
    set_cookie = ";".join(
        h for h in response.headers.get_list("set-cookie") if h.startswith(OAUTH_STATE_COOKIE_NAME + "=")
    )
    assert set_cookie
    lowered = set_cookie.lower()
    assert "httponly" in lowered
    assert "samesite=lax" in lowered
    assert f"max-age={auth_module.OAUTH_STATE_MAX_AGE}" in lowered


# ---------------------------------------------------------------------------
# 2-4. Missing / incorrect / cross-browser state is rejected
# ---------------------------------------------------------------------------


def test_callback_with_missing_state_is_rejected(client, github):
    start_login(client)
    response = callback(client, state=None)

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or missing OAuth state"
    # Rejected before any external call and before any session is created.
    assert github.token_calls == []
    assert "critique_session" not in response.cookies
    assert client.get("/auth/check", follow_redirects=False).status_code == 401


def test_callback_with_incorrect_state_is_rejected(client, github):
    start_login(client)
    response = callback(client, state="attacker-guessed-state")

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or missing OAuth state"
    assert github.token_calls == []
    assert "critique_session" not in response.cookies


def test_state_from_another_browser_is_rejected(client, github):
    """The classic login-CSRF: attacker's state meets the victim's browser."""
    _, attacker_state, _ = start_login(client)

    victim = TestClient(app, follow_redirects=False)
    # The victim even has their own perfectly valid pending state.
    _, victim_state, _ = start_login(victim)
    assert victim_state != attacker_state

    response = callback(victim, state=attacker_state)
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or missing OAuth state"
    assert github.token_calls == []
    assert "critique_session" not in response.cookies

    # The victim's own attempt still works afterwards.
    ok = callback(victim, state=victim_state)
    assert ok.status_code in (302, 307)


def test_unsigned_attacker_supplied_state_cookie_is_rejected(client, github):
    """A state must be accepted only because *we* issued it, not merely
    because a cookie carrying it is present (cookie-tossing defense)."""
    _, state, _ = start_login(client)
    # Attacker overwrites the cookie with the raw state, unsigned.
    client.cookies.set(OAUTH_STATE_COOKIE_NAME, state)

    response = callback(client, state=state)
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or missing OAuth state"
    assert github.token_calls == []
    assert "critique_session" not in response.cookies


def test_non_ascii_state_is_rejected_without_error(client, github):
    start_login(client)
    response = callback(client, state="état")
    assert response.status_code == 400
    assert github.token_calls == []


# ---------------------------------------------------------------------------
# 5. Single use: a consumed state cannot be replayed
# ---------------------------------------------------------------------------


def test_consumed_state_cannot_be_replayed(client, github):
    _, state, _ = start_login(client)
    first = callback(client, state=state)
    assert first.status_code in (302, 307)
    # The accepted state was dropped from this browser.
    remaining = client.cookies.get(OAUTH_STATE_COOKIE_NAME)
    assert remaining in (None, "", '""')

    replay = callback(client, state=state)
    assert replay.status_code == 400
    assert replay.json()["detail"] == "Invalid or missing OAuth state"
    assert "critique_session" not in replay.cookies


def test_state_is_consumed_even_when_github_exchange_fails(client, monkeypatch, github):
    github.access_token = None  # simulate GitHub rejecting the code
    _, state, _ = start_login(client)

    failed = callback(client, state=state)
    assert failed.status_code == 400
    assert failed.json()["detail"] == "GitHub authentication failed"  # unchanged contract
    remaining = client.cookies.get(OAUTH_STATE_COOKIE_NAME)
    assert remaining in (None, "", '""')

    # Same state, second attempt: now rejected as unknown.
    replay = callback(client, state=state, code="another-code")
    assert replay.status_code == 400
    assert replay.json()["detail"] == "Invalid or missing OAuth state"
    assert len(github.token_calls) == 1


def test_expired_state_is_rejected(client, github, monkeypatch):
    _, state, _ = start_login(client)
    monkeypatch.setattr(auth_module, "OAUTH_STATE_MAX_AGE", -1)

    response = callback(client, state=state)
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or missing OAuth state"
    assert github.token_calls == []


# ---------------------------------------------------------------------------
# 6. The generated state is unpredictable
# ---------------------------------------------------------------------------


def test_states_are_random_unique_and_long(client, github):
    states = [start_login(client)[1] for _ in range(5)]

    assert len(set(states)) == len(states), "states must not repeat"
    for state in states:
        assert len(state) >= 40
        assert state.isascii()
        # token_urlsafe alphabet: no '+', '/', '=' padding.
        assert all(c.isalnum() or c in "-_" for c in state)
    # Not a fixed/static value.
    assert len({s for s in states}) == 5


# ---------------------------------------------------------------------------
# 7. return_to behaviour is unchanged
# ---------------------------------------------------------------------------


def test_safe_return_to_still_honoured_with_state(client, github):
    _, state, _ = start_login(client, return_to="/project/5")
    response = callback(client, state=state)
    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/project/5"
    # return_to cookie is still cleared after a successful login.
    assert client.cookies.get(RETURN_TO_COOKIE_NAME) in (None, "", '""')


def test_unsafe_return_to_still_ignored_with_state(client, github):
    _, state, _ = start_login(client, return_to="https://evil.com")
    response = callback(client, state=state)
    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/"


# ---------------------------------------------------------------------------
# 5 (edge cases). Concurrent attempts and cancellation
# ---------------------------------------------------------------------------


def test_two_concurrent_logins_in_one_browser_both_work(client, github):
    _, state_a, _ = start_login(client)
    _, state_b, _ = start_login(client)
    assert state_a != state_b

    first = callback(client, state=state_a)
    assert first.status_code in (302, 307)
    second = callback(client, state=state_b)
    assert second.status_code in (302, 307)


def test_oldest_pending_state_is_evicted_after_the_cap(client, github):
    states = [start_login(client)[1] for _ in range(auth_module.OAUTH_STATE_MAX_PENDING + 1)]
    oldest = states[0]

    response = callback(client, state=oldest)
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or missing OAuth state"
    assert github.token_calls == []

    # The newest attempt is unaffected by the eviction.
    ok = callback(client, state=states[-1])
    assert ok.status_code in (302, 307)


def test_github_error_redirect_without_code_is_unaffected(client, github):
    """GitHub cancellation/error redirect never reaches the handler (no `code`),
    exactly as before this change."""
    response = client.get("/auth/callback?error=access_denied", follow_redirects=False)
    assert response.status_code == 422
    assert github.token_calls == []
    assert "critique_session" not in response.cookies


# ---------------------------------------------------------------------------
# 8. Email authentication is untouched by the state change
# ---------------------------------------------------------------------------


def test_email_login_works_while_an_oauth_state_is_pending(client, github):
    """Email auth shares the session/return_to helpers with the GitHub flow.
    It must neither require nor consume the OAuth state cookie."""
    from datetime import datetime, timedelta, timezone

    from app import auth as _auth
    from app.models import EmailLoginToken

    # This browser has an in-flight GitHub login...
    _, state, _ = start_login(client)
    assert state

    # ...and now completes an email login instead (token inserted directly so
    # no Resend call is involved).
    email = f"oauth_boundary_{uuid.uuid4().hex[:10]}@example.com"
    raw_token = _auth.secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        db.add(
            EmailLoginToken(
                email=email,
                token_hash=_auth._hash_token(raw_token),
                created_at=now,
                expires_at=now + timedelta(minutes=15),
                used_at=None,
                requester_ip_hash="e" * 64,
                return_to=None,
            )
        )
        db.commit()
    finally:
        db.close()

    verified = client.get("/auth/email/verify?token=" + raw_token, follow_redirects=False)
    assert verified.status_code in (302, 307)
    assert "critique_session" in verified.cookies
    assert client.get("/auth/check", follow_redirects=False).status_code == 200
    # The pending OAuth state was left alone by the email flow.
    assert client.cookies.get(OAUTH_STATE_COOKIE_NAME) not in (None, "", '""')
