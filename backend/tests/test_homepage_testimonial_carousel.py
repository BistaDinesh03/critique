"""Homepage testimonial carousel: structure, identicons, autoplay, a11y.

The testimonial section (``<section class="real-feedback">``) was redesigned
into a horizontal carousel with deterministic geometric identicons. These
tests lock down the contract the redesign promised:

1. All four testimonials (Josh Clark, Alex Lovesyuk, Dennis, Peter) remain
   present with their exact wording, names, dates, metadata and tags. The
   first three keep their original wording verbatim; Peter's is reproduced
   word-for-word with no invented fields.
2. Three or fewer testimonials render without any carousel controls.
3. Identicons are deterministic, symmetrical and fully local (SVG only).
4. Four testimonials on desktop (3 per view) produce two pages, activating
   navigation with one pagination dot per page (pages = ceil(slides/per-view)).
5. Autoplay runs on a 5-6 second interval, wraps around, and honours the
   pause/play control plus hover, focus, touch and tab-visibility pauses.
6. ``prefers-reduced-motion`` never autoplays.
7. The layout breakpoints match desktop (3) / tablet (2) / mobile (1).
8. The render harness runs the page's scripts without JavaScript errors and
   unrelated homepage functionality keeps working.

Static facts (wording, markup, CSS) are asserted against the page source;
behaviour is exercised through the real inline script inside the Node
rendering harness, same as the other homepage suites.

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
SOURCE = FRONTEND_DIR / "index.html"
SHARED_CSS = BACKEND_DIR.parent / "static" / "shared.css"

pytestmark = [
    pytest.mark.frontend_render,
    pytest.mark.skipif(
        shutil.which("node") is None,
        reason="node is required to run the frontend rendering harness",
    ),
]


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


def source():
    return SOURCE.read_text(encoding="utf-8")


def feedback_section():
    """The rendered markup of the testimonial section only."""
    src = source()
    start = src.index('<section class="real-feedback"')
    end = src.index("</section>", start)
    return src[start:end]


def add_slides(count):
    """Harness call: append `count` real slide elements, then refresh.

    The harness builds DOM elements only for tagged, id-bearing nodes, so a
    test that wants "more testimonials were added" creates the same
    ``li.fb-slide`` elements a page author would ship and asks the carousel
    to rescan, which is exactly the auto-adaptation path.
    """
    return {
        "evaluate": (
            "var t = document.getElementById('fb-track');"
            f"for (var i = 0; i < {count}; i++) {{"
            "  var li = document.createElement('li');"
            "  li.className = 'fb-slide';"
            "  t.appendChild(li);"
            "}"
            "CritiqueTestimonials.refresh();"
        ),
        "as": f"slides{count}",
    }


STATE = {"evaluate": "CritiqueTestimonials.state()", "as": "state"}


# ---------------------------------------------------------------------------
# 1-2. Testimonials present, wording and metadata unchanged
# ---------------------------------------------------------------------------


def test_all_four_testimonials_keep_their_exact_wording_and_metadata():
    src = source()

    # All four testimonials (and only these) are present. Each name appears
    # exactly twice: the visible heading and the avatar's identicon seed.
    assert src.count('class="review-card"') == 4
    assert src.count('<li class="fb-slide">') == 4
    for ident, name in (
        ("review-josh-name", "Josh Clark"),
        ("review-alex-name", "Alex Lovesyuk"),
        ("review-dennis-name", "Dennis"),
        ("review-peter-name", "Peter"),
    ):
        assert f'id="{ident}"' in src, f"missing heading for {name}"
        assert src.count(name) == 2, f"{name} must only be heading + data-name"

    # Josh Clark: role, score, summary, metadata and tags, verbatim.
    assert "Founder of Disband" in src
    assert '<div class="review-score">6.9 <span class="review-score-total">/ 10</span></div>' in src
    assert '<div class="review-score-label">Overall</div>' in src
    assert (
        "Praised the concept, flagged submission friction, inconsistent icons, "
        "UI mismatches, and concerns around analytics and security."
    ) in src
    assert "<span>External review</span>" in src
    assert "<span>Sept 2026</span>" in src
    assert "<span>Feedback received → improvements shipped</span>" in src
    for tag in ("Security", "UI", "Analytics"):
        assert f'<span class="review-tag">{tag}</span>' in src

    # The "70 tests passing" tag is untouched (issue #229 stays out of scope).
    assert src.count('<span class="review-tag accent">70 tests passing</span>') == 1

    # Alex Lovesyuk: quote, metadata, no invented role or score.
    assert "“Critique's focus on honest feedback for builders caught my eye.”" in src
    assert "<span>Twitter</span>" in src
    assert "<span>Oct 2026</span>" in src

    # Dennis: role and full quote, verbatim.
    assert '<p class="review-role">DEV</p>' in src
    assert (
        "“I like the idea behind Critique, especially the focus on helping "
        "builders improve their products through real feedback. I appreciate "
        "that you took my suggestions seriously and actually implemented "
        "improvements based on them. That kind of responsiveness makes a real "
        "difference. I'd definitely recommend Critique to other builders who "
        "want honest feedback and want to improve their products.”"
    ) in src

    # Peter: verbatim community feedback, no quotation marks added (his
    # original carried none) and no invented surname, title, company, rating,
    # date, tags or claims. The only metadata is the neutral label.
    assert (
        "Just tried Critique and left some feedback on a project. Noice "
        "concept, especally the focuse on specific question rether than "
        "generic revew.keep bui;ding"
    ) in src
    peter_card = src[src.index('id="review-peter-name"'):]
    peter_card = peter_card[: peter_card.index("</article>")]
    assert "<span>Community feedback</span>" in peter_card
    # Truthfully omits every field we cannot supply: no role, no score, no
    # date, no tags, no invented attribution beyond the first name.
    assert "review-role" not in peter_card
    assert "review-score" not in peter_card
    assert "review-tag" not in peter_card
    assert "review-meta-dot" not in peter_card
    # Peter's card never gains a quotation mark the source feedback lacked.
    assert "“" not in peter_card


def test_section_markup_is_semantic_and_carousel_labelled():
    src = source()
    section = feedback_section()

    # Region labelling: the section and the carousel both carry names.
    assert '<section class="real-feedback" aria-labelledby="real-feedback-title">' in src
    assert '<h2 id="real-feedback-title">What builders say</h2>' in src
    assert 'id="fb-carousel" role="region" aria-roledescription="carousel"' in src
    assert 'aria-label="What builders say"' in src

    # Semantic list structure for the slides.
    assert '<ul class="fb-track" id="fb-track" role="list">' in src
    assert src.count('<li class="fb-slide">') == 4

    # Real buttons with accessible names; controls start hidden.
    assert '<button type="button" class="fb-nav" id="fb-prev" aria-label="Previous testimonials">' in src
    assert '<button type="button" class="fb-nav" id="fb-next" aria-label="Next testimonials">' in src
    assert '<button type="button" class="fb-toggle" id="fb-pause">Pause</button>' in src
    assert '<div class="fb-controls" id="fb-controls" hidden>' in src
    assert 'id="fb-dots" role="group" aria-label="Testimonial pages"' in src

    # Autoplay stays inside the agreed 5-6 second band.
    autoplay = re.search(r'data-autoplay="(\d+)"', section)
    assert autoplay, "carousel must declare its autoplay interval"
    assert 5000 <= int(autoplay.group(1)) <= 6000

    # Testimonial text lives in the markup itself, never fetched or hidden:
    # no network references and no images inside this section.
    assert "http" not in section
    assert "url(" not in section
    assert "<img" not in section

    # Avatars map names to identicons; the letter initial is kept as the
    # graceful no-JavaScript fallback.
    for name, initial in (
        ("Josh Clark", "J"),
        ("Alex Lovesyuk", "A"),
        ("Dennis", "D"),
        ("Peter", "P"),
    ):
        assert (
            f'<div class="review-avatar" data-name="{name}" aria-hidden="true">{initial}</div>'
            in src
        )


# ---------------------------------------------------------------------------
# 3. Three testimonials show no unnecessary controls
# ---------------------------------------------------------------------------


def test_three_testimonials_render_without_carousel_controls(tmp_path):
    result = run(
        tmp_path,
        "index.html",
        [
            add_slides(3),
            STATE,
            {"evaluate": "document.getElementById('fb-track').style.transform", "as": "transform"},
        ],
    )

    state = result["values"]["state"]
    assert state["slideCount"] == 3
    assert state["perView"] == 3
    assert state["pages"] == 1
    assert state["controlsVisible"] is False
    assert state["autoplayActive"] is False
    assert result["flags"]["fb-controls"]["hidden"] is True
    assert result["ids"]["fb-dots"] == ""
    # No sliding is applied while there is a single page.
    assert result["values"]["transform"] == ""


# ---------------------------------------------------------------------------
# 4. Identicons: deterministic, symmetrical, local
# ---------------------------------------------------------------------------


def test_identicons_are_deterministic_symmetric_and_local(tmp_path):
    result = run(
        tmp_path,
        "index.html",
        [
            {
                "evaluate": (
                    "({"
                    "a: CritiqueTestimonials.identicon('Josh Clark'),"
                    "b: CritiqueTestimonials.identicon('Josh Clark'),"
                    "c: CritiqueTestimonials.identicon('Dennis'),"
                    "d: CritiqueTestimonials.identicon('Alex Lovesyuk')"
                    "})"
                ),
                "as": "icons",
            }
        ],
    )
    icons = result["values"]["icons"]

    # Same name, byte-identical avatar; different names, different avatars.
    assert icons["a"] == icons["b"], "identicon must be deterministic per name"
    assert icons["a"] != icons["c"]
    assert icons["a"] != icons["d"]

    svg = icons["a"]
    assert svg.startswith("<svg viewBox=\"0 0 40 40\"")
    assert 'aria-hidden="true"' in svg
    assert 'focusable="false"' in svg
    # Design tokens only: no network references, no external images.
    assert "http" not in svg
    assert "<img" not in svg
    assert "fb-id-bg" in svg
    assert "fb-id-neutral" in svg or "fb-id-accent" in svg
    assert svg.count("<rect") > 1, "pattern must contain filled cells"

    # Symmetry: the grid mirrors across the vertical axis, so the cell
    # columns at index 0/4 and 1/3 must carry identical counts. The lookbehind
    # skips the rounded-corner rx attributes on the same elements.
    columns = [int(x) for x in re.findall(r'(?<!r)x="(\d+)"', svg)]
    by_col = {c: columns.count(c) for c in set(columns)}
    assert by_col.get(1, 0) == by_col.get(33, 0), "outer columns must mirror"
    assert by_col.get(9, 0) == by_col.get(25, 0), "inner columns must mirror"


# ---------------------------------------------------------------------------
# 5-6. A fourth testimonial activates navigation; pagination matches pages
# ---------------------------------------------------------------------------


def test_fourth_testimonial_activates_navigation_and_pagination(tmp_path):
    result = run(tmp_path, "index.html", [add_slides(4), STATE])

    state = result["values"]["state"]
    assert state["slideCount"] == 4
    assert state["perView"] == 3
    assert state["pages"] == 2, "4 slides at 3 per view = 2 pages"
    assert state["controlsVisible"] is True
    assert state["autoplayActive"] is True
    assert result["flags"]["fb-controls"]["hidden"] is False

    # One dot per page, each labelled, exactly one marked current.
    dots = result["ids"]["fb-dots"]
    assert dots.count('class="fb-dot"') == 2
    assert 'aria-label="Show testimonial page 1 of 2"' in dots
    assert 'aria-label="Show testimonial page 2 of 2"' in dots
    assert dots.count('aria-current="true"') == 1
    assert 'class="fb-dot" data-page="0" aria-label' in dots
    assert 'aria-current="true"' in dots


def test_four_real_slides_page_across_desktop_with_visible_controls(tmp_path):
    """The shipped markup (4 slides) yields two desktop pages and controls.

    Reads the real slide count out of the page source rather than a hard-coded
    number, so the page math stays verified even if a fifth testimonial lands
    later: desktop shows 3 per view, so controls must appear iff there is more
    than one page.
    """
    real_slides = source().count('<li class="fb-slide">')
    assert real_slides == 4, "homepage ships four testimonial slides"

    result = run(tmp_path, "index.html", [add_slides(real_slides), STATE])
    state = result["values"]["state"]

    per_view = state["perView"]  # desktop default is 3
    assert per_view == 3
    expected_pages = -(-real_slides // per_view)  # ceil division
    assert expected_pages == 2, "four cards over three-per-view is two pages"
    assert state["pages"] == expected_pages
    assert state["controlsVisible"] is (expected_pages > 1)
    assert result["flags"]["fb-controls"]["hidden"] is False
    # Pagination exposes exactly one dot per page.
    assert result["ids"]["fb-dots"].count('class="fb-dot"') == expected_pages


def test_navigation_wraps_and_pause_play_controls_autoplay(tmp_path):
    # Wrap-around navigation: next on the last page returns to the first,
    # prev on the first page reaches the last.
    ordered = run(
        tmp_path,
        "index.html",
        [
            add_slides(4),
            {"clickId": "fb-next"},
            {"evaluate": "CritiqueTestimonials.state().page", "as": "p1"},
            {"clickId": "fb-next"},
            {"evaluate": "CritiqueTestimonials.state().page", "as": "p2"},
            {"clickId": "fb-prev"},
            {"evaluate": "CritiqueTestimonials.state().page", "as": "p3"},
        ],
    )["values"]
    assert ordered["p1"] == 1
    assert ordered["p2"] == 0, "next on the last page must wrap to the first"
    assert ordered["p3"] == 1, "prev on the first page must wrap to the last"

    # Manual navigation hands control to the user: the Pause/Play control
    # reports the state through its accessible name and rotation stays off
    # until Play is pressed.
    result = run(
        tmp_path,
        "index.html",
        [
            add_slides(4),
            {"clickId": "fb-pause"},
            {"evaluate": "CritiqueTestimonials.state()", "as": "paused"},
            {"evaluate": "document.getElementById('fb-pause').innerHTML", "as": "paused_label"},
            {"clickId": "fb-pause"},
            {"evaluate": "CritiqueTestimonials.state()", "as": "resumed"},
            {"evaluate": "document.getElementById('fb-pause').innerHTML", "as": "resumed_label"},
        ],
    )
    values = result["values"]
    assert values["paused"]["userPaused"] is True
    assert values["paused"]["autoplayActive"] is False
    assert values["paused_label"] == "Play"
    assert values["resumed"]["userPaused"] is False
    assert values["resumed"]["autoplayActive"] is True
    assert values["resumed_label"] == "Pause"


# ---------------------------------------------------------------------------
# 7. Autoplay interval: 5-6 seconds
# ---------------------------------------------------------------------------


def test_autoplay_interval_is_between_five_and_six_seconds(tmp_path):
    # Fresh run: intercept setInterval to observe the real interval the
    # carousel requests when rotation becomes active.
    result = run(
        tmp_path,
        "index.html",
        [
            {
                "evaluate": (
                    "var seen = [];"
                    "setInterval = function (fn, ms) { seen.push(ms); return 0; };"
                    "var t = document.getElementById('fb-track');"
                    "for (var i = 0; i < 4; i++) {"
                    "  var li = document.createElement('li');"
                    "  li.className = 'fb-slide';"
                    "  t.appendChild(li);"
                    "}"
                    "CritiqueTestimonials.refresh();"
                    "({seen: seen, state: CritiqueTestimonials.state()})"
                ),
                "as": "autoplay",
            }
        ],
    )
    autoplay = result["values"]["autoplay"]

    assert autoplay["seen"], "rotation must schedule an interval when active"
    for ms in autoplay["seen"]:
        assert 5000 <= ms <= 6000, f"interval {ms}ms outside the 5-6s band"
    assert autoplay["state"]["autoplayMs"] == 5500
    assert autoplay["state"]["autoplayActive"] is True

    # The interval is declared on the markup too, inside the same band.
    assert 'data-autoplay="5500"' in source()


# ---------------------------------------------------------------------------
# 8. Desktop / tablet / mobile layouts
# ---------------------------------------------------------------------------


def test_layout_matches_desktop_tablet_and_mobile():
    src = source()

    # Section caps at ~1040px.
    assert re.search(r"\.real-feedback\s*\{[^}]*max-width:\s*1040px", src), (
        "carousel section must be able to use the full ~1040px row"
    )

    # Viewport clips the paged track only when JS enhanced the carousel,
    # which is what keeps horizontal page overflow impossible.
    assert re.search(
        r'\.fb-carousel\[data-enhanced="true"\] \.fb-viewport\s*\{\s*overflow:\s*hidden',
        src,
    )

    # Desktop: three cards across, gap from the design token.
    assert "--fb-gap: var(--space-5)" in src
    assert re.search(
        r'\.fb-carousel\[data-enhanced="true"\] \.fb-slide\s*\{[^}]*'
        r"flex:\s*0 0 calc\(\(100% - var\(--fb-gap\) \* 2\) / 3\)",
        src,
    )

    # Tablet: two cards across.
    tablet = src[src.index("@media (max-width: 900px)") :]
    assert 'flex: 0 0 calc((100% - var(--fb-gap)) / 2)' in tablet

    # Mobile: one card at a time.
    mobile = src[src.index("@media (max-width: 600px)") :]
    assert "flex: 0 0 100%" in mobile

    # Equal heights: slides stretch, cards fill the slide.
    assert re.search(r"\.fb-track\s*\{[^}]*align-items:\s*stretch", src)
    assert re.search(r"\.fb-slide\s*\{[^}]*display:\s*flex", src)

    # Balanced cards: the card is a flex column and the metadata row is
    # anchored to the bottom, so a short quote leaves its breathing room
    # above the row instead of pooling empty space beneath it.
    assert re.search(
        r"\.review-card\s*\{[^}]*display:\s*flex;[^}]*flex-direction:\s*column", src, re.S
    ), "review card must be a flex column so short cards stay balanced"
    assert re.search(
        r"\.review-meta\s*\{[^}]*margin-top:\s*auto", src, re.S
    ), "metadata must anchor to the card bottom"

    # Without JS the track wraps instead of clipping, so no testimonial is
    # ever unreachable. The enhanced viewport clips its own overflow, which is
    # what keeps horizontal page overflow impossible.
    assert re.search(r"\.fb-track\s*\{[^}]*flex-wrap:\s*wrap", src)
    assert 'flex-wrap: nowrap' in src
    assert re.search(
        r'\.fb-carousel\[data-enhanced="true"\] \.fb-viewport\s*\{[^}]*overflow:\s*hidden', src, re.S
    ), "the paged viewport must clip so cards never overflow the page"


# ---------------------------------------------------------------------------
# 9. Reduced motion never autoplays
# ---------------------------------------------------------------------------


def test_reduced_motion_never_autoplays(tmp_path):
    assert "(prefers-reduced-motion: reduce)" in source()

    result = run(
        tmp_path,
        "index.html",
        [
            add_slides(4),
            {"evaluate": "CritiqueTestimonials.state()", "as": "before"},
            {"evaluate": "CritiqueTestimonials.setMotionPreference(true) || CritiqueTestimonials.state()", "as": "on"},
            {"evaluate": "CritiqueTestimonials.setMotionPreference(false) || CritiqueTestimonials.state()", "as": "off"},
            {"clickId": "fb-pause"},  # explicit user opt-in still works
            {"evaluate": "CritiqueTestimonials.state()", "as": "manual"},
        ],
    )
    values = result["values"]

    assert values["before"]["autoplayActive"] is True
    assert values["on"]["reducedMotion"] is True
    assert values["on"]["autoplayActive"] is False, "reduced motion must not autoplay"
    assert values["on"]["running"] is False, "the interval must be cleared"
    # Leaving reduced motion does not restart rotation on its own...
    assert values["off"]["autoplayActive"] is False
    # ...but the user can still start it explicitly with Play.
    assert values["manual"]["userPaused"] is False
    assert values["manual"]["autoplayActive"] is True


# ---------------------------------------------------------------------------
# 10. Pause on hover, focus, touch and tab visibility
# ---------------------------------------------------------------------------


def test_hover_focus_touch_and_visibility_pause_autoplay(tmp_path):
    # The carousel element must actually be wired for those interactions.
    registration = run(
        tmp_path,
        "index.html",
        [
            {
                "evaluate": (
                    "document.getElementById('fb-carousel').handlers"
                    ".map(function (h) { return h.type; })"
                ),
                "as": "types",
            }
        ],
    )["values"]["types"]
    for event in ("mouseenter", "mouseleave", "focusin", "focusout", "touchstart", "touchend"):
        assert event in registration, f"missing {event} listener on the carousel"

    result = run(
        tmp_path,
        "index.html",
        [
            add_slides(4),
            {"evaluate": "CritiqueTestimonials.state()", "as": "initial"},
            {"evaluate": "CritiqueTestimonials.pause('hover') || CritiqueTestimonials.state()", "as": "hover_on"},
            {"evaluate": "CritiqueTestimonials.resume('hover') || CritiqueTestimonials.state()", "as": "hover_off"},
            {"evaluate": "CritiqueTestimonials.pause('focus') || CritiqueTestimonials.state()", "as": "focus_on"},
            {"evaluate": "CritiqueTestimonials.resume('focus') || CritiqueTestimonials.state()", "as": "focus_off"},
            {
                "evaluate": (
                    "CritiqueTestimonials.touchStart({touches: [{clientX: 200, clientY: 100}]});"
                    "CritiqueTestimonials.state()"
                ),
                "as": "touch_on",
            },
            {
                "evaluate": (
                    "CritiqueTestimonials.touchEnd({changedTouches: [{clientX: 180, clientY: 104}]});"
                    "CritiqueTestimonials.state()"
                ),
                "as": "touch_off",
            },
            {
                "evaluate": "document.hidden = true; CritiqueTestimonials.visibility(); CritiqueTestimonials.state()",
                "as": "hidden_on",
            },
            {
                "evaluate": "document.hidden = false; CritiqueTestimonials.visibility(); CritiqueTestimonials.state()",
                "as": "hidden_off",
            },
            {
                "evaluate": (
                    "CritiqueTestimonials.touchStart({touches: [{clientX: 200, clientY: 100}]});"
                    "CritiqueTestimonials.touchEnd({changedTouches: [{clientX: 40, clientY: 112}]});"
                    "CritiqueTestimonials.state()"
                ),
                "as": "after_swipe",
            },
        ],
    )
    v = result["values"]

    assert v["initial"]["autoplayActive"] is True

    assert v["hover_on"]["pausedFor"]["hover"] is True
    assert v["hover_on"]["autoplayActive"] is False
    assert v["hover_off"]["autoplayActive"] is True

    assert v["focus_on"]["pausedFor"]["focus"] is True
    assert v["focus_on"]["autoplayActive"] is False
    assert v["focus_off"]["autoplayActive"] is True

    assert v["touch_on"]["pausedFor"]["touch"] is True
    assert v["touch_on"]["autoplayActive"] is False
    assert v["touch_off"]["autoplayActive"] is True

    assert v["hidden_on"]["pausedFor"]["hidden"] is True
    assert v["hidden_on"]["autoplayActive"] is False
    assert v["hidden_off"]["autoplayActive"] is True

    # A horizontal swipe advances one page and hands control to the user.
    assert v["after_swipe"]["page"] == 1
    assert v["after_swipe"]["userPaused"] is True
    assert v["after_swipe"]["autoplayActive"] is False


# ---------------------------------------------------------------------------
# 10. Keyboard accessibility
# ---------------------------------------------------------------------------


def test_controls_are_keyboard_accessible_buttons():
    src = source()
    css = SHARED_CSS.read_text(encoding="utf-8")

    # Real buttons (native Enter/Space activation), all labelled.
    assert src.count('<button type="button" class="fb-nav"') == 2
    assert 'id="fb-prev" aria-label="Previous testimonials"' in src
    assert 'id="fb-next" aria-label="Next testimonials"' in src
    assert '<button type="button" class="fb-toggle" id="fb-pause">Pause</button>' in src

    # The pause control swaps between Pause and Play, so its state is
    # announced through the accessible name rather than colour alone.
    assert "state.userPaused ? 'Play' : 'Pause'" in src

    # Pagination buttons are created as labelled buttons with aria-current.
    assert '<button type="button" class="fb-dot" data-page="' in src
    assert "aria-label=\"Show testimonial page " in src
    assert "(i === state.page ? ' aria-current=\"true\"' : '')" in src

    # Visible focus comes from the shared focus-visible outline.
    assert ":focus-visible" in css
    assert "outline: 2px solid var(--focus)" in css


# ---------------------------------------------------------------------------
# 11-12. Harness runs error-free; no homepage regressions
# ---------------------------------------------------------------------------


def test_render_harness_is_error_free_and_homepage_features_survive(tmp_path):
    # The page's scripts (including the new carousel block) must execute
    # without a single JavaScript error on load.
    result = run(tmp_path, "index.html", [])
    assert result["errors"] == []

    src = source()
    # Social-proof avatar stack (a separate feature) is untouched.
    assert 'id="avatar-stack"' in src
    assert "loadSocialProof" in src
    # The dynamic builder count still comes from /api/stats.
    assert "total_builders" in src
    assert re.search(r"total_builders\s*>\s*0", src)
    # Login-gated project submission still present.
    assert "showProjectInlineLoginPrompt" in src
    # The test-count tag stays exactly as-is (issue #229 out of scope).
    assert src.count("70 tests passing") == 1
