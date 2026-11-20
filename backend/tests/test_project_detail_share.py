"""Project detail header sharing: copy link, disclosure panel, and fallback."""

import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import unquote

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"
HARNESS = Path(__file__).resolve().parent / "frontend_render_harness.js"
TEST_ORIGIN = "http://testserver"

pytestmark = [
    pytest.mark.frontend_render,
    pytest.mark.skipif(
        shutil.which("node") is None,
        reason="node is required to run the frontend rendering harness",
    ),
]

PROJECT_DETAIL = {
    "project": {
        "id": 1,
        "title": "Akiya Scout",
        "description": "Scans listings for abandoned houses",
        "url": "https://akiya-scout.example",
        "image_url": None,
        "owner_id": 1,
        "response_count": 0,
        "created_at": "2026-09-01T10:00:00",
    },
    "question": {
        "id": 1,
        "project_id": 1,
        "text": "Is the price shown up front?",
        "is_active": True,
    },
    "is_owner": False,
}

CANONICAL_URL = TEST_ORIGIN + "/project/1"


def run_detail(tmp_path, calls, fetch=None, location="/project/1", extra=None):
    scenario = {
        "page": (FRONTEND_DIR / "project_detail.html").as_posix(),
        "calls": calls,
        "read": {"byId": "content"},
        "fetch": fetch or {},
        "location": location,
    }
    if extra:
        scenario.update(extra)
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


def events(result, name):
    marker = "event_name=" + name
    return [
        r
        for r in result["requests"]
        if (i := r["url"].find(marker)) != -1
        and (i + len(marker) == len(r["url"]) or r["url"][i + len(marker)] == "&")
    ]


def share_actions(result):
    return [
        m
        for m in result["createdMeta"]
        if (m.get("className") or "").split(" ")[0] == "share-action"
    ]


def native_controls(result):
    return [
        m
        for m in result["createdMeta"]
        if "share-native" in (m.get("className") or "")
    ]


def test_project_detail_loads_share_script_after_ui_js():
    source = (FRONTEND_DIR / "project_detail.html").read_text(encoding="utf-8")
    ui_tag = '<script src="/static/ui.js"></script>'
    share_tag = '<script src="/static/share.js"></script>'
    assert ui_tag in source
    assert share_tag in source
    ui_idx = source.index(ui_tag)
    share_idx = source.index(share_tag)
    assert share_idx > ui_idx
    between = source[ui_idx + len(ui_tag) : share_idx]
    assert "<script" not in between


def test_initial_render_hides_share_panel_and_fires_no_share_ui_shown(tmp_path):
    result = run_detail(
        tmp_path,
        [{"fn": "renderProject", "args": [PROJECT_DETAIL, []]}],
        location="/project/1",
    )

    html = result["html"]
    assert 'id="copy-project-link"' in html
    assert 'id="toggle-project-share"' in html
    assert 'aria-controls="project-share-panel"' in html
    assert result["flags"]["toggle-project-share"]["ariaExpanded"] == "false"
    assert result["flags"]["project-share-panel"]["hidden"] is True
    assert share_actions(result) == []
    assert events(result, "share_ui_shown") == []


def test_toggle_share_reveals_canonical_actions_and_tracks_once(tmp_path):
    result = run_detail(
        tmp_path,
        [
            {
                "evaluate": (
                    "window.location.href = 'http://testserver/project/1?resume=feedback&utm=test'; 'set'"
                ),
                "as": "hrefSet",
            },
            {"fn": "renderProject", "args": [PROJECT_DETAIL, []]},
            {"clickId": "toggle-project-share"},
            {"clickId": "toggle-project-share"},
            {"clickId": "toggle-project-share"},
        ],
        location="/project/1?resume=feedback&utm=test",
    )

    assert result["flags"]["project-share-panel"]["hidden"] is False
    assert result["flags"]["toggle-project-share"]["ariaExpanded"] == "true"

    actions = share_actions(result)
    assert [a.get("text") for a in actions] == ["X", "Reddit", "Copy link", "Copy post"]
    assert native_controls(result) == []

    # share_ui_shown fires once on first reveal, never again on close/re-open.
    ui_events = events(result, "share_ui_shown")
    assert len(ui_events) == 1
    assert "project_id=1" in ui_events[0]["url"]

    # X and Reddit compose links use project title and canonical URL without query params.
    x_link = next(a for a in actions if a.get("text") == "X")
    reddit_link = next(a for a in actions if a.get("text") == "Reddit")

    assert x_link["href"].startswith("https://twitter.com/intent/tweet?text=")
    x_text = unquote(x_link["href"].split("text=", 1)[1])
    assert "Akiya Scout" in x_text
    assert CANONICAL_URL in x_text
    assert "resume=feedback" not in x_text
    assert "utm=test" not in x_text

    assert reddit_link["href"].startswith("https://www.reddit.com/submit?url=")
    reddit_query = reddit_link["href"].split("?", 1)[1].split("&")
    reddit_url = unquote(reddit_query[0].split("=", 1)[1])
    reddit_title = unquote(reddit_query[1].split("title=", 1)[1])
    assert reddit_url == CANONICAL_URL
    assert reddit_title == "Akiya Scout"
    assert "resume=feedback" not in reddit_link["href"]
    assert "utm=test" not in reddit_link["href"]


