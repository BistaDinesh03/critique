"""Homepage community proof: real, named members -- never a headcount.

The hero's community row introduces actual Critique members who have a public
GitHub login and a public avatar. It must never show a total account count or a
"+N" filler, and it must degrade to fewer members -- or none -- rather than
inventing people.

These tests run the page's real JavaScript in the Node rendering harness and
assert on the markup it produces, plus a couple of source-level guards that the
copy can never drift back to a number.
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

HEADLINE = "Real people. Real things being built."
SUPPORTING = "Meet builders sharing their projects and helping each other improve."

GITHUB_1 = "https://avatars.githubusercontent.com/u/109844087?v=4"
GITHUB_2 = "https://avatars.githubusercontent.com/u/69650536?v=4"


def source():
    return (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")


def run(tmp_path, calls, fetch=None, read=None):
    scenario = {
        "page": (FRONTEND_DIR / "index.html").as_posix(),
        "calls": calls,
        "read": read or {"byId": "member-row"},
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
        "public_members": [
            {"username": "HarshYeole", "avatar_url": GITHUB_1},
            {"username": "DennisKutt", "avatar_url": GITHUB_2},
        ],
    }
    body.update(overrides)
    return body


# ---------------------------------------------------------------------------
# Static copy and layout
# ---------------------------------------------------------------------------


def test_headline_and_supporting_copy():
    src = source()
    assert HEADLINE in src
    assert SUPPORTING in src


def test_explore_cta_points_at_project_discovery():
    src = source()
    assert re.search(r'class="community-explore" href="/discover"', src)


def test_source_never_contains_a_builder_count_or_plus_n():
    src = source()
    assert not re.search(r"Join\s+\d+\s+builders", src)
    assert "already using Critique" not in src
    assert "avatar-more" not in src
    assert not re.search(r'class="avatar-stack"', src)


def test_community_row_ships_as_a_loading_placeholder():
    src = source()
    # The section announces its busy state; the row starts as skeletons so the
    # hero does not jump, and it is not a claim of anything yet.
    assert 'id="community-proof"' in src
    assert re.search(r'id="community-proof"[^>]*aria-busy="true"', src)
    assert "member-chip-skeleton" in src


# ---------------------------------------------------------------------------
# Real members render as name + avatar
# ---------------------------------------------------------------------------


def test_named_members_render_with_their_public_avatars(tmp_path):
    result = load(tmp_path)
    html = result["ids"]["member-row"]

    assert html.count('class="member-chip"') == 2
    assert f'src="{GITHUB_1}"' in html
    assert f'src="{GITHUB_2}"' in html
    assert "@HarshYeole" in html
    assert "@DennisKutt" in html
    assert result["flags"]["member-row"]["hidden"] is False
    assert result["flags"]["community-proof"]["display"] == "flex"
    assert result["flags"]["community-proof"]["ariaBusy"] == "false"


def test_member_avatars_are_not_fake_profile_links(tmp_path):
    """There are no public profile routes, so avatars are not links."""
    result = load(tmp_path)
    html = result["ids"]["member-row"]
    assert "<a" not in html


def test_avatar_images_are_decorative_and_sized(tmp_path):
    result = load(tmp_path)
    html = result["ids"]["member-row"]
    assert 'alt=""' in html
    assert 'width="26"' in html and 'height="26"' in html


def test_the_total_builder_count_is_never_rendered(tmp_path):
    result = load(tmp_path, stats(total_builders=1337))
    html = result["ids"]["member-row"]
    assert "1337" not in html
    assert "Join" not in html


# ---------------------------------------------------------------------------
# Only genuine public profiles; never invented people
# ---------------------------------------------------------------------------


def test_email_signups_and_unsafe_avatars_are_excluded(tmp_path):
    result = load(
        tmp_path,
        stats(
            public_members=[
                {"username": "email_deadbeefdeadbeef", "avatar_url": None},
                {"username": "alice", "avatar_url": "http://evil.example/a.png"},
                {"username": "bob", "avatar_url": "javascript:alert(1)"},
                {"username": "carol", "avatar_url": GITHUB_1},
            ]
        ),
    )
    html = result["ids"]["member-row"]

    assert html.count('class="member-chip"') == 1
    assert "@carol" in html
    assert "email_" not in html
    assert "evil.example" not in html
    assert "alice" not in html and "bob" not in html


def test_falls_back_to_builders_when_public_members_is_absent(tmp_path):
    body = stats()
    body.pop("public_members")
    body["builders"] = [
        {"username": "email_deadbeefdeadbeef", "avatar_url": None},
        {"username": "HarshYeole", "avatar_url": GITHUB_1},
    ]
    result = load(tmp_path, body)
    html = result["ids"]["member-row"]

    assert html.count('class="member-chip"') == 1
    assert "@HarshYeole" in html
    assert "email_" not in html


def test_a_short_list_is_shown_gracefully(tmp_path):
    result = load(
        tmp_path,
        stats(public_members=[{"username": "HarshYeole", "avatar_url": GITHUB_1}]),
    )
    html = result["ids"]["member-row"]
    assert html.count('class="member-chip"') == 1
    assert "avatar-more" not in html
    assert result["flags"]["member-row"]["hidden"] is False
    assert result["flags"]["community-proof"]["display"] == "flex"


def test_the_row_is_capped_at_six_members(tmp_path):
    roster = [
        {"username": f"builder{i}", "avatar_url": f"https://avatars.githubusercontent.com/u/{i}?v=4"}
        for i in range(8)
    ]
    result = load(tmp_path, stats(public_members=roster))
    html = result["ids"]["member-row"]
    assert html.count('class="member-chip"') == 6
    assert "avatar-more" not in html


def test_no_public_members_hides_the_row_without_inventing_people(tmp_path):
    result = load(tmp_path, stats(public_members=[]))
    html = result["ids"]["member-row"]

    assert html.strip() == ""
    assert result["flags"]["member-row"]["hidden"] is True
    assert result["flags"]["community-proof"]["display"] == "none"
    assert result["flags"]["community-proof"]["ariaBusy"] == "false"
    assert "Join" not in html
    assert "@" not in html


def test_a_failed_request_leaves_no_placeholder_or_invented_members(tmp_path):
    result = run(tmp_path, [{"fn": "loadSocialProof", "args": []}])
    html = result["ids"]["member-row"]

    assert html.strip() == ""
    assert result["flags"]["member-row"]["hidden"] is True
    assert result["flags"]["community-proof"]["display"] == "none"
    assert result["flags"]["community-proof"]["ariaBusy"] == "false"
