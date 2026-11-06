"""Frontend render tests for the empty discover feed state.

Verifies that when no projects are waiting for feedback, the discover page
renders an accessible empty state with guidance and a call-to-action to submit
a project, without leaving skeleton placeholders or broken pagination behind.
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


def run_harness(tmp_path, page, calls, fetch=None, location="/discover", read=None):
    """Execute the page's scripts inside the Node render harness."""
    scenario = {
        "page": (FRONTEND_DIR / page).as_posix(),
        "calls": calls,
        "read": read or {"created": True},
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
        timeout=60,
    )
    assert proc.returncode == 0, f"harness crashed:\n{proc.stderr}"
    result = json.loads(proc.stdout)
    assert result["errors"] == [], f"page script errors: {result['errors']}"
    return result


def test_discover_show_empty_renders_heading_guidance_and_cta(tmp_path):
    """Calling showEmpty() displays the accessible empty state."""
    result = run_harness(
        tmp_path,
        "discover.html",
        [{"fn": "showEmpty", "args": []}],
        read={"byId": "project-list"},
    )
    html = result.get("html", "") or " ".join(result.get("created", []))

    # Empty state heading and subtext
    assert "No projects waiting for feedback yet" in html
    assert "Be the first maker to ask a question." in html
    # Call to action button to submit a project
    assert 'href="/"' in html
    assert "Submit a project" in html
    # Accessible status role
    assert 'role="status"' in html


def test_discover_empty_state_hides_pagination_and_resets_busy(tmp_path):
    """Empty discover feed hides pagination and marks the list not busy."""
    result = run_harness(
        tmp_path,
        "discover.html",
        [
            {"evaluate": "showEmpty()", "as": "called"},
            {"evaluate": "document.getElementById('pagination').style.display", "as": "paginationDisplay"},
            {"evaluate": "document.getElementById('project-list').getAttribute('aria-busy')", "as": "busy"},
        ],
    )
    values = result["values"]
    assert values["paginationDisplay"] == "none"
    assert values["busy"] == "false"


def test_discover_empty_state_removes_list_role_for_a11y(tmp_path):
    """Empty list removes role='list' so empty states do not violate aria-required-children."""
    result = run_harness(
        tmp_path,
        "discover.html",
        [
            {"evaluate": "showEmpty()", "as": "ran"},
            {"evaluate": "document.getElementById('project-list').getAttribute('role')", "as": "role"},
            {"evaluate": "document.getElementById('project-list').getAttribute('aria-label')", "as": "label"},
        ],
    )
    values = result["values"]
    assert values["role"] is None or values["role"] == ""
    assert values["label"] is None or values["label"] == ""


def test_discover_empty_feed_via_api_fetch(tmp_path):
    """When the API returns an empty project list, showEmpty is invoked."""
    result = run_harness(
        tmp_path,
        "discover.html",
        [{"fn": "loadProjects", "args": [1]}],
        fetch={
            "/api/projects/?page=1&page_size=9": {
                "status": 200,
                "body": {"items": [], "total_pages": 0, "total": 0},
            }
        },
        read={"byId": "project-list"},
    )
    html = result.get("html", "")
    assert "No projects waiting for feedback yet" in html
    assert "Submit a project" in html