def test_toggle_share_renders_native_share_only_when_supported(tmp_path):
    result = run_detail(
        tmp_path,
        [
            {
                "evaluate": (
                    "window.__shares = []; "
                    "navigator.share = function(data) { "
                    "window.__shares.push(data); return Promise.resolve(); }; 'installed'"
                ),
                "as": "shareStub",
            },
            {"fn": "renderProject", "args": [PROJECT_DETAIL, []]},
            {"clickId": "toggle-project-share"},
            {"clickCreatedContaining": "Share project"},
            {"evaluate": "window.__shares", "as": "shares"},
        ],
        location="/project/1?resume=feedback&utm=test",
    )

    assert len(native_controls(result)) == 1
    assert [a.get("text") for a in share_actions(result)] == [
        "X",
        "Reddit",
        "Copy link",
        "Copy post",
    ]
    assert len(result["values"]["shares"]) == 1
    shared = result["values"]["shares"][0]
    assert shared["title"] == "Akiya Scout"
    assert shared["url"] == CANONICAL_URL
    assert shared["text"].endswith(CANONICAL_URL)
    assert "resume=feedback" not in shared["url"]


def test_copy_project_link_copies_canonical_url_and_tracks_event(tmp_path):
    result = run_detail(
        tmp_path,
        [
            {
                "evaluate": (
                    "window.location.href = 'http://testserver/project/1?resume=feedback&utm=test'; 'set'"
                ),
                "as": "hrefSet",
            },
            {"fn": "renderProject", "args": [PROJECT_DETAIL, []]},
            {"clickId": "copy-project-link"},
        ],
        location="/project/1?resume=feedback&utm=test",
    )

    assert result["clipboard"] == [CANONICAL_URL]
    copy_events = events(result, "share_copy_link")
    assert len(copy_events) == 1
    assert "project_id=1" in copy_events[0]["url"]
    assert any(t["type"] == "success" for t in result["toasts"])
    assert events(result, "share_ui_shown") == []


def test_copy_project_link_does_not_track_when_clipboard_fails(tmp_path):
    result = run_detail(
        tmp_path,
        [
            {"fn": "renderProject", "args": [PROJECT_DETAIL, []]},
            {"clickId": "copy-project-link"},
        ],
        location="/project/1",
        extra={"clipboardReject": True},
    )

    assert result["clipboard"] == []
    assert events(result, "share_copy_link") == []
    assert any(t["type"] == "error" for t in result["toasts"])


def test_progressive_enhancement_without_critique_share(tmp_path):
    result = run_detail(
        tmp_path,
        [
            {
                "evaluate": (
                    "delete window.CritiqueShare; "
                    "window.location.href = 'http://testserver/project/1?resume=feedback&utm=test'; 'deleted'"
                ),
                "as": "deleted",
            },
            {"fn": "renderProject", "args": [PROJECT_DETAIL, []]},
            {"clickId": "copy-project-link"},
        ],
        location="/project/1?resume=feedback&utm=test",
    )

    html = result["html"]
    assert 'id="copy-project-link"' in html
    assert 'id="toggle-project-share"' not in html
    assert 'id="project-share-panel"' not in html
    assert result["clipboard"] == [CANONICAL_URL]
    copy_events = events(result, "share_copy_link")
    assert len(copy_events) == 1
    assert "project_id=1" in copy_events[0]["url"]
    assert events(result, "share_ui_shown") == []


def test_header_share_controls_enforce_44px_tap_targets_and_mobile_wrap():
    source = (FRONTEND_DIR / "project_detail.html").read_text(encoding="utf-8")

    actions_btn = re.search(r"\.project-header-actions\s+\.btn\s*\{(.*?)\}", source, re.S)
    assert actions_btn is not None
    assert "min-height: 44px" in actions_btn.group(1)
    assert "min-width: 44px" in actions_btn.group(1)

    panel_action = re.search(r"\.project-share-panel\s+\.share-action\s*\{(.*?)\}", source, re.S)
    assert panel_action is not None
    assert "min-height: 44px" in panel_action.group(1)
    assert "min-width: 44px" in panel_action.group(1)

    panel_native = re.search(r"\.project-share-panel\s+\.share-native\s*\{(.*?)\}", source, re.S)
    assert panel_native is not None
    assert "min-height: 44px" in panel_native.group(1)

    # Mobile media query keeps a 2-column grid with minmax(0, 1fr) so 360px has no overflow.
    mobile_match = re.search(r"@media\s*\(max-width:\s*600px\)\s*\{(.*)\}\s*</style>", source, re.S)
    assert mobile_match is not None
    mobile_css = mobile_match.group(1)
    assert ".project-share-panel .card-share" in mobile_css
    assert "repeat(2, minmax(0, 1fr))" in mobile_css
