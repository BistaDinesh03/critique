"""Frontend render tests for Discover "Hide projects I've answered" (#840)."""

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
    pytest.mark.skipif(shutil.which("node") is None, reason="node is required for rendering"),
]


def _run_discover(tmp_path, calls, fetch=None, location="/discover", read=None):
    scenario = {
        "page": (FRONTEND_DIR / "discover.html").as_posix(),
        "calls": calls,
        "read": read or {"byId": "project-list"},
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


def _sample_project(pid, title=None):
    return {
        "id": pid,
        "title": title or f"Project {pid}",
        "description": "A test project",
        "question_text": "Does this make sense?",
        "response_count": 2,
        "has_responded": False,
    }


def test_discover_toggle_updates_fetch_url_syncs_url_and_resets_page(tmp_path):
    fetch_routes = {
        "/auth/check": {"status": 200, "body": {"authenticated": True}},
        "/api/projects/?page=1&page_size=9&hide_answered=true": {
            "status": 200,
            "body": {"items": [_sample_project(10)], "total": 12, "page": 1, "page_size": 9, "total_pages": 2},
        },
        "/api/projects/?page=2&page_size=9&hide_answered=true": {
            "status": 200,
            "body": {"items": [_sample_project(20)], "total": 12, "page": 2, "page_size": 9, "total_pages": 2},
        },
        "/api/projects/?page=1&page_size=9": {
            "status": 200,
            "body": {"items": [_sample_project(1), _sample_project(2)], "total": 2, "page": 1, "page_size": 9, "total_pages": 1},
        },
        "/api/projects/?page=2&page_size=9": {
            "status": 200,
            "body": {"items": [_sample_project(3)], "total": 12, "page": 2, "page_size": 9, "total_pages": 2},
        },
    }

    calls = [
        {
            "evaluate": (
                "(function(){"
                "  window.__pushed = [];"
                "  history.pushState = function(state, title, url) {"
                "    window.__pushed.push(String(url));"
                "    var q = String(url).indexOf('?');"
                "    window.location.search = q === -1 ? '' : String(url).slice(q);"
                "  };"
                "  return true;"
                "})()"
            ),
            "as": "hooked",
        },
        {"fn": "setHideAnswered", "args": [True]},
        {"evaluate": "currentPage", "as": "pageAfterEnable"},
        {"evaluate": "document.getElementById('hide-answered-toggle').checked", "as": "checkedAfterEnable"},
        {"fn": "changePage", "args": [1]},
        {"evaluate": "currentPage", "as": "pageAfterNext"},
        {"fn": "setHideAnswered", "args": [False]},
        {"evaluate": "currentPage", "as": "pageAfterDisable"},
        {"evaluate": "document.getElementById('hide-answered-toggle').checked", "as": "checkedAfterDisable"},
        {"evaluate": "window.__pushed", "as": "pushedUrls"},
    ]

    result = _run_discover(tmp_path, calls, fetch=fetch_routes, location="/discover?page=2")
    values = result["values"]
    req_urls = [r["url"] for r in result["requests"]]

    assert values["pageAfterEnable"] == 1
    assert values["checkedAfterEnable"] is True
    assert values["pageAfterNext"] == 2
    assert values["pageAfterDisable"] == 1
    assert values["checkedAfterDisable"] is False

    assert "/api/projects/?page=1&page_size=9&hide_answered=true" in req_urls
    assert "/api/projects/?page=2&page_size=9&hide_answered=true" in req_urls
    assert "/api/projects/?page=1&page_size=9" in req_urls

    assert values["pushedUrls"][0] == "/discover?hide_answered=1"
    assert "hide_answered=1" in values["pushedUrls"][1]
    assert "page=2" in values["pushedUrls"][1]
    assert values["pushedUrls"][2] == "/discover"


def test_discover_filtered_empty_state_and_turn_off_action(tmp_path):
    fetch_routes = {
        "/auth/check": {"status": 200, "body": {"authenticated": True}},
        "/api/projects/?page=1&page_size=9&hide_answered=true": {
            "status": 200,
            "body": {"items": [], "total": 0, "page": 1, "page_size": 9, "total_pages": 1},
        },
        "/api/projects/?page=1&page_size=9": {
            "status": 200,
            "body": {"items": [_sample_project(99, "Restored Project")], "total": 1, "page": 1, "page_size": 9, "total_pages": 1},
        },
    }

    calls = [
        {"fn": "loadProjects", "args": [1]},
        {"evaluate": "document.getElementById('project-list').innerHTML", "as": "emptyHtml"},
        {"evaluate": "document.getElementById('hide-answered-toggle').checked", "as": "checkedBefore"},
        {"clickId": "turn-off-hide-answered"},
        {"evaluate": "document.getElementById('hide-answered-toggle').checked", "as": "checkedAfter"},
        {"evaluate": "document.getElementById('project-list').innerHTML", "as": "restoredHtml"},
    ]

    result = _run_discover(tmp_path, calls, fetch=fetch_routes, location="/discover?hide_answered=1")
    values = result["values"]

    assert values["checkedBefore"] is True
    assert (
        "You've answered every project here. Turn off the filter to see them again, or submit a project of your own."
        in values["emptyHtml"]
    )
    assert "No projects waiting for feedback yet" not in values["emptyHtml"]
    assert 'href="/"' in values["emptyHtml"]
    assert "Submit a project" in values["emptyHtml"]

    assert values["checkedAfter"] is False
    req_urls = [r["url"] for r in result["requests"]]
    assert "/api/projects/?page=1&page_size=9&hide_answered=true" in req_urls
    assert "/api/projects/?page=1&page_size=9" in req_urls
    assert "Restored Project" in values["restoredHtml"] or any(
        "Restored Project" in html for html in result["created"]
    )


def test_discover_guest_control_disabled_with_hint_and_default_empty_state(tmp_path):
    fetch_routes = {
        "/auth/check": {"status": 401, "body": {"detail": "Not authenticated"}},
        "/api/projects/?page=1&page_size=9": {
            "status": 200,
            "body": {"items": [], "total": 0, "page": 1, "page_size": 9, "total_pages": 1},
        },
    }

    calls = [
        {"fn": "loadProjects", "args": [1]},
        {"evaluate": "document.getElementById('hide-answered-toggle').disabled", "as": "toggleDisabled"},
        {"evaluate": "document.getElementById('hide-answered-toggle').checked", "as": "toggleChecked"},
        {"evaluate": "document.getElementById('hide-answered-hint').hidden", "as": "hintHidden"},
        {"evaluate": "document.getElementById('project-list').innerHTML", "as": "emptyHtml"},
    ]

    result = _run_discover(tmp_path, calls, fetch=fetch_routes, location="/discover")
    values = result["values"]
    assert values["toggleDisabled"] is True
    assert values["toggleChecked"] is False
    assert values["hintHidden"] is False
    assert "No projects waiting for feedback yet" in values["emptyHtml"]
    assert "You've answered every project here." not in values["emptyHtml"]
