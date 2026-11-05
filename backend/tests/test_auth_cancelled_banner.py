"""Frontend browser rendering tests for the /?auth=cancelled banner.

When a visitor presses Cancel on GitHub's consent screen, /auth/callback redirects to
/?auth=cancelled. The homepage script reveals #auth-cancelled-banner with a neutral
message and cleans up the URL with history.replaceState so a page refresh does not
replay the banner.

Exercises frontend/index.html through the Node rendering harness (frontend_render_harness.js).
Guarded by the frontend_render marker.
"""

import json
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

CANCELLED_LOCATION = "/?auth=cancelled"
BANNER_ID = "auth-cancelled-banner"

# Intercepts history.replaceState to capture the cleaned URL handed to it.
CAPTURE_REPLACE = (
    "(function () { window.__replaced = null; "
    "window.history.replaceState = function (state, title, url) { window.__replaced = url; }; "
    "return 'patched'; })()"
)


def run(tmp_path, calls=None, location="/", read=None):
    """Execute the homepage's scripts and return the harness result."""
    scenario = {
        "page": (FRONTEND_DIR / "index.html").as_posix(),
        "calls": calls or [],
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


def test_auth_cancelled_param_reveals_banner_on_load(tmp_path):
    """When landing on /?auth=cancelled, the banner is displayed on load."""
    result = run(tmp_path, calls=[], location=CANCELLED_LOCATION)
    assert banner_display(result) == "block"


def test_auth_cancelled_banner_renders_neutral_message(tmp_path):
    """The banner displays a neutral explanation that nothing went wrong and the visitor can retry."""
    result = run(
        tmp_path,
        calls=[{"fn": "showAuthCancelledBanner", "args": []}],
        location=CANCELLED_LOCATION,
    )
    message = result["html"]
    assert "GitHub sign-in was cancelled" in message
    assert "so you're not signed in" in message
    assert "Nothing went wrong" in message
    assert "you can try again whenever you like" in message


def test_homepage_without_cancelled_param_keeps_banner_hidden(tmp_path):
    """A normal homepage visit without ?auth=cancelled leaves the banner hidden."""
    result = run(tmp_path, calls=[], location="/")
    assert banner_display(result) is None
    assert result["html"] == ""


def test_unrelated_query_params_do_not_reveal_cancelled_banner(tmp_path):
    """Unrelated query params do not trigger the cancellation banner."""
    result = run(
        tmp_path,
        calls=[{"fn": "showAuthCancelledBanner", "args": []}],
        location="/?auth=unknown&foo=bar",
    )
    assert banner_display(result) is None
    assert result["html"] == ""


def test_cancelled_flag_stripped_via_replace_state(tmp_path):
    """history.replaceState cleans up ?auth=cancelled while preserving other params."""
    calls = [
        {"evaluate": CAPTURE_REPLACE, "as": "patch"},
        {"fn": "showAuthCancelledBanner", "args": []},
        {"evaluate": "window.__replaced", "as": "replaced"},
    ]

    # Sole param cleans to "/"
    res_sole = run(tmp_path, calls=calls, location=CANCELLED_LOCATION)
    assert res_sole["values"]["replaced"] == "/"

    # Preserves adjacent params
    res_adjacent = run(
        tmp_path,
        calls=calls,
        location="/?auth=cancelled&resume=project_submit",
    )
    assert res_adjacent["values"]["replaced"] == "/?resume=project_submit"


def test_banner_markup_in_index_html():
    """#auth-cancelled-banner is present in index.html with role=status and display:none."""
    source = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    assert f'id="{BANNER_ID}"' in source
    assert 'role="status"' in source
    assert 'style="display: none;' in source
    # Must precede hero so users see notice without scrolling
    assert source.index(f'id="{BANNER_ID}"') < source.index('<section class="hero">')
