"""Discover and homepage cards show "Feedback given" only when has_responded."""

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
    pytest.mark.skipif(shutil.which("node") is None, reason="node is required"),
]

def project(pid, responded):
    return {
        "id": pid,
        "title": f"Project {pid}",
        "description": "d",
        "question_text": "q?",
        "response_count": 1,
        "has_responded": responded,
    }

def render(tmp_path, page, calls, fetch=None, location="/", read=None):
    scenario = {
        "page": (FRONTEND_DIR / page).as_posix(),
        "calls": calls,
        "read": read or {"created": True},
        "fetch": fetch or {},
        "location": location,
    }
    f = tmp_path / "scenario.json"
    f.write_text(json.dumps(scenario), encoding="utf-8")
    proc = subprocess.run(
        ["node", str(HARNESS), str(f)],
        capture_output=True, text=True, encoding="utf-8", timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["errors"] == [], result["errors"]
    return result["html"]

def test_discover_badge_only_on_responded_cards(tmp_path):
    html = render(
        tmp_path, "discover.html",
        [{"fn": "showProjects", "args": [[project(1, True), project(2, False)]]}],
        location="/discover",
    )
    assert html.count("Feedback given") == 1

def test_homepage_badge_only_on_responded_cards(tmp_path):
    body = {"items": [project(1, True), project(2, False)], "total": 2,
            "page": 1, "page_size": 6, "total_pages": 1}
    html = render(
        tmp_path, "index.html",
        [{"fn": "loadHomepageProjects", "args": []}],
        fetch={"/api/projects/?page=1&page_size=6": {"status": 200, "body": body}},
        read={"byId": "homepage-projects"},
    )
    assert html.count("Feedback given") == 1
