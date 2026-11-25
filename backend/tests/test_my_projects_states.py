"""Frontend render tests for the My Projects page states.

Covers the distinct states ``loadProjects()`` can render on ``my_projects.html``:
the loading skeletons, the "No projects yet" empty state, the load-error retry
state, and a populated card grid. A regression in any of them was previously
only catchable by looking at the page.

The tests use the shared Node render harness (``frontend_render_harness.js``)
rather than a new mechanism, and assert on the markup the page actually renders.
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

MY_PROJECTS_ENDPOINT = "/api/projects/my/list"


def run_harness(tmp_path, calls, fetch=None, location="/my-projects", read=None):
    """Execute my_projects.html scripts inside the Node render harness."""
    scenario = {
        "page": (FRONTEND_DIR / "my_projects.html").as_posix(),
        "calls": calls,
        "read": read or {"byId": "content"},
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


def test_my_projects_renders_loading_skeleton_while_pending(tmp_path):
    """While the request is in flight, the page shows skeleton cards.

    The loader is started without awaiting it (``void loadProjects()``) so the
    pending request stays in flight and the busy placeholder can be observed;
    awaiting it would block on a promise that never settles.
    """
    result = run_harness(
        tmp_path,
        [{"evaluate": "void loadProjects()"}],
        fetch={MY_PROJECTS_ENDPOINT: {"pending": True}},
    )
    html = result.get("html", "")

    # The busy placeholder is a grid of skeleton cards, hidden from a11y tree
    # so screen readers are not told about decorative placeholders.
    assert "projects-grid" in html
    assert "skeleton-card" in html
    assert 'aria-hidden="true"' in html


def test_my_projects_empty_state_offers_a_call_to_action(tmp_path):
    """An empty project list renders guidance and a submit CTA."""
    result = run_harness(
        tmp_path,
        [{"fn": "loadProjects", "args": []}],
        fetch={MY_PROJECTS_ENDPOINT: {"status": 200, "body": []}},
    )
    html = result.get("html", "")

    assert "No projects yet" in html
    assert "Share something you have built" in html
    # Call to action that leads to the project submission form.
    assert 'href="/#submit"' in html
    assert "Submit your first project" in html


def test_my_projects_load_error_offers_a_retry(tmp_path):
    """A failed load renders an alert with a working retry button."""
    result = run_harness(
        tmp_path,
        [{"fn": "loadProjects", "args": []}],
        fetch={MY_PROJECTS_ENDPOINT: {"status": 500, "body": {"detail": "boom"}}},
    )
    html = result.get("html", "")

    assert "Could not load projects" in html
    assert "Something went wrong." in html
    # The error is announced, and the retry re-invokes the loader.
    assert 'role="alert"' in html
    assert "Try again" in html
    assert "loadProjects()" in html


def test_my_projects_populated_grid_lists_cards_with_actions(tmp_path):
    """A populated list renders one card per project with the expected actions."""
    projects = [
        {
            "id": 1,
            "title": "Weather App",
            "description": "A tiny forecast app",
            "response_count": 0,
            "image_url": None,
        },
        {
            "id": 2,
            "title": "Notes CLI",
            "description": "Plain-text notes",
            "response_count": 3,
            "image_url": None,
        },
    ]
    result = run_harness(
        tmp_path,
        [{"fn": "loadProjects", "args": []}],
        fetch={MY_PROJECTS_ENDPOINT: {"status": 200, "body": projects}},
    )
    html = result.get("html", "")

    # One card per project, with its title.
    assert html.count('class="project-card"') == 2
    assert "Weather App" in html
    assert "Notes CLI" in html

    # Response counts are shown as a human label, singular vs plural.
    assert "No responses yet" in html
    assert "3 responses" in html

    # Each card links to the project and its feedback, plus share/delete.
    assert 'href="/project/1"' in html
    assert 'href="/project/2/results"' in html
    assert "View project" in html
    assert "View Feedback" in html
    assert "toggleShare(this)" in html
    assert "deleteProject(2, this)" in html