"""Auth-choice UX: every login-required action offers both auth methods.

Critique has two existing sign-in methods (GitHub OAuth and an email magic
link). Wherever the UI stops an unauthenticated user, both must be offered with
the same wording, the same resume/return behaviour and the same analytics
events -- without duplicating those events.

These tests run each page's *real* JavaScript, including the shared
``static/ui.js`` auth-choice helper, inside the Node rendering harness, and
assert on the markup, reflected links, network calls and stored drafts the page
actually produces.

Requires ``node`` on PATH; the whole module is skipped when it is missing.
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

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node is required to run the frontend rendering harness",
)

GITHUB = "Continue with GitHub"
EMAIL = "Continue with email"
NO_PASSWORD = "No password required."

EMAIL_START = {"/auth/email/start": {"status": 200, "body": {"ok": True}}}


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


def events(result, name):
    """Every request that tracked `name`."""
    marker = "event_name=" + name
    return [r for r in result["requests"] if marker in r["url"]]


def login_hrefs(result):
    """Every /auth/login link the page built during the scenario."""
    return [
        str(meta["href"])
        for meta in result["createdMeta"]
        if meta.get("href") and str(meta["href"]).startswith("/auth/login")
    ]


def email_posts(result):
    return [
        r for r in result["requests"]
        if "/auth/email/start" in r["url"] and r["method"] == "POST"
    ]


def assert_offers_both_methods(html, **extra):
    """The canonical auth-choice rule from the task, checked per gate."""
    assert html.count(GITHUB) == 1, f"expected one GitHub option:\n{html}"
    assert html.count(EMAIL) == 1, f"expected one email option:\n{html}"
    assert NO_PASSWORD in html, f"missing supporting text:\n{html}"
    for needle in extra.values():
        assert needle in html, f"missing {needle!r}:\n{html}"


EMAIL_OPS = [
    {"clickCreatedContaining": EMAIL},
    {"setValuePlaceholder": {"placeholder": "you@example.com", "value": "builder@example.com"}},
    {"submitCreatedContaining": "Send login link"},
]


# ---------------------------------------------------------------------------
# Feedback login gate (project detail)
# ---------------------------------------------------------------------------


def test_feedback_gate_offers_github_and_email(tmp_path):
    result = run(
        tmp_path,
        "project_detail.html",
        [{"fn": "showInlineLoginPrompt", "args": []}],
        location="/project/1",
    )
    assert_offers_both_methods(
        result["html"],
        title="Almost there",
        message="Your feedback is ready to send.",
        note="Your answer will be shared with the builder.",
    )


def test_feedback_gate_return_to_resumes_the_feedback_flow(tmp_path):
    result = run(
        tmp_path,
        "project_detail.html",
        [{"fn": "showInlineLoginPrompt", "args": []}],
        location="/project/1",
    )
    assert login_hrefs(result) == [
        "/auth/login?return_to=%2Fproject%2F1%3Fresume%3Dfeedback"
    ]


def test_feedback_gate_prompt_event_is_fired_only_once(tmp_path):
    result = run(
        tmp_path,
        "project_detail.html",
        [
            {"fn": "showInlineLoginPrompt", "args": []},
            {"fn": "showInlineLoginPrompt", "args": []},
        ],
        location="/project/1",
    )
    assert len(events(result, "login_prompt_shown")) == 1
    # Re-rendering must still show exactly one complete choice rather than an
    # empty box: the submit handler clears #message before redrawing the gate.
    assert_offers_both_methods(result["html"])


def test_feedback_gate_github_choice_tracks_and_keeps_the_draft(tmp_path):
    result = run(
        tmp_path,
        "project_detail.html",
        [
            {"fn": "showInlineLoginPrompt", "args": []},
            {"clickCreatedContaining": GITHUB},
        ],
        location="/project/1",
    )
    assert len(events(result, "auth_method_selected_github")) == 1
    assert len(events(result, "login_started")) == 1
    assert events(result, "auth_method_selected_email") == []
    assert "critique_feedback_1" in result["storage"]["session"]


def test_feedback_gate_email_choice_opens_the_email_form(tmp_path):
    result = run(
        tmp_path,
        "project_detail.html",
        [
            {"fn": "showInlineLoginPrompt", "args": []},
            {"clickCreatedContaining": EMAIL},
        ],
        location="/project/1",
    )
    assert len(events(result, "auth_method_selected_email")) == 1
    assert events(result, "auth_method_selected_github") == []
    assert events(result, "login_started") == []
    assert "Send login link" in result["html"]
    assert "Back" in result["html"]
    assert "critique_feedback_1" in result["storage"]["session"]
    assert "critique_feedback_1_email_fallback" in result["storage"]["local"]


def test_feedback_gate_email_link_resumes_the_feedback_flow(tmp_path):
    result = run(
        tmp_path,
        "project_detail.html",
        [
            {"fn": "showInlineLoginPrompt", "args": []},
            *EMAIL_OPS,
        ],
        fetch=EMAIL_START,
        location="/project/1",
    )
    sent = email_posts(result)
    assert len(sent) == 1, result["requests"]
    body = json.loads(sent[0]["body"])
    assert body["email"] == "builder@example.com"
    assert body["return_to"] == "/project/1?resume=feedback"
    assert len(events(result, "email_verification_sent")) == 1
    assert "Check your email" in result["html"]


def test_email_send_failure_keeps_the_form_and_says_so(tmp_path):
    """A rejected magic-link request (429/5xx) must not fail silently.

    The endpoint is rate limited, so this is a path users really hit: the form
    has to stay usable with a readable error instead of looking like nothing
    happened or pretending the mail went out.
    """
    result = run(
        tmp_path,
        "project_detail.html",
        [
            {"fn": "showInlineLoginPrompt", "args": []},
            *EMAIL_OPS,
        ],
        fetch={"/auth/email/start": {"status": 429, "body": {}}},
        location="/project/1",
    )
    assert result["errors"] == [], f"page script errors: {result['errors']}"
    assert len(email_posts(result)) == 1, result["requests"]
    # The failure is reported, and no success is claimed.
    assert "Couldn't send the link. Please try again." in result["html"]
    assert "Check your email" not in result["html"]
    assert len(events(result, "email_verification_sent")) == 0
    # The form is still there and re-enabled so the user can retry.
    assert "Send login link" in result["html"]
    assert any(
        m.get("placeholder") == "you@example.com" for m in result["createdMeta"]
    ), result["createdMeta"]


# ---------------------------------------------------------------------------
# Project submission login gate (homepage)
# ---------------------------------------------------------------------------


def test_project_submit_gate_offers_github_and_email(tmp_path):
    result = run(
        tmp_path,
        "index.html",
        [{"fn": "showProjectInlineLoginPrompt", "args": []}],
    )
    assert_offers_both_methods(
        result["html"],
        title="Almost there",
        message="Your project is ready to submit.",
        note="Your draft is saved.",
    )
    assert login_hrefs(result) == [
        "/auth/login?return_to=%2F%3Fresume%3Dproject_submit"
    ]


def test_project_submit_gate_prompt_event_is_fired_only_once(tmp_path):
    result = run(
        tmp_path,
        "index.html",
        [
            {"fn": "showProjectInlineLoginPrompt", "args": []},
            {"fn": "showProjectInlineLoginPrompt", "args": []},
        ],
    )
    assert len(events(result, "login_prompt_shown")) == 1


def test_project_submit_gate_saves_the_draft_when_a_method_is_chosen(tmp_path):
    before = run(
        tmp_path, "index.html", [{"fn": "showProjectInlineLoginPrompt", "args": []}]
    )
    assert "critique_project_draft" not in before["storage"]["session"]

    after = run(
        tmp_path,
        "index.html",
        [
            {"fn": "showProjectInlineLoginPrompt", "args": []},
            {"clickCreatedContaining": GITHUB},
        ],
    )
    assert "critique_project_draft" in after["storage"]["session"]
    assert len(events(after, "auth_method_selected_github")) == 1
    assert len(events(after, "login_started")) == 1


def test_project_submit_gate_email_choice_opens_the_email_form(tmp_path):
    result = run(
        tmp_path,
        "index.html",
        [
            {"fn": "showProjectInlineLoginPrompt", "args": []},
            {"clickCreatedContaining": EMAIL},
        ],
    )
    assert len(events(result, "auth_method_selected_email")) == 1
    assert events(result, "auth_method_selected_github") == []
    assert "Send login link" in result["html"]
    assert "critique_project_draft" in result["storage"]["session"]


def test_project_submit_email_link_resumes_the_submit(tmp_path):
    result = run(
        tmp_path,
        "index.html",
        [
            {"fn": "showProjectInlineLoginPrompt", "args": []},
            *EMAIL_OPS,
        ],
        fetch=EMAIL_START,
    )
    sent = email_posts(result)
    assert len(sent) == 1, result["requests"]
    assert json.loads(sent[0]["body"])["return_to"] == "/?resume=project_submit"
    assert len(events(result, "email_verification_sent")) == 1


# ---------------------------------------------------------------------------
# My Projects login gate
# ---------------------------------------------------------------------------


def test_my_projects_gate_offers_github_and_email(tmp_path):
    result = run(
        tmp_path,
        "my_projects.html",
        [{"fn": "loadProjects", "args": []}],
        fetch={"/api/projects/my/list": {"status": 401, "body": {}}},
    )
    assert_offers_both_methods(
        result["html"],
        title="Sign in required",
        message="Sign in to see and manage your projects.",
    )
    assert login_hrefs(result) == ["/auth/login?return_to=%2Fmy-projects"]


def test_my_projects_email_link_returns_to_my_projects(tmp_path):
    result = run(
        tmp_path,
        "my_projects.html",
        [
            {"fn": "loadProjects", "args": []},
            *EMAIL_OPS,
        ],
        fetch={
            "/api/projects/my/list": {"status": 401, "body": {}},
            **EMAIL_START,
        },
    )
    sent = email_posts(result)
    assert len(sent) == 1, result["requests"]
    assert json.loads(sent[0]["body"])["return_to"] == "/my-projects"


# ---------------------------------------------------------------------------
# Navbar login (auth choice instead of a forced GitHub redirect)
# ---------------------------------------------------------------------------


def test_navbar_login_menu_offers_github_and_email(tmp_path):
    result = run(tmp_path, "index.html", [{"clickId": "login-btn"}])
    assert_offers_both_methods(result["html"])
    assert login_hrefs(result) == ["/auth/login?return_to=%2F"]
    assert len(events(result, "login_prompt_shown")) == 1
    # The button opens a choice of both methods, so its accessible name must
    # follow the visible "Login" text rather than claim GitHub alone.
    assert result["flags"]["login-btn"]["ariaLabel"] == "Login"


def test_navbar_login_menu_is_offered_on_every_page(tmp_path):
    for page in (
        "index.html",
        "discover.html",
        "my_projects.html",
        "project_detail.html",
        "project_results.html",
    ):
        result = run(tmp_path, page, [{"clickId": "login-btn"}])
        assert_offers_both_methods(result["html"])
        assert result["flags"]["login-btn"]["ariaLabel"] == "Login"


def test_nav_menu_stays_open_when_an_option_is_chosen(tmp_path):
    """Regression: picking an option must not close the menu it lives in.

    Choosing "Continue with email" re-renders the panel, which detaches the
    clicked node before the document's outside-click listener runs. Testing
    containment against that post-render tree closed the menu immediately, so
    the email form flashed and vanished.
    """
    result = run(
        tmp_path,
        "index.html",
        [{"clickId": "login-btn"}, {"clickCreatedContaining": EMAIL}],
    )
    assert result["flags"]["nav-login-menu"]["hidden"] is False
    assert result["flags"]["login-btn"]["ariaExpanded"] == "true"
    assert "Send login link" in result["html"]
    assert len(events(result, "auth_method_selected_email")) == 1


def test_nav_menu_closes_when_the_click_is_outside(tmp_path):
    result = run(
        tmp_path,
        "index.html",
        [{"clickId": "login-btn"}, {"dispatchDocumentClickId": "navbar-nav"}],
    )
    assert result["flags"]["nav-login-menu"]["hidden"] is True
    assert result["flags"]["login-btn"]["ariaExpanded"] == "false"


# ---------------------------------------------------------------------------
# Builder avatars on the homepage
# ---------------------------------------------------------------------------


def social_proof(tmp_path, builders, total_builders=6, read=None):
    return run(
        tmp_path,
        "index.html",
        [{"fn": "loadSocialProof", "args": []}],
        fetch={
            "/api/stats": {
                "status": 200,
                "body": {
                    "total_builders": total_builders,
                    "total_projects": 3,
                    "builders": builders,
                },
            }
        },
        read=read or {"byId": "avatar-stack"},
    )


def test_github_avatars_are_rendered_as_images(tmp_path):
    result = social_proof(
        tmp_path,
        [{"username": "alice", "avatar_url": "https://avatars.githubusercontent.com/u/1?v=4"}],
    )
    html = result["html"]
    assert "<img" in html
    assert 'src="https://avatars.githubusercontent.com/u/1?v=4"' in html


def test_builder_without_an_avatar_gets_a_local_deterministic_fallback(tmp_path):
    builders = [{"username": "email_0123456789abcdef", "avatar_url": None}]
    first = social_proof(tmp_path, builders)
    second = social_proof(tmp_path, builders)

    html = first["html"]
    assert "<img" not in html, "missing avatar must not fall back to an image"
    assert 'class="avatar-fallback"' in html
    assert "<svg" in html
    # Deterministic: identical on every page load.
    assert second["html"] == html
    # Different builders must not share an identical avatar.
    other = social_proof(
        tmp_path, [{"username": "email_fedcba9876543210", "avatar_url": None}]
    )
    assert other["html"] != html


def test_fallback_avatar_never_leaks_the_email_address(tmp_path):
    result = social_proof(
        tmp_path,
        [{"username": "email_0123456789abcdef", "avatar_url": None}],
    )
    html = result["html"]
    assert "@" not in html, f"an email-shaped string reached the markup: {html}"
    assert "email_0123456789abcdef" not in html


def test_unsafe_avatar_urls_are_not_loaded(tmp_path):
    result = social_proof(
        tmp_path,
        [
            {"username": "alice", "avatar_url": "javascript:alert(1)"},
            {"username": "bob", "avatar_url": "http://evil.example/a.png"},
            {"username": "carol", "avatar_url": "https://avatars.githubusercontent.com/u/3?v=4"},
        ],
    )
    html = result["html"]
    assert html.count("<img") == 1
    assert 'src="https://avatars.githubusercontent.com/u/3?v=4"' in html
    assert html.count('class="avatar-fallback"') == 2


def test_social_proof_shows_the_real_builder_count(tmp_path):
    result = social_proof(tmp_path, [], total_builders=6)
    assert result["ids"]["social-proof-text"] == (
        "Join 6 builders already using Critique"
    )

    single = social_proof(tmp_path, [], total_builders=1)
    assert single["ids"]["social-proof-text"] == "Join 1 builder already using Critique"


def test_homepage_never_hardcodes_a_builder_count():
    """No fake or invented social proof may be baked into the page."""
    source = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    assert not re.search(r"Join\s+\d+\s+builders", source)
    assert "total_builders" in source  # the count still comes from /api/stats
    assert re.search(r"total_builders\s*>\s*0", source)  # nothing is claimed at 0
