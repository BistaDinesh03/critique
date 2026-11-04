"""Discover page shows an empty state when there are no projects."""

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
        shutil.which("node") is None or not HARNESS.exists(),
        reason="node or frontend_render_harness.js missing",
    ),
]

DISCOVER_PAGE = (FRONTEND_DIR / "discover.html").as_posix()

EMPTY_BODY = {"items": [], "total_pages": 0}

ONE_ITEM_BODY = {
    "items": [
        {
            "id": 1,
            "title": "Sample Project",
            "description": "D",
            "question_text": "Q?",
            "response_count": 0,
            "created_at": "2026-01-01T00:00:00Z",
        }
    ],
    "total_pages": 1,
}


def run(tmp_path, calls, body=None, read=None):
    scenario = {
        "page": DISCOVER_PAGE,
        "calls": calls,
        "read": read or {"byId": "project-list"},
        "fetch": {
            "/api/projects/": {"status": 200, "body": body or EMPTY_BODY},
        },
        "location": "/discover",
    }
    scenario = {
        "page": DISCOVER_PAGE,
        "calls": calls,
        "read": {"byId": "project-list"},
        "fetch": {
            "/api/projects/": {"status": 200, "body": body or EMPTY_BODY},
        },
        "location": "/discover",
    }
    scenario_file = tmp_path / "scenario.json"
    scenario_file.write_text(json.dumps(scenario), encoding="utf-8")

    proc = subprocess.run(
        ["node", str(HARNESS), str(scenario_file)],
        capture_output=True, text=True, encoding="utf-8", timeout=120,
    )
    assert proc.returncode == 0, f"harness crashed:\n{proc.stderr}"
    result = json.loads(proc.stdout)
    assert result["errors"] == [], f"page script errors: {result['errors']}"
    return result


# ---------------------------------------------------------------------------
# Source-level tests
# ---------------------------------------------------------------------------

def test_empty_state_exists_in_page_source():
    source = (FRONTEND_DIR / "discover.html").read_text(encoding="utf-8")
    assert "empty-state" in source
    assert "No projects waiting for feedback yet" in source
    assert "Submit a project" in source


def test_empty_state_has_css_styling():
    source = (FRONTEND_DIR / "discover.html").read_text(encoding="utf-8")
    style = source[source.index("<style>"):source.index("</style>")]
    assert ".empty-state" in style
    assert "display: flex" in style or "display:flex" in style
    assert "text-align: center" in style or "text-align:center" in style


# ---------------------------------------------------------------------------
# Render tests -- loadProjects() ko calls ke zariye dobara chalao
# ---------------------------------------------------------------------------

def test_empty_state_renders_on_load_with_zero_items(tmp_path):
    """API 0 items -> loadProjects(1) ke baad empty-state render ho."""
    result = run(
        tmp_path,
        calls=[
            # {fn: "loadProjects", args: [1]} -- loadProjects global function hai
            {"fn": "loadProjects", "args": [1]},
        ],
    )
    html = result["html"]
    print("\n=== project-list innerHTML ===")
    print(html[:800])
    assert "empty-state" in html, f"empty state nahi mila. html={html!r}"
    assert "No projects waiting for feedback yet" in html
    assert "Submit a project" in html


def test_empty_state_cta_href(tmp_path):
    result = run(
        tmp_path,
        calls=[{"fn": "loadProjects", "args": [1]}],
    )
    html = result["html"]
    assert 'href="/"' in html, f"CTA href nahi mila. html={html!r}"
    assert 'class="btn btn-primary"' in html


def test_pagination_hidden_on_empty(tmp_path):
    result = run(
        tmp_path,
        calls=[{"fn": "loadProjects", "args": [1]}],
    )
    pagination = result["flags"].get("pagination", {})
    print(f"\nDEBUG pagination flag: {pagination}")
    assert pagination.get("display") == "none", f"pagination: {pagination}"


def test_cards_render_when_items_exist(tmp_path):
    """showProjects ke bina -- sirf loadProjects se cards aa rahe hain ya nahi."""
    result = run(
        tmp_path,
        calls=[{"fn": "loadProjects", "args": [1]}],
        body=ONE_ITEM_BODY,
    )
    print("\n=== requests ===", result["requests"])
    print("=== html ===", repr(result["html"]))
    print("=== errors ===", result["errors"])
    html = result["html"]
    # Agar html khaali hai toh empty state bhi nahi aaya
    # Iska matlab loadProjects ne fetch se data hi nahi liya
    assert html != "", f"project-list khaali hai. requests={result['requests']}"
    assert "project-card" in html, f"cards nahi bane. html={html!r}"
    result = run(
        tmp_path,
        calls=[
            {"fn": "loadProjects", "args": [1]},
            # data check karo
            {"evaluate": "typeof data", "as": "data_type"},
        ],
        body=ONE_ITEM_BODY,
    )
    print("\n=== DEBUG ===")
    print("html:", repr(result["html"]))
    print("values:", result["values"])
    print("requests:", result["requests"])
    print("errors:", result["errors"])
    html = result["html"]
    assert "project-card" in html, f"cards nahi bane. html={html!r}"
