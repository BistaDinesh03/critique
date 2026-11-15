"""Homepage social proof: real, named members -- no headcount.

The hero's social-proof row keeps its original overlapping-avatar design. It
shows only real, publicly displayable avatars from /api/stats, never a total
member count or a "+N" bubble, and never invents people.

These tests run the page's real JavaScript in the Node rendering harness and
assert on the markup it produces, plus a few source-level guards.
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

PRIMARY = "Real builders. Real projects. Honest feedback."
SUPPORTING = "Discover what people are building and help each other make it better."
LINK = "Explore their projects"

GITHUB_1 = "https://avatars.githubusercontent.com/u/109844087?v=4"
GITHUB_2 = "https://avatars.githubusercontent.com/u/69650536?v=4"


def source():
    return (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")


def run(tmp_path, calls, fetch=None, read=None):
    scenario = {
        "page": (FRONTEND_DIR / "index.html").as_posix(),
        "calls": calls,
        "read": read or {"byId": "avatar-stack"},
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


def load(tmp_path, body=None, read=None):
    body = body if body is not None else stats()
    return run(
        tmp_path,
        [{"fn": "loadSocialProof", "args": []}],
        fetch={"/api/stats": {"status": 200, "body": body}},
        read=read,
    )


def stats(**overrides):
    body = {
        "total_builders": 13,
        "total_projects": 14,
        "total_questions": 14,
        "total_responses": 43,
        "builders": [
            {"username": "HarshYeole", "avatar_url": GITHUB_1},
            {"username": "DennisKutt", "avatar_url": GITHUB_2},
        ],
    }
    body.update(overrides)
    return body


# ---------------------------------------------------------------------------
# Static copy, layout and source guards
# ---------------------------------------------------------------------------


def test_primary_and_supporting_copy():
    src = source()
    assert PRIMARY in src
    assert SUPPORTING in src


def test_explore_link_points_at_project_discovery():
    src = source()
    assert re.search(r'class="social-proof-link" href="/discover"', src)
    assert LINK in src


def test_source_keeps_original_avatar_design_and_removes_counts():
    src = source()
    assert 'class="social-proof"' in src
    assert 'id="avatar-stack"' in src
    assert "avatar-skeleton" in src
    assert not re.search(r"Join\s+\d+\s+builders", src)
    assert "avatar-more" not in src
    assert not re.search(r'class="community-proof"', src)
    assert not re.search(r'class="member-chip"', src)


def test_original_avatar_sizes_are_preserved():
    src = source()
    assert "width: 32px;" in src
    assert "height: 32px;" in src
    assert "margin-left: -8px;" in src


# ---------------------------------------------------------------------------
# Real avatars render; synthetic / unsafe ones do not
# ---------------------------------------------------------------------------


def test_real_avatars_render_from_builders(tmp_path):
    result = load(tmp_path)
    html = result["ids"]["avatar-stack"]

    assert html.count("<img") == 2
    assert f'src="{GITHUB_1}"' in html
    assert f'src="{GITHUB_2}"' in html
    assert result["flags"]["social-proof"]["display"] == "flex"
    assert result["flags"]["social-proof"]["ariaBusy"] == "false"


def test_unsafe_and_missing_avatars_are_skipped(tmp_path):
    result = load(
        tmp_path,
        stats(
            builders=[
                {"username": "email_deadbeefdeadbeef", "avatar_url": None},
                {"username": "alice", "avatar_url": "http://evil.example/a.png"},
                {"username": "bob", "avatar_url": "javascript:alert(1)"},
                {"username": "carol", "avatar_url": GITHUB_1},
            ]
        ),
    )
    html = result["ids"]["avatar-stack"]

    assert html.count("<img") == 1
    assert f'src="{GITHUB_1}"' in html
    assert "email_" not in html
    assert "evil.example" not in html
    assert "alice" not in html and "bob" not in html


def test_no_real_avatars_hides_the_row_without_inventing_people(tmp_path):
    result = load(tmp_path, stats(builders=[]))
    html = result["ids"]["avatar-stack"]

    assert html.strip() == ""
    assert result["flags"]["social-proof"]["display"] == "none"
    assert result["flags"]["social-proof"]["ariaBusy"] == "false"


def test_a_failed_request_leaves_no_placeholder_or_invented_avatars(tmp_path):
    result = run(tmp_path, [{"fn": "loadSocialProof", "args": []}])
    html = result["ids"]["avatar-stack"]

    assert html.strip() == ""
    assert result["flags"]["social-proof"]["display"] == "none"
    assert result["flags"]["social-proof"]["ariaBusy"] == "false"


def test_avatars_are_not_profile_links(tmp_path):
    """There are no public profile routes, so avatars are not anchors."""
    result = load(tmp_path)
    html = result["ids"]["avatar-stack"]
    assert "<a" not in html