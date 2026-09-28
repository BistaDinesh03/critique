"""Loading UX: every placeholder resolves, and resolves to something useful.

The homepage grid, the discover list and the project page paint a skeleton
while their requests are in flight. The rules these tests hold the pages to:

* the placeholder is in the markup, announced (``aria-busy`` + an ``sr-only``
  status) rather than being a silent blank page;
* a successful response replaces it with the real content -- no skeleton left
  behind;
* a failed response replaces it with a message and a retry control, so the
  visitor is never parked behind an endless spinner;
* each critical endpoint is requested exactly once per render.

They run each page's own JavaScript inside the Node rendering harness, so what
is asserted is what the browser actually executes.

Requires ``node`` on PATH; the whole module is skipped when it is missing.
"""

import json
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

PROJECTS_URL = "/api/projects/?page=1&page_size=6"

PROJECT_ITEM = {
    "id": 7,
    "title": "Ship the thing",
    "description": "A short description",
    "question_text": "Is the pricing clear?",
    "response_count": 2,
    "image_url": None,
}


def run(tmp_path, page, calls, fetch=None, location="/", read=None):
    """Execute the page's scripts and return the harness result."""
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
        timeout=120,
    )
    assert proc.returncode == 0, f"harness crashed:\n{proc.stderr}"
    result = json.loads(proc.stdout)
    assert result["errors"] == [], f"page script errors: {result['errors']}"
    return result


def markup(page, marker, window=2000):
    """The source that follows `marker`, for asserting on static placeholders."""
    source = (FRONTEND_DIR / page).read_text(encoding="utf-8")
    assert marker in source, f"{marker} missing from {page}"
    return source.split(marker, 1)[1][:window]


def homepage_projects(result):
    return result["ids"]["homepage-projects"]


# ---------------------------------------------------------------------------
# Placeholders exist in the markup, before any script runs
# ---------------------------------------------------------------------------


def test_homepage_grid_starts_as_a_skeleton_with_a_live_status():
    block = markup("index.html", 'id="homepage-projects"')
    assert 'aria-busy="true"' in block
    assert block.count('class="skeleton-card"') == 3, "expected placeholder cards"
    # The skeleton is decorative; the announced state carries the meaning.
    assert 'class="sr-only" role="status"' in block
    assert "Loading projects" in block


def test_discover_list_starts_busy_with_a_live_status():
    block = markup("discover.html", 'id="project-list"', window=400)
    assert 'aria-busy="true"' in block
    status = markup("discover.html", 'id="project-list-status"', window=200)
    assert 'class="sr-only" role="status"' in status


def test_project_page_starts_with_a_skeleton_shell():
    block = markup("project_detail.html", 'id="content"', window=900)
    assert 'aria-busy="true"' in block
    assert "skeleton-detail-title" in block
    assert "skeleton-detail-block" in block
    assert "Loading project" in block


# ---------------------------------------------------------------------------
# The skeleton resolves to content
# ---------------------------------------------------------------------------


def test_homepage_skeleton_resolves_to_real_project_cards(tmp_path):
    result = run(
        tmp_path,
        "index.html",
        [{"fn": "loadHomepageProjects", "args": []}],
        fetch={PROJECTS_URL: {"status": 200, "body": {"items": [PROJECT_ITEM], "total": 1}}},
    )
    html = homepage_projects(result)
    assert "skeleton" not in html, f"placeholder survived the response: {html}"
    assert html.count("project-card") >= 1
    assert "Ship the thing" in html
    # Loading state resolved, and the resolved state is reported to AT.
    assert result["flags"]["homepage-projects"]["ariaBusy"] == "false"


def test_discover_skeleton_resolves_to_real_project_cards(tmp_path):
    result = run(
        tmp_path,
        "discover.html",
        [{"fn": "loadProjects", "args": [1]}],
        fetch={
            "/api/projects/": {
                "status": 200,
                "body": {"items": [PROJECT_ITEM], "total": 1, "page": 1, "total_pages": 1},
            }
        },
    )
    # showProjects appends the cards, so they are asserted as created nodes.
    assert any(meta["className"] == "project-card" for meta in result["createdMeta"])
    assert "Ship the thing" in result["html"]
    assert result["flags"]["project-list"]["ariaBusy"] == "false"
    # The busy announcement is cleared with the message, not left spinning.
    assert result["ids"]["project-list-status"] == ""


# ---------------------------------------------------------------------------
# The skeleton resolves to a useful error instead of spinning forever
# ---------------------------------------------------------------------------


