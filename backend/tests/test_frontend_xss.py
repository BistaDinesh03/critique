"""Regression tests for the stored XSS (P1) in user-controlled HTML rendering.

These tests exercise the *actual* rendering boundary: they execute the real
inline JavaScript of each frontend page (via a Node harness) and parse the
exact HTML string the page assigns to innerHTML. They do not test the escaping
helper in isolation.

Requires `node` on PATH; the whole module is skipped when it is missing.
"""

import json
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

from app.main import app

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent
FRONTEND_DIR = REPO_DIR / "frontend"
HARNESS = Path(__file__).resolve().parent / "frontend_render_harness.js"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node is required to run the frontend rendering harness",
)

# Verified payloads (the first one is the exact payload that produced a live
# onerror attribute before the fix).
PAYLOAD_IMAGE = 'https://evil.com/x.png" onerror="alert(1)" data-x="'
PAYLOAD_TITLE = 't" onmouseover="alert(2)'
PAYLOAD_URL = 'https://evil.com/a?b=1" onfocus="alert(4)'
PAYLOAD_SUGGESTION = 'nice work" onmouseover="alert(9)'

LEGIT = {
    "id": 1,
    "title": "My SaaS App",
    "description": "Build & ship <fast> things",
    "url": "https://example.com/path?a=1&b=2",
    "image_url": "https://example.com/img.png",
    "question_text": "Does this solve a real problem?",
    "response_count": 3,
}


