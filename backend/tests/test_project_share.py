"""Optional sharing: the success state, the platform links, the card row.

Phases 2-6 and 9 of the sharing pass. After the API confirms a 201, the
project form shows a success state with the real project -- title, public
link, the question it asked -- and an optional, user-initiated share
section. My Projects gets an inline share row per card, driven by the same
``CritiqueShare`` module.

Sharing never posts anything by itself: the platform links only build that
platform's own compose/share URL (fixed domains, correctly encoded), the
copy buttons only touch the clipboard, and the whole section can be
skipped. The panel offers exactly four compact, icon-labelled actions —
X, Reddit, Copy link, Copy post — and nothing else. Behaviour runs through
the Node rendering harness; URL safety and wiring are also asserted
against the source where a live DOM is not needed.

Requires ``node`` on PATH; the whole module is skipped when it is missing.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import unquote

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"
STATIC_DIR = BACKEND_DIR.parent / "static"
HARNESS = Path(__file__).resolve().parent / "frontend_render_harness.js"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node is required to run the frontend rendering harness",
)

HOMEPAGE_URL = "/api/projects/?page=1&page_size=6"
SUBMIT_URL = "/api/projects/"
MY_PROJECTS_URL = "/api/projects/my/list"
TEST_ORIGIN = "http://testserver"

# The body POST /api/projects/ really answers with (ProjectWithQuestion).
CREATED_PROJECT = {
    "project": {
        "id": 9,
        "title": "Akiya Scout",
        "description": "Scans listings for abandoned houses",
        "url": "https://akiya-scout.example",
        "image_url": None,
        "owner_id": 1,
        "response_count": 0,
        "created_at": "2026-09-01T10:00:00",
    },
    "question": {
        "id": 9,
        "project_id": 9,
        "text": "Is the price shown up front?",
        "is_active": True,
    },
}

PUBLIC_URL = TEST_ORIGIN + "/project/9"
DEFAULT_POST = (
    "I just shared my project, Akiya Scout, on Critique and would love some "
    "honest feedback. What do you think, and what could I improve?\n\n" + PUBLIC_URL
)

# Values are set the way a visitor types them; the harness reads element
# values directly and the submit handler builds its payload from them.
FILL_PROJECT = [
    {
        "evaluate": (
            "document.getElementById('title').value = 'Akiya Scout'; "
            "document.getElementById('description').value = 'Scans listings for abandoned houses'; "
            "document.getElementById('url').value = 'https://akiya-scout.example'; "
            "document.getElementById('image_url').value = ''; "
            "document.getElementById('question').value = 'Is the price shown up front?'; "
            "'filled'"
        ),
        "as": "filled",
    },
    {"submitId": "project-form"},
]

# The submit handler is async: give its fetch + render a tick before calls
# that interact with the panel it produced.
WAIT_FOR_RENDER = {
    "evaluate": (
        "new Promise(function(r) { setTimeout(function() { r('waited'); }, 10); })"
    ),
    "as": "waited",
}


def run(tmp_path, page, calls, fetch=None, location="/"):
    """Execute the page's scripts and return the harness result."""
    scenario = {
        "page": (FRONTEND_DIR / page).as_posix(),
        "calls": calls,
        "read": {"created": True},
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


def events(result, name):
    """Requests that tracked exactly `name` (not its longer relatives)."""
    marker = "event_name=" + name
    return [
        r
        for r in result["requests"]
        if (i := r["url"].find(marker)) != -1
        and (i + len(marker) == len(r["url"]) or r["url"][i + len(marker)] == "&")
    ]


def posts(result):
    """The project submissions themselves (analytics also posts, elsewhere)."""
    return [
        r for r in result["requests"]
        if r["method"] == "POST" and r["url"] == SUBMIT_URL
    ]


def texts(result):
    """Text of every created leaf, in creation order."""
    return [m["text"] for m in result["createdMeta"] if m.get("text")]


def anchors(result):
    return [m for m in result["createdMeta"] if (m.get("tag") or "").lower() == "a"]


def submitted_page(tmp_path, fetch_overrides=None, extra_calls=None):
    """Fill the form, submit it, wait, then run any extra calls."""
    fetch = {
        HOMEPAGE_URL: {"status": 200, "body": {"total": 0, "items": []}},
        SUBMIT_URL: {"status": 201, "body": CREATED_PROJECT},
    }
    if fetch_overrides:
        fetch.update(fetch_overrides)
    calls = list(FILL_PROJECT) + [WAIT_FOR_RENDER] + list(extra_calls or [])
    return run(tmp_path, "index.html", calls, fetch=fetch)


def mobile_blocks(source):
    """Bodies of every phone-width media query in the stylesheet."""
    blocks = []
    for match in re.finditer(r"@media[^{]*max-width:\s*600px[^{]*\{", source):
        depth = 1
        index = match.end()
        while index < len(source) and depth:
            if source[index] == "{":
                depth += 1
            elif source[index] == "}":
                depth -= 1
            index += 1
        blocks.append(source[match.end():index - 1])
    return blocks


# ---------------------------------------------------------------------------
# Phase 2: the success state after a confirmed submission
# ---------------------------------------------------------------------------


def test_successful_submission_shows_the_live_success_state(tmp_path):
    result = submitted_page(tmp_path)

    # The real signals: recorded, reported, no draft left behind.
    assert len(posts(result)) == 1
    assert len(events(result, "project_submit")) == 1
    assert "critique_project_draft" not in result["storage"]["session"]

    seen = texts(result)
    assert "Your project is live!" in seen
    assert any("has been shared on Critique" in t for t in seen)
    assert "Let more people discover your project" in seen
    assert any("reach more builders" in t for t in seen)


def test_success_state_shows_the_real_title_link_and_question(tmp_path):
    result = submitted_page(tmp_path)
    seen = texts(result)

    assert "Akiya Scout" in seen
    assert "Scans listings for abandoned houses" in seen
    assert "Is the price shown up front?" in seen

    link = next(m for m in result["createdMeta"] if m.get("href") == PUBLIC_URL)
    assert link["text"] == PUBLIC_URL

    # The share section exists inside the success state, marked optional.
    share = next(
        m for m in result["createdMeta"]
        if (m.get("tag") or "").lower() == "section"
        and m.get("className") == "share-section"
    )
    assert share is not None
    # And a clear way onward is always offered next to the share options.
    assert any(
        m.get("href") == "/my-projects" and m.get("text") == "Continue to My Projects"
        for m in result["createdMeta"]
    )


def test_a_failed_submission_shows_no_success_and_no_share_state(tmp_path):
    fetch = {
        HOMEPAGE_URL: {"status": 200, "body": {"total": 0, "items": []}},
        SUBMIT_URL: {"status": 400, "body": {"detail": "Title is required"}},
    }
    result = run(
        tmp_path,
        "index.html",
        list(FILL_PROJECT) + [WAIT_FOR_RENDER],
        fetch=fetch,
    )

    assert len(posts(result)) == 1
    # The failure reports honestly and the share UI never appears.
    assert "Error" in (result["ids"].get("message") or "")
    assert "Your project is live!" not in " ".join(result["created"])
    assert not any(
        m.get("className") == "success-share" for m in result["createdMeta"]
    )
    assert len(events(result, "share_ui_shown")) == 0


# ---------------------------------------------------------------------------
# Phases 3-4: platform URLs and the editable suggested post
# ---------------------------------------------------------------------------


def test_the_suggested_post_carries_the_real_project(tmp_path):
    result = submitted_page(tmp_path)

    post = next(m for m in result["createdMeta"] if m.get("value"))
    # Exactly the agreed template: real title, real public URL, no claims
    # about feedback received.
    assert post["value"] == DEFAULT_POST
    assert "Akiya Scout" in post["value"]
    assert PUBLIC_URL in post["value"]
    assert "responses" not in post["value"]


def test_platform_share_urls_are_encoded_and_point_at_fixed_domains(tmp_path):
    result = submitted_page(tmp_path)

    x = next(a for a in anchors(result) if a.get("text") == "X")
    reddit = next(a for a in anchors(result) if a.get("text") == "Reddit")

    # X: compose URL carrying the post, round-tripping through encoding.
    assert x["href"].startswith("https://twitter.com/intent/tweet?text=")
    assert unquote(x["href"].split("text=", 1)[1]) == DEFAULT_POST

    # Reddit: submission URL + title, both encoded.
    assert reddit["href"].startswith("https://www.reddit.com/submit?url=")
    params = reddit["href"].split("?", 1)[1].split("&")
    assert unquote(params[0].split("=", 1)[1]) == PUBLIC_URL
    assert unquote(params[1].split("title=", 1)[1]) == "Akiya Scout"

    # Every external option opens a new tab with noopener; the internal
    # success link stays a plain same-tab link.
    for a in anchors(result):
        if (a.get("href") or "").startswith("https://"):
            assert a.get("target") == "_blank"
            assert "noopener" in (a.get("rel") or "")
            assert "noreferrer" in (a.get("rel") or "")


def test_clicking_x_opens_a_compose_window_with_the_current_text(tmp_path):
    result = submitted_page(
        tmp_path,
        extra_calls=[
            {
                "evaluate": (
                    "document.getElementById('message').postInput.value = "
                    "'Edited before sharing'; 'edited'"
                ),
                "as": "edited",
            },
            {"clickCreatedContaining": "X"},
        ],
    )

    # One window, to X's compose URL, with the edited text -- not the stale
    # default, and never reported as a completed share.
    assert len(result["opened"]) == 1
    opened = result["opened"][0]
    assert opened["url"].startswith("https://twitter.com/intent/tweet?text=")
    assert unquote(opened["url"].split("text=", 1)[1]) == "Edited before sharing"
    assert "noopener" in (opened["features"] or "")
    assert len(events(result, "share_option_clicked")) == 1


def test_the_panel_offers_exactly_four_actions(tmp_path):
    result = submitted_page(tmp_path)

    # Exactly X, Reddit, Copy link, Copy post -- in that order, nothing else.
    actions = [
        m for m in result["createdMeta"] if m.get("className") == "share-action"
    ]
    assert [a.get("text") for a in actions] == [
        "X",
        "Reddit",
        "Copy link",
        "Copy post",
    ]

    # The retired options are gone from the rendered DOM, not merely hidden.
    assert "LinkedIn" not in " ".join(result["created"])
    assert "Copy for Threads" not in " ".join(result["created"])
    for m in result["createdMeta"]:
        href = (m.get("href") or "").lower()
        assert "linkedin" not in href
        assert "threads" not in href
    # And no leftover button waits for a click that can never come.
    assert result["clipboard"] == []
    assert result["opened"] == []


def test_share_actions_carry_real_platform_icons_and_accessible_names(tmp_path):
    result = submitted_page(tmp_path)

    # Four icon slots, each holding static inline SVG marked decorative.
    icons = [m for m in result["createdMeta"] if m.get("className") == "share-icon"]
    assert len(icons) == 4
    for icon in icons:
        assert "<svg" in (icon.get("html") or "")
        assert 'aria-hidden="true"' in (icon.get("html") or "")

    # X and Reddit announce themselves to assistive tech and on hover.
    x = next(a for a in anchors(result) if a.get("text") == "X")
    reddit = next(a for a in anchors(result) if a.get("text") == "Reddit")
    assert x.get("ariaLabel") == "Share this project on X"
    assert x.get("title") == "Share on X"
    assert reddit.get("ariaLabel") == "Share this project on Reddit"
    assert reddit.get("title") == "Share on Reddit"

    # The copy buttons explain themselves in a tooltip too.
    copy_link = next(
        m for m in result["createdMeta"] if m.get("text") == "Copy link"
    )
    copy_post = next(
        m for m in result["createdMeta"] if m.get("text") == "Copy post"
    )
    assert copy_link.get("tag").lower() == "button"
    assert copy_link.get("title") == "Copy the project link"
    assert copy_post.get("tag").lower() == "button"
    assert copy_post.get("title") == "Copy the suggested post"


# ---------------------------------------------------------------------------
# Phases 5-6: copy actions, skip, and optionality
# ---------------------------------------------------------------------------


def test_copy_project_link_copies_the_public_url(tmp_path):
    result = submitted_page(
        tmp_path,
        extra_calls=[{"clickCreatedContaining": "Copy link"}],
    )

    assert result["clipboard"] == [PUBLIC_URL]
    assert len(events(result, "share_copy_link")) == 1
    # A small, temporary confirmation.
    assert any(t == "Link copied" for t in texts(result))


def test_copy_suggested_post_copies_the_current_edited_text(tmp_path):
    result = submitted_page(
        tmp_path,
        extra_calls=[
            {
                "evaluate": (
                    "document.getElementById('message').postInput.value = "
                    "'My edited post text'; 'edited'"
                ),
                "as": "edited",
            },
            {"clickCreatedContaining": "Copy post"},
        ],
    )

    # Only the current text is copied; the template is not appended and the
    # edit is not overwritten.
    assert result["clipboard"] == ["My edited post text"]
    assert len(events(result, "share_copy_post")) == 1
    # A small, temporary confirmation.
    assert any(t == "Post copied" for t in texts(result))


def test_sharing_is_entirely_optional(tmp_path):
    # A submission that never touches the share section succeeds completely.
    result = submitted_page(tmp_path)

    assert len(events(result, "project_submit")) == 1
    assert "Your project is live!" in texts(result)
    # The only share event is the section being shown; nothing was copied,
    # nothing was opened.
    assert len(events(result, "share_ui_shown")) == 1
    assert len(events(result, "share_copy_link")) == 0
    assert len(events(result, "share_copy_post")) == 0
    assert len(events(result, "share_option_clicked")) == 0
    assert result["clipboard"] == []
    assert result["opened"] == []


def test_skip_for_now_collapses_the_share_section_and_keeps_the_success(tmp_path):
    result = submitted_page(
        tmp_path,
        extra_calls=[{"clickCreatedContaining": "Skip for now"}],
    )

    # The optional section hides; the success state and its link remain.
    assert result["flags"]["share-section"]["display"] == "none"
    assert "Your project is live!" in texts(result)
    assert any(m.get("href") == PUBLIC_URL for m in result["createdMeta"])
    assert result["flags"]["share-section"]["ariaLabel"] == (
        "Share your project (optional)"
    )


# ---------------------------------------------------------------------------
# Phase 5: the My Projects card row
# ---------------------------------------------------------------------------

MY_PROJECTS_LIST = [
    {
        "id": 1,
        "title": "Sentry bot",
        "description": "Watches your logs",
        "url": None,
        "image_url": None,
        "owner_id": 7,
        "created_at": "2026-09-01T10:00:00",
        "question_text": "Is the alerting clear enough?",
        "response_count": 2,
    },
    {
        "id": 2,
        "title": "Log Lens",
        "description": "Reads your stack traces",
        "url": None,
        "image_url": None,
        "owner_id": 7,
        "created_at": "2026-09-02T10:00:00",
        "question_text": "Would you use this daily?",
        "response_count": 0,
    },
]


def test_card_share_rows_carry_the_project_they_belong_to(tmp_path):
    result = run(
        tmp_path,
        "my_projects.html",
        [
            {"fn": "loadProjects", "args": []},
            WAIT_FOR_RENDER,
            {
                "evaluate": (
                    "CritiqueShare.renderCardShareRow("
                    "document.getElementById('content'), "
                    "{projectId: 1, title: 'Sentry bot'}); 'row1'"
                ),
                "as": "row1",
            },
            {
                "evaluate": (
                    "CritiqueShare.renderCardShareRow("
                    "document.getElementById('content'), "
                    "{projectId: 2, title: 'Log Lens'}); 'row2'"
                ),
                "as": "row2",
            },
        ],
        fetch={MY_PROJECTS_URL: {"status": 200, "body": MY_PROJECTS_LIST}},
    )

    # Each row links to its own project, in creation order: never the wrong
    # URL even with several projects on the page.
    reddit = [m for m in result["createdMeta"] if m.get("text") == "Reddit"]
    assert len(reddit) == 2
    assert TEST_ORIGIN + "/project/1" == unquote(
        reddit[0]["href"].split("?", 1)[1].split("&", 1)[0].split("=", 1)[1]
    )
    assert TEST_ORIGIN + "/project/2" == unquote(
        reddit[1]["href"].split("?", 1)[1].split("&", 1)[0].split("=", 1)[1]
    )

    # The suggested post implied by each row's links names that row's own
    # project (X's compose text ends with that row's URL).
    x_links = [a for a in result["createdMeta"] if a.get("text") == "X"]
    assert len(x_links) == 2
    assert unquote(x_links[0]["href"].split("text=", 1)[1]).endswith(
        TEST_ORIGIN + "/project/1"
    )
    assert unquote(x_links[1]["href"].split("text=", 1)[1]).endswith(
        TEST_ORIGIN + "/project/2"
    )

    # Opening a row is tracked per project.
    ui_events = events(result, "share_ui_shown")
    assert len(ui_events) == 2
    assert any("project_id=1" in e["url"] for e in ui_events)
    assert any("project_id=2" in e["url"] for e in ui_events)


def test_card_copy_link_uses_the_first_rows_project(tmp_path):
    result = run(
        tmp_path,
        "my_projects.html",
        [
            {"fn": "loadProjects", "args": []},
            WAIT_FOR_RENDER,
            {
                "evaluate": (
                    "CritiqueShare.renderCardShareRow("
                    "document.getElementById('content'), "
                    "{projectId: 1, title: 'Sentry bot'}); 'row1'"
                ),
                "as": "row1",
            },
            {"clickCreatedContaining": "Copy link"},
        ],
        fetch={MY_PROJECTS_URL: {"status": 200, "body": [MY_PROJECTS_LIST[0]]}},
    )

    assert result["clipboard"] == [TEST_ORIGIN + "/project/1"]
    assert len(events(result, "share_copy_link")) == 1


def test_card_share_row_offers_the_same_four_actions(tmp_path):
    result = run(
        tmp_path,
        "my_projects.html",
        [
            {"fn": "loadProjects", "args": []},
            WAIT_FOR_RENDER,
            {
                "evaluate": (
                    "CritiqueShare.renderCardShareRow("
                    "document.getElementById('content'), "
                    "{projectId: 1, title: 'Sentry bot'}); 'row'"
                ),
                "as": "row",
            },
        ],
        fetch={MY_PROJECTS_URL: {"status": 200, "body": [MY_PROJECTS_LIST[0]]}},
    )

    # The same compact set on the card, in the same order.
    actions = [
        m for m in result["createdMeta"] if m.get("className") == "share-action"
    ]
    assert [a.get("text") for a in actions] == [
        "X",
        "Reddit",
        "Copy link",
        "Copy post",
    ]
    # In the card's balanced 2x2 wrapper, with icons.
    assert any(
        m.get("className") == "share-grid card-share" for m in result["createdMeta"]
    )
    icons = [m for m in result["createdMeta"] if m.get("className") == "share-icon"]
    assert len(icons) == 4

    # And the retired options stay retired here too.
    seen = " ".join(result["created"])
    assert "LinkedIn" not in seen
    assert "Threads" not in seen


def test_view_feedback_and_delete_survive_next_to_share(tmp_path):
    result = run(
        tmp_path,
        "my_projects.html",
        [{"fn": "loadProjects", "args": []}, WAIT_FOR_RENDER],
        fetch={MY_PROJECTS_URL: {"status": 200, "body": [MY_PROJECTS_LIST[0]]}},
    )

    content = result["ids"]["content"]
    # The old actions are untouched...
    assert '<a href="/project/1/results" class="btn btn-primary">View Feedback</a>' in content
    assert "deleteProject(1, this)" in content
    # ...and Share is wired to that card's own data, collapsed by default.
    assert 'onclick="toggleShare(this)"' in content
    assert 'data-project="1"' in content
    assert 'data-title="Sentry bot"' in content
    assert 'aria-expanded="false"' in content


# ---------------------------------------------------------------------------
# Phase 8: security of the new markup
# ---------------------------------------------------------------------------


def test_malicious_project_data_cannot_reach_the_share_markup(tmp_path):
    evil = {
        "project": dict(
            CREATED_PROJECT["project"],
            title='"><img src=x onerror=alert(1)>',
            description="<script>alert(2)</script>",
        ),
        "question": dict(CREATED_PROJECT["question"], text="<svg onload=alert(3)>"),
    }
    result = submitted_page(
        tmp_path,
        fetch_overrides={SUBMIT_URL: {"status": 201, "body": evil}},
    )

    rendered = "\n".join(result["created"])
    # The payload survives as escaped text, never as live markup. (The only
    # raw markup allowed through is the icon constants' own <svg xmlns=…> --
    # an executable payload would look like <svg onload=…>, never that.)
    assert "<img src=x" not in rendered
    assert "<script" not in rendered
    assert "<svg onload" not in rendered
    assert "&lt;img" in rendered
    assert "&lt;script" in rendered
    assert "&lt;svg" in rendered

    # Share URLs keep it percent-encoded: no raw quote or angle bracket can
    # reach an href, so the payload can never close an attribute or open a
    # tag. (The word "onerror" may survive as encoded *text* -- a word in a
    # URL parameter is inert; what matters is that `=`, `<` and `"` are not.)
    for m in result["createdMeta"]:
        href = m.get("href") or ""
        if href.startswith("https://"):
            assert "<" not in href and ">" not in href
            assert '"' not in href


def test_share_links_cannot_become_unsafe_redirects(tmp_path):
    source = (STATIC_DIR / "share.js").read_text(encoding="utf-8")

    # Fixed, verified hosts; the public link is built only from the origin
    # that served the page.
    for host in [
        "https://twitter.com/intent/tweet",
        "https://www.reddit.com/submit",
    ]:
        assert host in source
    assert "window.location.origin + '/project/'" in source
    # External opens always carry noopener; no tracking parameters ride
    # along on shared URLs.
    assert "'noopener,noreferrer'" in source
    assert "noopener noreferrer" in source
    assert "utm_" not in source
    # The retired options are absent from the implementation itself, so no
    # endpoint for them can creep back in through this module.
    lowered = source.lower()
    assert "linkedin" not in lowered
    assert "threads" not in lowered
    # Nothing publishes automatically: every action sits in a click handler.
    assert "setInterval" not in source
    assert "autoplay" not in source
    # Icons are static constants: exactly one innerHTML write in the whole
    # module, sourced from the icon map -- never from any user content.
    assert len(re.findall(r"\.innerHTML\s*=", source)) == 1
    assert "icon.innerHTML = ICONS[name]" in source


# ---------------------------------------------------------------------------
# Phase 6/17: the layout rules that keep this usable at 412px
# ---------------------------------------------------------------------------


def test_the_share_ui_stacks_on_a_phone_and_keeps_focus_visible():
    css = (STATIC_DIR / "shared.css").read_text(encoding="utf-8")
    mobile = " ".join(mobile_blocks(css))

    # Desktop: one compact row of four equal actions.
    assert ".share-grid" in css
    assert "grid-template-columns: repeat(4, minmax(0, 1fr))" in css
    # The card keeps a balanced 2x2 inside its half-width column.
    assert re.search(
        r"\.card-share\s*\{\s*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)",
        css,
    )
    # Phone: two equal columns -- two buttons per line, and minmax(0, ...)
    # guarantees nothing can overflow horizontally at 412px or narrower.
    assert ".share-grid" in mobile
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in mobile
    # The quiet way onward still stacks full-width below the actions.
    assert ".share-actions" in mobile
    assert "flex-direction: column" in mobile
    assert ".success-share" in mobile

    # Icons render left of their labels, and never take extra space in a
    # shrinking track.
    assert ".share-icon" in css
    assert "order: -1" in css
    assert "flex: none" in css

    # Keyboard users get a visible focus ring on every share control.
    assert ".share-action:focus-visible" in css
    assert "outline: 2px solid var(--focus)" in css