def test_homepage_skeleton_resolves_to_a_retryable_error(tmp_path):
    # No route configured: the request 404s, exactly like an unreachable API.
    result = run(tmp_path, "index.html", [{"fn": "loadHomepageProjects", "args": []}])

    classes = [meta["className"] for meta in result["createdMeta"]]
    assert "error-state" in classes, f"no error state was rendered: {classes}"
    retry = [
        meta
        for meta in result["createdMeta"]
        if meta["className"] == "btn btn-secondary" and meta["text"] == "Try again"
    ]
    assert retry, f"the error state offered no way out: {result['createdMeta']}"
    assert "Couldn't load projects" in result["html"]
    # Loading state still resolved: aria-busy is cleared on the failure path.
    assert result["flags"]["homepage-projects"]["ariaBusy"] == "false"


def test_discover_skeleton_resolves_to_a_retryable_error(tmp_path):
    result = run(tmp_path, "discover.html", [{"fn": "loadProjects", "args": [1]}])
    assert "error-state" in result["ids"]["project-list"]
    assert "Try again" in result["ids"]["project-list"]
    assert result["flags"]["project-list"]["ariaBusy"] == "false"
    assert result["ids"]["project-list-status"] == "Couldn't load projects."


def test_project_page_reports_an_error_when_the_project_fails_to_load(tmp_path):
    result = run(
        tmp_path,
        "project_detail.html",
        [{"fn": "loadProject", "args": []}],
        location="/project/7",
    )
    classes = [meta["className"] for meta in result["createdMeta"]]
    assert "error-state" in classes, f"no error state was rendered: {classes}"
    assert any(meta["text"] == "Try again" for meta in result["createdMeta"])
    assert result["flags"]["content"]["ariaBusy"] == "false"


def test_loading_state_never_resolves_by_staying_on_a_spinner(tmp_path):
    """A failed request must clear aria-busy on every loading region."""
    for page, calls in (
        ("index.html", [{"fn": "loadHomepageProjects", "args": []}]),
        ("discover.html", [{"fn": "loadProjects", "args": [1]}]),
        ("project_detail.html", [{"fn": "loadProject", "args": []}]),
    ):
        location = "/project/7" if page == "project_detail.html" else "/"
        result = run(tmp_path, page, calls, location=location)
        busy_ids = [
            element_id
            for element_id, flag in result["flags"].items()
            if flag["ariaBusy"] == "true"
        ]
        assert busy_ids == [], f"{page} left {busy_ids} marked busy after a failure"


def test_social_proof_placeholder_resolves_to_the_real_row(tmp_path):
    result = run(
        tmp_path,
        "index.html",
        [{"fn": "loadSocialProof", "args": []}],
        fetch={
            "/api/stats": {
                "status": 200,
                "body": {"total_builders": 2, "total_projects": 1, "builders": []},
            }
        },
    )
    assert result["flags"]["social-proof"]["ariaBusy"] == "false"
    assert result["flags"]["social-proof"]["display"] == "flex"
    assert result["ids"]["social-proof-text"] == "Join 2 builders already using Critique"


def test_social_proof_placeholder_is_hidden_when_stats_fail(tmp_path):
    """No social proof may be invented: failure hides the row, it does not spin."""
    result = run(tmp_path, "index.html", [{"fn": "loadSocialProof", "args": []}])
    assert result["flags"]["social-proof"]["ariaBusy"] == "false"
    assert result["flags"]["social-proof"]["display"] == "none"
    # The placeholder stays silent: no builder sentence is invented on failure.
    assert "Join" not in result["ids"]["social-proof-text"]


# ---------------------------------------------------------------------------
# No duplicated critical requests
# ---------------------------------------------------------------------------


def test_critical_endpoints_are_requested_once_per_render(tmp_path):
    result = run(
        tmp_path,
        "index.html",
        [
            {"fn": "loadSocialProof", "args": []},
            {"fn": "loadHomepageProjects", "args": []},
            {"fn": "checkAuth", "args": []},
        ],
        fetch={
            "/api/stats": {
                "status": 200,
                "body": {"total_builders": 1, "total_projects": 1, "builders": []},
            },
            PROJECTS_URL: {"status": 200, "body": {"items": [PROJECT_ITEM], "total": 1}},
        },
    )
    urls = [request["url"] for request in result["requests"]]
    for endpoint in ("/api/stats", PROJECTS_URL, "/auth/check"):
        assert urls.count(endpoint) == 1, f"{endpoint} requested {urls.count(endpoint)}x: {urls}"
    duplicates = {url for url in urls if urls.count(url) > 1}
    assert duplicates == set(), f"duplicated requests: {sorted(duplicates)}"


def test_discover_requests_the_list_once_per_render(tmp_path):
    result = run(
        tmp_path,
        "discover.html",
        [{"fn": "loadProjects", "args": [1]}],
        fetch={
            "/api/projects/": {
                "status": 200,
                "body": {"items": [PROJECT_ITEM], "total": 1, "page": 1, "total_pages": 1},
            }
        },
    )
    list_requests = [r for r in result["requests"] if "/api/projects/" in r["url"]]
    assert len(list_requests) == 1, f"list fetched {len(list_requests)}x: {result['requests']}"
