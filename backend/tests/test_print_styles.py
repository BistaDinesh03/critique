import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSS_PATH = ROOT / "static" / "shared.css"
FRONTEND_DIR = ROOT / "frontend"
PAGES = ("discover.html", "project_detail.html", "project_results.html")


def _print_css() -> str:
    css = CSS_PATH.read_text(encoding="utf-8")
    start = css.find("@media print")
    assert start != -1, "shared.css has no @media print block"
    i = css.find("{", start) + 1
    depth = 1
    while depth and i < len(css):
        depth += {"{": 1, "}": -1}.get(css[i], 0)
        i += 1
    return css[css.find("{", start) + 1 : i - 1]


def _hidden_selectors(block: str) -> str:
    match = re.search(r"([^{}]+)\{[^}]*display:\s*none\s*!important", block)
    assert match, "no display: none rule in print block"
    return match.group(1)


def _rule_body(block: str, selector: str) -> str:
    pattern = re.escape(selector) + r"\s*\{([^}]*)\}"
    match = re.search(pattern, block)
    assert match, f"no rule for {selector!r} in print block"
    return match.group(1)


def test_print_hides_navigation_footer_buttons_and_forms():
    selectors = _hidden_selectors(_print_css())
    for sel in (".navbar", ".site-footer", ".breadcrumb-nav", ".btn", "button", "form", "textarea", ".no-print"):
        assert sel in selectors, f"{sel} not hidden in print"


def test_print_hides_discover_interactive_and_non_printable_chrome():
    selectors = _hidden_selectors(_print_css())
    for sel in (".skip-link", ".pagination", ".skeleton-card", ".back-to-top", ".modal-backdrop", "input"):
        assert sel in selectors, f"{sel} not hidden in print"


def test_print_uses_high_contrast_ink_on_white():
    block = _print_css()
    assert re.search(r"--background:\s*#fff(fff)?", block)
    assert re.search(r"--surface:\s*#fff(fff)?", block)
    assert re.search(r"--text-primary:\s*#000(000)?", block)
    assert "color-scheme: light" in block
    assert re.search(r"body\s*\{[^}]*background:\s*#fff", block)


def test_print_overrides_dark_theme_custom_properties():
    block = _print_css()
    assert ':root[data-theme="dark"]' in block
    assert ':root:not([data-theme="light"])' in block
    assert re.search(r"--success-bg:\s*#fff(fff)?", block)
    assert re.search(r"--success-text:\s*#000(000)?", block)


def test_print_does_not_clip_content():
    block = _print_css()
    assert re.search(r"overflow:\s*visible", block)
    assert "box-shadow: none" in block
    assert "break-inside: avoid" in block
    assert re.search(r"\.container-wide", block)


def test_print_styles_discover_grid_and_project_cards():
    block = _print_css()
    project_list_rule = _rule_body(block, ".project-list")
    assert re.search(r"display:\s*block\s*!important", project_list_rule)
    assert re.search(r"max-width:\s*none\s*!important", project_list_rule)

    assert re.search(
        r"\.project-card\s*\{[^}]*break-inside:\s*avoid[^}]*page-break-inside:\s*avoid",
        block,
        re.DOTALL,
    )
    assert re.search(
        r"\.project-card\s*\{[^}]*overflow:\s*visible\s*!important",
        block,
        re.DOTALL,
    )
    assert re.search(
        r"\.project-card\s*\{[^}]*box-shadow:\s*none\s*!important",
        block,
        re.DOTALL,
    )
    assert re.search(
        r"\.project-card\s*\{[^}]*transform:\s*none\s*!important",
        block,
        re.DOTALL,
    )

    desc_rule = _rule_body(block, ".project-description")
    assert re.search(r"display:\s*block\s*!important", desc_rule)
    assert re.search(r"-webkit-line-clamp:\s*unset\s*!important", desc_rule)
    assert re.search(r"overflow:\s*visible\s*!important", desc_rule)

    title_rule = _rule_body(block, ".page-title")
    assert "break-after: avoid" in title_rule
    assert "page-break-after: avoid" in title_rule

    screenshot_rule = _rule_body(block, ".project-screenshot")
    assert "max-height:" in screenshot_rule

    badge_rule = _rule_body(block, ".badge")
    assert "border:" in badge_rule


def test_print_rules_are_additive_for_screen():
    css = CSS_PATH.read_text(encoding="utf-8")
    assert css.count("@media print") == 1
    start = css.find("@media print")
    depth, i = 0, css.find("{", start)
    assert i != -1, "@media print block has no opening brace"
    while i < len(css):
        depth += {"{": 1, "}": -1}.get(css[i], 0)
        i += 1
        if depth == 0:
            break
    assert depth == 0, "@media print block has unbalanced braces"
    print_block = css[start:i]
    outside_print = css[:start] + css[i:]
    assert ".no-print" in print_block
    assert ".no-print" not in outside_print
    assert ".project-list" in print_block
    assert ".project-list" not in outside_print
    assert ".project-card" in print_block
    assert ".project-card" not in outside_print
    assert not re.search(r"\.navbar[^{]*\{[^}]*display:\s*none\s*!important", outside_print)


def test_pages_load_shared_print_rules():
    for page in PAGES:
        html = (FRONTEND_DIR / page).read_text(encoding="utf-8")
        assert '<link rel="stylesheet" href="/static/shared.css">' in html
        assert 'class="navbar"' in html and 'class="site-footer"' in html


def test_discover_markup_matches_print_selectors():
    html = (FRONTEND_DIR / "discover.html").read_text(encoding="utf-8")
    for token in (
        'class="skip-link"',
        'class="page-title"',
        'class="project-list"',
        "project-card",
        "project-screenshot",
        "project-description",
        'class="pagination"',
        "skeleton-card",
        'class="back-to-top"',
        "badge-success",
    ):
        assert token in html, f"{token} missing from discover.html"
