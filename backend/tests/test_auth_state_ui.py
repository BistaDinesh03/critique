"""Header auth states, exercised through each page's own JavaScript.

The navbar starts logged-out in the markup (Login present, Logout hidden by
shared.css) and the server may stamp an early session state into <head>.
Either way /auth/check stays authoritative, so every answer it can give has
to land on a deliberate header state:

* 200 -- the logged-in header: logout shown, login hidden;
* any other status, or a thrown error -- the logged-out header. A failed
  check must never leave authenticated UI up, not even the stamped one.

The Node rendering harness runs the real page scripts, so what is asserted
is what the browser actually executes. All five pages that ship the shared
navbar are covered, the results page included.

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

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node is required to run the frontend rendering harness",
)

PAGES = ["index.html", "discover.html", "my_projects.html", "project_detail.html",
         "project_results.html"]

CHECK_SUCCESS = {"/auth/check": {"status": 200, "body": {"authenticated": True}}}
CHECK_UNAUTHORIZED = {"/auth/check": {"status": 401, "body": {"detail": "Not authenticated"}}}
CHECK_SERVER_ERROR = {"/auth/check": {"status": 500, "body": {"detail": "boom"}}}


def run(tmp_path, page, calls, fetch=None):
    """Execute the page's scripts and return the harness result."""
    scenario = {
        "page": (FRONTEND_DIR / page).as_posix(),
        "calls": calls,
        "read": {"created": True},
        "fetch": fetch or {},
        "location": "/",
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


@pytest.mark.parametrize("page", PAGES)
def test_successful_check_shows_the_logged_in_header(tmp_path, page):
    result = run(tmp_path, page, [{"fn": "checkAuth", "args": []}], fetch=CHECK_SUCCESS)
    assert auth_displays(result) == ("none", "inline")


@pytest.mark.parametrize("page", PAGES)
def test_failed_check_lands_on_the_logged_out_header(tmp_path, page):
    # No route mocked: the harness answers /auth/check with 404.
    result = run(tmp_path, page, [{"fn": "checkAuth", "args": []}])
    assert auth_displays(result) == ("inline", "none")


@pytest.mark.parametrize("page", PAGES)
def test_unauthorized_check_lands_on_the_logged_out_header(tmp_path, page):
    """401 is the designed answer for a stale or unknown session; like every
    other non-200 it must land on the logged-out header, stamp or no stamp."""
    result = run(
        tmp_path, page, [{"fn": "checkAuth", "args": []}], fetch=CHECK_UNAUTHORIZED
    )
    assert auth_displays(result) == ("inline", "none")


@pytest.mark.parametrize("page", PAGES)
def test_server_error_never_leaves_authenticated_ui_up(tmp_path, page):
    result = run(
        tmp_path, page, [{"fn": "checkAuth", "args": []}], fetch=CHECK_SERVER_ERROR
    )
    assert auth_displays(result) == ("inline", "none")


@pytest.mark.parametrize("page", PAGES)
def test_markup_never_claims_an_auth_state_on_its_own(page):
    """Neither auth button ships with an inline display.

    Login must be visible until the check says otherwise; the server stamp
    (not markup) is what suppresses it for signed-in first paint. Logout's
    visibility belongs to shared.css's default and the check's toggling.
    """
    source = (FRONTEND_DIR / page).read_text(encoding="utf-8")
    login_tag = re.search(r'<a[^>]*id="login-btn"[^>]*>', source).group(0)
    logout_tag = re.search(r'<a[^>]*id="logout-btn"[^>]*>', source).group(0)
    assert "style=" not in login_tag, "login must not carry an inline display"
    assert "style=" not in logout_tag, "logout visibility belongs to CSS/check"
    # And the stylesheet default keeps anonymous visitors on the logged-out
    # header even before any script runs.
    shared_css = (FRONTEND_DIR.parent / "static" / "shared.css").read_text(
        encoding="utf-8"
    )
    assert "#logout-btn" in shared_css
