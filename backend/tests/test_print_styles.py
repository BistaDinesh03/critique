import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSS_PATH = ROOT / "static" / "shared.css"
FRONTEND_DIR = ROOT / "frontend"
PAGES = ("project_detail.html", "project_results.html")


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


def test_print_hides_navigation_footer_buttons_and_forms():
    selectors = _hidden_selectors(_print_css())
    for sel in (".navbar", ".site-footer", ".breadcrumb-nav", ".btn", "button", "form", "textarea", ".no-print"):
        assert sel in selectors, f"{sel} not hidden in print"


def test_print_uses_high_contrast_ink_on_white():
    block = _print_css()
    assert re.search(r"--background:\s*#fff(fff)?", block)
    assert re.search(r"--surface:\s*#fff(fff)?", block)
    assert re.search(r"--text-primary:\s*#000(000)?", block)
    assert "color-scheme: light" in block
    assert re.search(r"body\s*\{[^}]*background:\s*#fff", block)


def test_print_does_not_clip_content():
    block = _print_css()
    assert re.search(r"overflow:\s*visible", block)
    assert "box-shadow: none" in block
    assert "break-inside: avoid" in block
    assert re.search(r"\.container-wide", block)


def test_print_rules_are_additive_for_screen():
    css = CSS_PATH.read_text(encoding="utf-8")
    start = css.find("@media print")
    assert css.count("@media print") == 1
    # print block is last, so it can only affect print media
    depth, i = 0, css.find("{", start)
    while i < len(css):
        depth += {"{": 1, "}": -1}.get(css[i], 0)
        i += 1
        if depth == 0:
            break
    assert css[i:].strip() == ""


def test_both_pages_load_shared_print_rules():
    for page in PAGES:
        html = (FRONTEND_DIR / page).read_text(encoding="utf-8")
        assert '<link rel="stylesheet" href="/static/shared.css">' in html
        assert 'class="navbar"' in html and 'class="site-footer"' in html
