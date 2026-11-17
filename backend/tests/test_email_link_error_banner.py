"""The magic-link failure the backend reports is actually shown to the visitor.

``GET /auth/email/verify`` sends expired, already-used and otherwise invalid
magic links back to ``/?error=email_link`` -- three redirect sites in
``app/auth.py``, pinned by ``test_email_auth`` -- but nothing on the homepage
used to read that parameter. Reproduced on the live site: visiting the exact
URL the backend redirects to rendered a perfectly normal homepage with no
explanation at all, so a visitor who clicked a stale link was left to guess.

Expected: the first paint after the redirect says the link no longer works and
what to do next. Actual (before the fix): silence. The homepage script now
reveals a banner on load whenever ``error=email_link`` is present.

These tests run the homepage's *real* JavaScript through the Node rendering
harness and assert on the banner the page actually reveals -- on load, with no
further interaction, because the visitor has just been redirected here. The
wording has to stay generic: it must never hint at whether an email address or
an account exists.

Requires ``node`` on PATH; the whole module is skipped when it is missing.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"
HARNESS = Path(__file__).resolve().parent / "frontend_render_harness.js"

pytestmark = [
    pytest.mark.frontend_render,
    pytest.mark.skipif(
        shutil.which("node") is None,
        reason="node is required to run the frontend rendering harness",
    ),
]

# The exact URL /auth/email/verify redirects to (see app/auth.py).
ERROR_LOCATION = "/?error=email_link"

BANNER_ID = "auth-error-banner"

# Captures the URL the page hands to history.replaceState, so the flag cleanup
# is assertable even though the harness's history stub does nothing.
CAPTURE_REPLACE = (
    "(function () { window.__replaced = null; "
    "window.history.replaceState = function (state, title, url) { window.__replaced = url; }; "
    "return 'patched'; })()"
)


def run(tmp_path, calls, location="/", read=None):
    """Execute the homepage's scripts and return the harness result."""
    scenario = {
        "page": (FRONTEND_DIR / "index.html").as_posix(),
        "calls": calls,
        "read": read or {"byId": BANNER_ID},
        "fetch": {},
        "location": location,
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
    assert proc.returncode == 0, f"harness crashed:\n{proc.stderr}"
    result = json.loads(proc.stdout)
    assert result["errors"] == [], f"page script errors: {result['errors']}"
    return result


def banner_display(result):
    return result["flags"][BANNER_ID]["display"]


def test_error_param_reveals_the_banner_on_load(tmp_path):
    """The URL the backend redirects to must explain itself on first paint.

    Revealed by the page's own load-time script -- no click, no scroll -- so
    the visitor who lands here from a stale magic link sees the message
    immediately. Before the fix, nothing on this page read ``error=`` at all.
    """
    result = run(tmp_path, calls=[], location=ERROR_LOCATION)
    assert banner_display(result) == "block"


def test_banner_message_says_what_happened_and_what_to_do(tmp_path):
    """Generic wording: no token, no email address, no account-existence hint."""
    result = run(
        tmp_path,
        [{"fn": "showAuthErrorBanner", "args": []}],
        location=ERROR_LOCATION,
    )
    message = result["html"]
    assert "no longer valid" in message, message
    assert "request a new one" in message, message
    # The failure must never leak who or what the link was for.
    assert "@" not in message, message
    assert "account" not in message.lower(), message
    assert "token" not in message.lower(), message


def test_homepage_without_the_param_stays_silent(tmp_path):
    """A normal visit (or one with other flags) must show no banner."""
    result = run(
        tmp_path,
        [{"fn": "showAuthErrorBanner", "args": []}],
        location="/",
    )
    assert banner_display(result) is None
    assert result["html"] == ""


def test_unrelated_error_values_are_ignored(tmp_path):
    """Only the error the backend actually emits is handled."""
    result = run(
        tmp_path,
        [{"fn": "showAuthErrorBanner", "args": []}],
        location="/?error=something_else",
    )
    assert banner_display(result) is None
    assert result["html"] == ""


def test_error_flag_is_dropped_but_other_params_survive(tmp_path):
    """Cleaning the URL must not replay the banner nor lose the resume flags.

    ``replaceState`` keeps the cleanup off the network (no reload), and any
    ``resume=`` param an auth flow put in the URL has to stay readable for the
    script that consumes it later in the same load.
    """
    calls = [
        {"evaluate": CAPTURE_REPLACE, "as": "patch"},
        {"fn": "showAuthErrorBanner", "args": []},
        {"evaluate": "window.__replaced", "as": "replaced"},
    ]

    both = run(tmp_path, calls, location="/?error=email_link&resume=project_submit")
    assert both["values"]["patch"] == "patched"
    assert both["values"]["replaced"] == "/?resume=project_submit"

    only_error = run(tmp_path, calls, location=ERROR_LOCATION)
    assert only_error["values"]["replaced"] == "/"


def test_banner_is_marked_up_as_an_alert_and_hidden_by_default():
    """The element ships in the page with role=alert, first inside <main>."""
    source = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    assert (
        f'<div id="{BANNER_ID}" class="auth-error-banner" role="alert"></div>'
        in source
    )
    # First inside <main>: a redirected visitor must not have to scroll.
    assert source.index(f'id="{BANNER_ID}"') < source.index('<section class="hero">')

    css = (FRONTEND_DIR.parent / "static" / "shared.css").read_text(encoding="utf-8")
    assert re.search(r"\.auth-error-banner\s*\{[^}]*display:\s*none", css), (
        "the banner must stay hidden until the script reveals it"
    )
