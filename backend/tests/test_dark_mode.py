from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSS_PATH = ROOT / "static" / "shared.css"
FRONTEND_DIR = ROOT / "frontend"


def test_dark_mode_css_variables_defined():
    css = CSS_PATH.read_text(encoding="utf-8")
    assert "@media (prefers-color-scheme: dark)" in css
    assert "color-scheme: light dark" in css

    # Check key dark theme variables
    assert "--background: #0f172a" in css
    assert "--surface: #1e293b" in css
    assert "--text-primary: #f8fafc" in css
    assert "--border: #334155" in css
    assert "--accent: #3b82f6" in css


def test_html_pages_carry_color_scheme_meta_tag():
    pages = ["index.html", "discover.html", "my_projects.html", "project_detail.html"]
    for page in pages:
        html = (FRONTEND_DIR / page).read_text(encoding="utf-8")
        assert '<meta name="color-scheme" content="light dark">' in html, f"{page} missing color-scheme meta tag"