def render(tmp_path, page, calls, read, fetch=None, location="/"):
    """Run the page's real JS in Node and return the HTML it produced."""
    scenario = {
        "page": (FRONTEND_DIR / page).as_posix(),
        "calls": calls,
        "read": read,
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
    assert result["html"].strip(), "page rendered no HTML"
    return result["html"]


class ParsedHTML(HTMLParser):
    """Collects every start tag with its attributes plus the visible text."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []  # list of (tag_name, [(attr_name, attr_value), ...])
        self.text = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, attrs))

    def handle_startendtag(self, tag, attrs):
        self.tags.append((tag, attrs))

    def handle_data(self, data):
        if data.strip():
            self.text.append(data)


def parse(html):
    parsed = ParsedHTML()
    parsed.feed(html)
    parsed.close()
    return parsed


def attr_names(attrs):
    return [name for name, _ in attrs]


def get_attr(parsed, tag, attr):
    """Return the single value of `attr` on the first `<tag>`."""
    for name, attrs in parsed.tags:
        if name == tag:
            values = [value for key, value in attrs if key == attr]
            assert len(values) == 1, f"expected exactly one {attr} on <{tag}>: {attrs}"
            return values[0]
    raise AssertionError(f"no <{tag}> in rendered HTML")


def find_attr(parsed, tag, attr):
    """Return `attr` from the first `<tag>` that actually carries it."""
    for name, attrs in parsed.tags:
        if name == tag:
            for key, value in attrs:
                if key == attr:
                    return value
    raise AssertionError(f"no <{tag} {attr}=...> in rendered HTML")


def assert_markup_is_safe(parsed, allowed_handlers):
    """Shared assertions for every rendered payload test."""
    seen_handlers = []
    for tag, attrs in parsed.tags:
        names = attr_names(attrs)
        # A duplicated attribute means the parser saw an injected second one.
        assert len(names) == len(set(names)), f"duplicate attribute on <{tag}>: {attrs}"
        for name, value in attrs:
            if name.startswith("on"):
                seen_handlers.append((tag, name, value))
    assert not [h for h in seen_handlers if h[2] not in allowed_handlers], (
        "attacker-controlled event handler rendered: "
        f"{[h for h in seen_handlers if h[2] not in allowed_handlers]}"
    )
    assert not [t for t, _ in parsed.tags if t in ("script", "iframe", "object")], (
        "injected element rendered"
    )


# ---------------------------------------------------------------------------
# 1. Malicious image URL must not create an executable onerror attribute.
# ---------------------------------------------------------------------------


def test_image_url_cannot_create_onerror_attribute(tmp_path):
    project = dict(LEGIT, image_url=PAYLOAD_IMAGE)
    html = render(
        tmp_path,
        "discover.html",
        [{"fn": "showProjects", "args": [[project]]}],
        {"created": True},
    )
    parsed = parse(html)
    assert_markup_is_safe(parsed, allowed_handlers={"this.style.display='none'"})

    img_attrs = next(attrs for tag, attrs in parsed.tags if tag == "img")
    assert sorted(attr_names(img_attrs)) == [
        "alt",
        "class",
        "loading",
        "onerror",
        "src",
    ]
    # The payload round-trips as data instead of breaking out of the attribute.
    assert get_attr(parsed, "img", "src") == PAYLOAD_IMAGE
    assert get_attr(parsed, "img", "alt") == "Screenshot of " + LEGIT["title"]
    # The only onerror left is the page's own hardcoded fallback handler.
    assert get_attr(parsed, "img", "onerror") == "this.style.display='none'"


def test_image_url_cannot_create_onerror_attribute_homepage(tmp_path):
    html = render(
        tmp_path,
        "index.html",
        [{"fn": "loadHomepageProjects", "args": []}],
        {"byId": "homepage-projects"},
        fetch={"/api/projects/": {"status": 200, "body": {"total": 1, "items": [dict(LEGIT, image_url=PAYLOAD_IMAGE)]}}},
    )
    parsed = parse(html)
    assert_markup_is_safe(parsed, allowed_handlers=set())
    assert get_attr(parsed, "img", "src") == PAYLOAD_IMAGE


def test_image_url_cannot_create_onerror_attribute_my_projects(tmp_path):
    html = render(
        tmp_path,
        "my_projects.html",
        [{"fn": "loadProjects", "args": []}],
        {"byId": "content"},
        fetch={
            "/api/projects/my/list": {
                "status": 200,
                "body": [dict(LEGIT, image_url=PAYLOAD_IMAGE)],
            }
        },
    )
    parsed = parse(html)
    assert_markup_is_safe(parsed, allowed_handlers={"toggleShare(this)", "deleteProject(1, this)"})
    assert get_attr(parsed, "img", "src") == PAYLOAD_IMAGE


def test_image_url_cannot_create_onerror_attribute_project_detail(tmp_path):
    data = {
        "project": dict(LEGIT, image_url=PAYLOAD_IMAGE, url=PAYLOAD_URL),
        "question": {"id": 1, "text": LEGIT["question_text"], "is_active": True, "project_id": 1},
    }
    html = render(
        tmp_path,
        "project_detail.html",
        [{"fn": "renderProject", "args": [data, []]}],
        {"byId": "content"},
        location="/project/1",
    )
    parsed = parse(html)
    assert_markup_is_safe(
        parsed,
        allowed_handlers={"trackFeedbackStart()", "this.style.display='none'"},
    )
    assert get_attr(parsed, "img", "src") == PAYLOAD_IMAGE
    assert get_attr(parsed, "a", "href") == PAYLOAD_URL


# ---------------------------------------------------------------------------
# 2. Malicious title must not create an executable event-handler attribute.
# ---------------------------------------------------------------------------


def test_title_cannot_create_onmouseover_attribute(tmp_path):
    project = dict(LEGIT, title=PAYLOAD_TITLE, image_url=LEGIT["image_url"])
    html = render(
        tmp_path,
        "discover.html",
        [{"fn": "showProjects", "args": [[project]]}],
        {"created": True},
    )
    parsed = parse(html)
    assert_markup_is_safe(parsed, allowed_handlers={"this.style.display='none'"})

    # No onmouseover anywhere, and the title survives intact as data.
    assert "onmouseover" not in [n for _, attrs in parsed.tags for n in attr_names(attrs)]
    assert get_attr(parsed, "img", "alt") == "Screenshot of " + PAYLOAD_TITLE
    assert PAYLOAD_TITLE in parsed.text
    review_link = next(attrs for tag, attrs in parsed.tags if tag == "a")
    assert get_attr(parsed, "a", "aria-label") == "Give feedback on " + PAYLOAD_TITLE
    assert sorted(attr_names(review_link)) == ["aria-label", "class", "href"]


def test_title_cannot_create_onmouseover_attribute_my_projects(tmp_path):
    html = render(
        tmp_path,
        "my_projects.html",
        [{"fn": "loadProjects", "args": []}],
        {"byId": "content"},
        fetch={
            "/api/projects/my/list": {
                "status": 200,
                "body": [dict(LEGIT, title=PAYLOAD_TITLE)],
            }
        },
    )
    parsed = parse(html)
    assert_markup_is_safe(parsed, allowed_handlers={"toggleShare(this)", "deleteProject(1, this)"})
    assert find_attr(parsed, "button", "data-title") == PAYLOAD_TITLE
    assert PAYLOAD_TITLE in parsed.text


def test_title_cannot_create_onmouseover_attribute_project_detail(tmp_path):
    data = {
        "project": dict(LEGIT, title=PAYLOAD_TITLE),
        "question": {"id": 1, "text": LEGIT["question_text"], "is_active": True, "project_id": 1},
    }
    html = render(
        tmp_path,
        "project_detail.html",
        [{"fn": "renderProject", "args": [data, []]}],
        {"byId": "content"},
        location="/project/1",
    )
    parsed = parse(html)
    assert_markup_is_safe(
        parsed,
        allowed_handlers={"trackFeedbackStart()", "this.style.display='none'"},
    )
    assert PAYLOAD_TITLE in parsed.text


def test_title_and_suggestion_cannot_create_attributes_on_results(tmp_path):
    data = {
        "project_title": PAYLOAD_TITLE,
        "question_text": LEGIT["question_text"],
        "is_owner": True,
        "responses": [
            {
                "id": 1,
                "clarity": "very_clear",
                "would_use": "yes",
                "suggestion": PAYLOAD_SUGGESTION,
                "question_id": 1,
            }
        ],
        "stats": {
            "total": 1,
            "clarity": {"very_clear": 100, "mostly_clear": 0, "confusing": 0},
            "would_use": {"yes": 100, "maybe": 0, "no": 0},
        },
    }
    html = render(
        tmp_path,
        "project_results.html",
        [
            {"fn": "countResponses", "args": [data]},
            {"fn": "renderPage", "args": [data]},
        ],
        {"byId": "content"},
        location="/project/1/results",
    )
    parsed = parse(html)
    assert_markup_is_safe(parsed, allowed_handlers=set())
    assert PAYLOAD_TITLE in parsed.text
    assert PAYLOAD_SUGGESTION in parsed.text


# ---------------------------------------------------------------------------
# 3. Normal data must still render correctly.
# ---------------------------------------------------------------------------


def test_legit_project_data_still_renders(tmp_path):
    html = render(
        tmp_path,
        "discover.html",
        [{"fn": "showProjects", "args": [[LEGIT]]}],
        {"created": True},
    )
    parsed = parse(html)
    assert get_attr(parsed, "img", "src") == LEGIT["image_url"]
    assert get_attr(parsed, "img", "alt") == "Screenshot of " + LEGIT["title"]
    assert get_attr(parsed, "a", "href") == "/project/1"
    assert get_attr(parsed, "a", "aria-label") == "Give feedback on " + LEGIT["title"]
    text = " ".join(parsed.text)
    assert LEGIT["title"] in text
    assert LEGIT["description"] in text
    assert LEGIT["question_text"] in text
    assert "3 responses" in text
    assert_markup_is_safe(parsed, allowed_handlers={"this.style.display='none'"})


def test_legit_project_detail_still_renders(tmp_path):
    data = {
        "project": LEGIT,
        "question": {"id": 1, "text": LEGIT["question_text"], "is_active": True, "project_id": 1},
    }
    responses = [
        {"id": 1, "clarity": "mostly_clear", "would_use": "maybe", "suggestion": "Add pricing"}
    ]
    html = render(
        tmp_path,
        "project_detail.html",
        [{"fn": "renderProject", "args": [data, responses]}],
        {"byId": "content"},
        location="/project/1",
    )
    parsed = parse(html)
    assert get_attr(parsed, "img", "src") == LEGIT["image_url"]
    assert get_attr(parsed, "a", "href") == LEGIT["url"]
    text = " ".join(parsed.text)
    assert LEGIT["title"] in text
    assert LEGIT["description"] in text
    assert "Add pricing" in text
    assert_markup_is_safe(
        parsed,
        allowed_handlers={"trackFeedbackStart()", "this.style.display='none'"},
    )


# ---------------------------------------------------------------------------
# 4. End to end: payload accepted by the API, stored, then rendered.
# ---------------------------------------------------------------------------


def test_stored_payload_from_api_renders_safely(tmp_path, auth_client):
    payload = {
        "project_data": {
            "title": PAYLOAD_TITLE,
            "description": 'desc " with <quotes> & amps',
            "url": PAYLOAD_URL,
            "image_url": PAYLOAD_IMAGE,
        },
        "question_data": {"text": 'What do you "think" <about> it?'},
    }
    created = auth_client.post("/api/projects/", json=payload)
    assert created.status_code == 201, created.text
    project_id = created.json()["project"]["id"]

    # Discover hides the author's own projects, so ask for the feed anonymously.
    saved_overrides = dict(app.dependency_overrides)
    app.dependency_overrides.clear()
    try:
        listing = auth_client.get("/api/projects/?page=1&page_size=50")
    finally:
        app.dependency_overrides.update(saved_overrides)
    assert listing.status_code == 200
    items = [p for p in listing.json()["items"] if p["id"] == project_id]
    assert items, "created project missing from the public list"
    assert items[0]["image_url"] == PAYLOAD_IMAGE  # stored unmodified, as designed

    html = render(
        tmp_path,
        "discover.html",
        [{"fn": "showProjects", "args": [items]}],
        {"created": True},
    )
    parsed = parse(html)
    assert_markup_is_safe(parsed, allowed_handlers={"this.style.display='none'"})
    assert get_attr(parsed, "img", "src") == PAYLOAD_IMAGE
    assert get_attr(parsed, "img", "alt") == "Screenshot of " + PAYLOAD_TITLE
    assert get_attr(parsed, "a", "aria-label") == "Give feedback on " + PAYLOAD_TITLE
    assert PAYLOAD_TITLE in parsed.text


# ---------------------------------------------------------------------------
# 5. The detector itself must be able to catch the original vulnerability.
# ---------------------------------------------------------------------------


def test_detector_flags_original_vulnerability():
    """Guard: the assertions above must fail on the pre-fix markup."""
    old_style = (
        '<img class="project-screenshot" src="' + PAYLOAD_IMAGE + '" alt="Screenshot of Legit" '
        'loading="lazy" onerror="this.style.display=\'none\'">'
    )
    parsed = parse(old_style)
    with pytest.raises(AssertionError):
        assert_markup_is_safe(parsed, allowed_handlers={"this.style.display='none'"})

    old_style_title = '<a class="btn" aria-label="View and respond to ' + PAYLOAD_TITLE + '">Review</a>'
    parsed_title = parse(old_style_title)
    with pytest.raises(AssertionError):
        assert_markup_is_safe(parsed_title, allowed_handlers=set())


# ---------------------------------------------------------------------------
# 6. Static audit: no user-controlled field may reach markup unescaped.
# ---------------------------------------------------------------------------

USER_FIELDS = (
    r"(?:project|p|data|r|b|q|item|resp|builder|fallback|draft)"
    r"\.(?:title|description|image_url|url|question_text|project_title"
    r"|suggestion|username|avatar_url|text)\b"
)
HTML_LITERAL = r"['\"]<"


def test_no_unescaped_user_fields_in_frontend_markup():
    """Every user-controlled field concatenated into markup must be escaped.

    This catches newly added sinks that the rendering tests above do not cover.
    """
    violations = []
    for path in sorted(FRONTEND_DIR.glob("*.html")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(USER_FIELDS, line) and re.search(HTML_LITERAL, line):
                if "escapeHtml(" not in line:
                    violations.append(f"{path.name}:{lineno}: {line.strip()}")
    assert not violations, "unescaped user data interpolated into HTML:\n" + "\n".join(
        violations
    )


def test_escape_html_is_attribute_safe_in_every_page():
    """All five pages must use quote-aware escaping (regression for the P1 fix)."""
    pages = [
        "index.html",
        "discover.html",
        "my_projects.html",
        "project_detail.html",
        "project_results.html",
    ]
    for name in pages:
        source = (FRONTEND_DIR / name).read_text(encoding="utf-8")
        body = re.search(r"function escapeHtml\([^)]*\)\s*\{[^}]*\}", source)
        assert body, f"{name} does not define escapeHtml"
        fn = body.group(0)
        for needle in ['replace(/"/g', "replace(/'/g", "replace(/</g", "replace(/&/g"]:
            assert needle in fn, f"{name} escapeHtml is not attribute-safe: missing {needle}"
