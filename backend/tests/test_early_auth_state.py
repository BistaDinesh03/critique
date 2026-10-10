"""Server-stamped early auth state on served pages.

An authenticated visitor returning to Critique used to see the Login button
until the browser's /auth/check round-trip resolved. The server now stamps a
``data-auth="in"`` hint plus its two CSS rules into ``<head>`` whenever the
session cookie's signature and age verify, so the correct header is part of
the first paint instead of a later swap.

The rules these tests hold the stamping to:

* it fires only for a valid session cookie -- missing, tampered or expired
  cookies must never produce it, because a failed check must not end up
  showing authenticated UI;
* it lands inside ``<head>``, before the header markup it styles, or it would
  be a race rather than a fix;
* it is presentation only: the token is never echoed into the page and no
  other response body content changes;
* it covers every page served through the frontend routes -- including the
  results page -- without modifying that page's own file;
* its pages are never cacheable (``private, no-store`` + ``Vary: Cookie``),
  because the body varies with the session cookie and no cache may replay
  one visitor's header to another.

The stamp deliberately skips the database (signature + age only): it is a
first-paint hint, and the browser's DB-backed /auth/check stays authoritative.
"""

from pathlib import Path

from fastapi.testclient import TestClient
from starlette.requests import Request

from app.auth import create_session_token, session_cookie_is_valid
from app.main import app

PAGES = ["/", "/discover", "/my-projects", "/project/1", "/project/1/results"]

STAMP = 'data-auth="in"'
LOGIN_RULE = 'html[data-auth="in"] #login-btn{display:none}'
LOGOUT_RULE = 'html[data-auth="in"] #logout-btn{display:inline-flex}'

SHARED_CSS = Path(__file__).resolve().parent.parent.parent / "static" / "shared.css"


def get_page(path, token=None):
    """Fresh client per request so cookies never leak between calls."""
    client = TestClient(app)
    if token is not None:
        client.cookies.set("critique_session", token)
    response = client.get(path)
    assert response.status_code == 200, f"{path}: {response.status_code}"
    return response.text


def _client(token=None):
    """A fresh client with an optional session cookie (never shared state)."""
    client = TestClient(app)
    if token is not None:
        client.cookies.set("critique_session", token)
    return client


def cookie_request(value=None):
    """A minimal ASGI request carrying an optional session cookie."""
    headers = []
    if value is not None:
        headers.append((b"cookie", f"critique_session={value}".encode()))
    return Request({"type": "http", "method": "GET", "path": "/", "headers": headers})


def test_anonymous_pages_carry_no_auth_stamp():
    for path in PAGES:
        assert STAMP not in get_page(path), f"anonymous {path} was stamped"


def test_tampered_cookie_is_ignored():
    assert STAMP not in get_page("/", token="not-a-session-token")


def test_stamp_never_echoes_the_token():
    token = create_session_token(1)
    html = get_page("/", token=token)
    assert token not in html, "the session token must not leak into the page"


def test_validity_helper_requires_signature_and_freshness():
    token = create_session_token(1)
    assert session_cookie_is_valid(cookie_request(token)) is True
    assert session_cookie_is_valid(cookie_request()) is False
    assert session_cookie_is_valid(cookie_request("garbage")) is False
    # Same age window get_current_user enforces; a negative max age expires
    # anything issued, which is how the expiry branch is exercised without
    # waiting a week.
    assert session_cookie_is_valid(cookie_request(token), max_age=-1) is False


def test_stamp_styles_both_auth_buttons():
    html = get_page("/", token=create_session_token(1))
    assert LOGIN_RULE in html
    assert LOGOUT_RULE in html
    # The shared default that keeps anonymous visitors on the logged-out
    # header even before any script runs.
    shared_css = SHARED_CSS.read_text(encoding="utf-8")
    assert "#logout-btn" in shared_css and "display: none" in shared_css


def _stamp_precedes_header(html):
    return (
        html.index(STAMP) < html.index("</head>") < html.index("<header")
    )


def test_valid_session_stamps_every_page_before_its_header():
    for path in PAGES:
        html = get_page(path, token=create_session_token(1))
        assert STAMP in html, f"authenticated {path} was not stamped"
        assert _stamp_precedes_header(html), f"stamp races the header on {path}"


# Signed tokens can name any user id; the test database never contains this
# one, so it exercises the "valid signature, nonexistent user" split exactly.
MISSING_USER_ID = 999_999_999


def test_signed_token_for_a_missing_user_grants_only_the_presentation_stamp():
    """Signature + age may stamp first paint; authorization still says no.

    The stamp is a hint without a payload: the token and the user id never
    enter the page, /auth/check keeps answering with its existing 401 for a
    user the database does not have, and a protected endpoint refuses the
    very same cookie outright.
    """
    token = create_session_token(MISSING_USER_ID)

    html = get_page("/", token=token)
    assert STAMP in html, "a correctly signed cookie may stamp first paint"
    assert token not in html, "the session token must not leak into the page"
    assert str(MISSING_USER_ID) not in html, "no user identity enters the page"

    client = _client(token)
    check = client.get("/auth/check")
    assert check.status_code == 401
    assert check.json() == {"detail": "User not found"}

    protected = client.get("/api/projects/my/list")
    assert protected.status_code == 401
    assert protected.json() == {"detail": "User not found"}


def test_a_token_altered_without_resigning_is_rejected_everywhere():
    """Payload edit and signature edit both fail closed, page included."""
    token = create_session_token(1)
    payload, signature = token.rsplit(".", 1)

    def flip_first_char(segment):
        replacement = "A" if segment[0] != "A" else "B"
        return replacement + segment[1:]

    tampered_tokens = [
        flip_first_char(payload) + "." + signature,  # contents altered
        payload + "." + flip_first_char(signature),  # HMAC altered
    ]
    for tampered in tampered_tokens:
        assert tampered != token
        assert session_cookie_is_valid(cookie_request(tampered)) is False
        assert STAMP not in get_page("/", token=tampered), (
            "an unresigned token must never be stamped into the page"
        )


def test_pages_opt_out_of_caching_because_their_body_varies_by_cookie():
    """Every stamped-capable page: private, no-store, Vary: Cookie."""
    for path in PAGES:
        for token in (None, create_session_token(1)):
            response = _client(token).get(path)
            assert response.status_code == 200, path
            assert response.headers["cache-control"] == "private, no-store", path
            assert response.headers["vary"] == "Cookie", path


def test_cache_headers_reach_only_the_html_pages():
    """Static assets keep their own caching; API and auth stay untouched."""
    client = _client()

    static = client.get("/static/shared.css")
    assert static.status_code == 200
    assert static.headers["cache-control"] == "public, max-age=86400"
    assert "vary" not in static.headers

    listing = client.get("/api/projects/")
    assert listing.status_code == 200
    assert "cache-control" not in listing.headers
    assert "vary" not in listing.headers

    check = client.get("/auth/check")
    assert check.status_code == 401
    assert "cache-control" not in check.headers
    assert "vary" not in check.headers
