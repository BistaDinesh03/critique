"""Frontend browser rendering tests for the branded 404 page (frontend/404.html).

Exercises the 404 page's scripts inside the Node rendering harness, asserting on:
- static content: "Page not found" heading and destination links ("/", "/discover");
- mobile nav toggle: click opens/closes menu and synchronizes aria-expanded;
- auth state: auth check status (200 vs 401/error) controls Login/Logout visibility.

Requires Node.js on PATH; guarded by the frontend_render marker.
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

CHECK_SUCCESS = {"/auth/check": {"status": 200, "body": {"authenticated": True}}}
CHECK_UNAUTHORIZED = {"/auth/check": {"status": 401, "body": {"detail": "Not authenticated"}}}
CHECK_ERROR = {"/auth/check": {"status": 500, "body": {"detail": "Internal server error"}}}


def run(tmp_path, calls=None, fetch=None, location="/nonexistent"):
    """Execute 404.html inside the Node rendering harness."""
    scenario = {
        "page": (FRONTEND_DIR / "404.html").as_posix(),
        "calls": calls or [],
        "read": {"created": True},
        "fetch": fetch or {},
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


def auth_displays(result):
    return (
        result["flags"]["login-btn"]["display"],
        result["flags"]["logout-btn"]["display"],
    )


def test_404_page_has_heading_and_destination_links():
    """Page markup includes 'Page not found' heading and links to home and Discover."""
    html = (FRONTEND_DIR / "404.html").read_text(encoding="utf-8")
    assert "Page not found" in html
    assert 'href="/"' in html
    assert 'href="/discover"' in html
    assert "Back to home" in html
    assert "Explore projects" in html


def test_404_skip_link_targets_focusable_main():
    html = (FRONTEND_DIR / "404.html").read_text(encoding="utf-8")
    assert re.search(r'<body>\s*<a href="#main-content" class="skip-link">', html)
    assert re.search(r'<main\b[^>]*\bid="main-content"[^>]*\btabindex="-1"', html)
    assert html.count('id="main-content"') == 1


def test_navbar_toggle_opens_and_closes_menu(tmp_path):
    """Clicking navbar-toggle toggles class navbar-nav-open and aria-expanded."""
    # Initially closed
    initial = run(tmp_path, calls=[])
    assert initial["flags"]["navbar-toggle"]["ariaExpanded"] in (None, "false")
    assert "navbar-nav-open" not in (initial["flags"]["navbar-nav"]["className"] or "")

    # Click opens
    opened = run(tmp_path, calls=[{"clickId": "navbar-toggle"}])
    assert opened["flags"]["navbar-toggle"]["ariaExpanded"] == "true"
    assert "navbar-nav-open" in opened["flags"]["navbar-nav"]["className"]

    # Second click closes
    closed = run(
        tmp_path,
        calls=[{"clickId": "navbar-toggle"}, {"clickId": "navbar-toggle"}],
    )
    assert closed["flags"]["navbar-toggle"]["ariaExpanded"] == "false"
    assert "navbar-nav-open" not in (closed["flags"]["navbar-nav"]["className"] or "")


def test_404_auth_signed_out_by_default(tmp_path):
    """When /auth/check returns 401 (or is not mocked), login is shown and logout is hidden."""
    result = run(tmp_path, calls=[{"fn": "checkAuth", "args": []}], fetch=CHECK_UNAUTHORIZED)
    assert auth_displays(result) == ("inline", "none")


def test_404_auth_signed_in_shows_logout(tmp_path):
    """When /auth/check returns 200, logout is shown and login is hidden."""
    result = run(tmp_path, calls=[{"fn": "checkAuth", "args": []}], fetch=CHECK_SUCCESS)
    assert auth_displays(result) == ("none", "inline")


def test_404_auth_error_falls_back_to_logged_out(tmp_path):
    """When /auth/check fails with 500, falls back to logged out state."""
    result = run(tmp_path, calls=[{"fn": "checkAuth", "args": []}], fetch=CHECK_ERROR)
    assert auth_displays(result) == ("inline", "none")
