"""Homepage social proof: original overlapping-avatar design, improved wording.

The hero keeps its original overlapping-avatar social-proof row (32px circles,
skeleton placeholders, +N bubble, divider). Only the wording changed and the
count stays dynamic from /api/stats. No count-free replacement layout, no extra
Discover link, no below-50/50+ switching.

These tests run the page's real JavaScript in the Node rendering harness.
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


def load(tmp_path, total, builders=None, read=None):
    if builders is None:
        builders = [
            {"username": "HarshYeole", "avatar_url": GITHUB_1},
            {"username": "DennisKutt", "avatar_url": GITHUB_2},
        ]
    body = {
        "total_builders": total,
        "total_projects": 14,
        "total_questions": 14,
        "total_responses": 43,
        "builders": builders,
    }
    return run(
        tmp_path,
        [{"fn": "loadSocialProof", "args": []}],
        fetch={"/api/stats": {"status": 200, "body": body}},
        read=read,
    )


# ---------------------------------------------------------------------------
# Static design / source guards
# ---------------------------------------------------------------------------


def test_original_avatar_design_is_preserved():
    src = source()
    assert 'class="social-proof"' in src
    assert 'id="avatar-stack"' in src
    assert "width: 32px;" in src
    assert "height: 32px;" in src
    assert "margin-left: -8px;" in src
    assert "avatar-skeleton" in src
    assert "avatar-more" in src
    # No count-free replacement layout.
    assert "community-proof" not in src
    assert "member-chip" not in src
    # No extra Discover link in the social-proof section.
    assert "social-proof-link" not in src


def test_no_hardcoded_count_in_source():
    src = source()
    assert not re.search(r"Join\s+\d+\s+members", src)
    assert not re.search(r"Join\s+\d+\s+builders", src)


def test_new_wording_present_in_source():
    src = source()
    assert "members on Critique." in src
    assert "Discover real projects. Share thoughtful feedback. Build better together." in src


def test_original_avatar_sizes_are_preserved():
    src = source()
    assert "width: 32px;" in src
    assert "height: 32px;" in src
    assert "margin-left: -8px;" in src


# ---------------------------------------------------------------------------
# Dynamic count and +N
# ---------------------------------------------------------------------------


def test_headline_uses_dynamic_count(tmp_path):
    for total in (1, 2, 14, 49, 50, 65, 100):
        result = load(tmp_path, total)
        text = result["ids"]["social-proof-text"]
        assert text == f"Join {total} members on Critique.", (total, text)


def test_plus_n_calculation(tmp_path):
    # builders has 2 entries -> shown.length 2 -> +N = total - 2
    result = load(tmp_path, 14)
    html = result["ids"]["avatar-stack"]
    assert "+12" in html, html
    assert 'class="avatar-more"' in html


def test_plus_n_with_fewer_visible_avatars(tmp_path):
    # builders list has 2 entries -> shown.length 2 -> +N = total - 2
    builders = [
        {"username": "carol", "avatar_url": GITHUB_1},
        {"username": "dave", "avatar_url": GITHUB_2},
    ]
    result = load(tmp_path, 14, builders=builders)
    html = result["ids"]["avatar-stack"]
    assert "+12" in html, html


def test_no_plus_n_when_total_not_greater_than_shown(tmp_path):
    # total=2, shown=2 -> remaining 0 -> no bubble
    builders = [
        {"username": "carol", "avatar_url": GITHUB_1},
        {"username": "dave", "avatar_url": GITHUB_2},
    ]
    result = load(tmp_path, 2, builders=builders)
    html = result["ids"]["avatar-stack"]
    assert "avatar-more" not in html


def test_count_does_not_depend_on_avatar_count(tmp_path):
    # Even with 0 real avatars, the count still reflects total_builders.
    result = load(tmp_path, 65, builders=[])
    # section hidden when total===0 only; here total>0 so visible with +65
    html = result["ids"]["avatar-stack"]
    assert "+65" in html


# ---------------------------------------------------------------------------
# Real avatars + fallback identicons
# ---------------------------------------------------------------------------


def test_real_avatars_render_as_images(tmp_path):
    result = load(tmp_path, 14)
    html = result["ids"]["avatar-stack"]
    assert html.count("<img") == 2
    assert f'src="{GITHUB_1}"' in html
    assert f'src="{GITHUB_2}"' in html


def test_synthetic_accounts_get_fallback_identicon(tmp_path):
    result = load(
        tmp_path,
        14,
        builders=[
            {"username": "email_deadbeefdeadbeef", "avatar_url": None},
            {"username": "carol", "avatar_url": GITHUB_1},
        ],
    )
    html = result["ids"]["avatar-stack"]
    # one real img + one identicon fallback
    assert html.count("<img") == 1
    assert 'class="avatar-fallback"' in html
    assert "<svg" in html
    # synthetic username is not exposed
    assert "email_deadbeefdeadbeef" not in html


def test_unsafe_avatar_urls_are_not_loaded(tmp_path):
    result = load(
        tmp_path,
        14,
        builders=[
            {"username": "alice", "avatar_url": "javascript:alert(1)"},
            {"username": "bob", "avatar_url": "http://evil.example/a.png"},
            {"username": "carol", "avatar_url": GITHUB_1},
        ],
    )
    html = result["ids"]["avatar-stack"]
    assert html.count("<img") == 1
    assert f'src="{GITHUB_1}"' in html
    assert html.count('class="avatar-fallback"') == 2


def test_avatars_are_not_profile_links(tmp_path):
    result = load(tmp_path, 14)
    html = result["ids"]["avatar-stack"]
    assert "<a" not in html


# ---------------------------------------------------------------------------
# Visibility, loading, errors
# ---------------------------------------------------------------------------


def test_section_hidden_when_zero_users(tmp_path):
    result = load(tmp_path, 0, builders=[])
    assert result["flags"]["social-proof"]["display"] == "none"
    assert result["flags"]["social-proof"]["ariaBusy"] == "false"


def test_failed_request_hides_the_row(tmp_path):
    result = run(tmp_path, [{"fn": "loadSocialProof", "args": []}])
    assert result["flags"]["social-proof"]["display"] == "none"
    assert result["flags"]["social-proof"]["ariaBusy"] == "false"


def test_loading_placeholder_has_no_count(tmp_path):
    src = source()
    assert "skeleton social-proof-skeleton-line" in src