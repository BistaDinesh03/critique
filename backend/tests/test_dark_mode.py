import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSS_PATH = ROOT / "static" / "shared.css"
FRONTEND_DIR = ROOT / "frontend"


def _extract_css_rule(css: str, selector: str) -> str:
    """Extract the declaration body of a CSS selector."""
    escaped = re.escape(selector)
    pattern = rf"{escaped}\s*\{{([^}}]+)\}}"
    match = re.search(pattern, css)
    assert match, f"Selector '{selector}' not found in CSS"
    return match.group(1)


def _extract_media_block(css: str, media_query: str) -> str:
    """Extract content inside a @media block."""
    start = css.find(media_query)
    assert start != -1, f"Media query '{media_query}' not found"
    brace_open = css.find("{", start)
    depth = 1
    i = brace_open + 1
    while depth > 0 and i < len(css):
        if css[i] == "{":
            depth += 1
        elif css[i] == "}":
            depth -= 1
        i += 1
    return css[brace_open + 1 : i - 1]


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


def test_theme_aware_alert_text_variables_defined_in_light_and_dark_themes():
    """Assert --success-text, --danger-text, and --warning-text are defined in both themes."""
    css = CSS_PATH.read_text(encoding="utf-8")

    # Light theme (:root before @media)
    root_match = re.search(r":root\s*\{([^}]+)\}", css)
    assert root_match, "Light theme :root block not found"
    light_root = root_match.group(1)

    assert "--success-text:" in light_root
    assert "--danger-text:" in light_root
    assert "--warning-text:" in light_root

    # Dark theme (@media (prefers-color-scheme: dark))
    dark_block = _extract_media_block(css, "@media (prefers-color-scheme: dark)")
    assert "--success-text:" in dark_block
    assert "--danger-text:" in dark_block
    assert "--warning-text:" in dark_block


def test_alert_classes_reference_theme_aware_text_variables():
    """Assert alert classes reference theme-aware variables rather than hard-coded hex colors."""
    css = CSS_PATH.read_text(encoding="utf-8")

    alert_rules = {
        ".alert-success": "--success-text",
        ".alert-error": "--danger-text",
        ".alert-warning": "--warning-text",
    }

    hex_color_pattern = re.compile(r"#[0-9a-fA-F]{3,8}")

    for selector, var_name in alert_rules.items():
        rule_body = _extract_css_rule(css, selector)
        color_match = re.search(r"color\s*:\s*([^;]+);", rule_body)
        assert color_match, f"{selector} does not define a 'color' property"
        color_val = color_match.group(1).strip()
        assert f"var({var_name})" in color_val, (
            f"{selector} color '{color_val}' must reference var({var_name})"
        )
        assert not hex_color_pattern.search(color_val), (
            f"{selector} color must not contain a hardcoded hex color: {color_val}"
        )


def test_login_prompt_form_input_uses_surface_background():
    """Assert .login-prompt-form .form-input sets background: var(--surface)."""
    css = CSS_PATH.read_text(encoding="utf-8")
    rule_body = _extract_css_rule(css, ".login-prompt-form .form-input")

    bg_match = re.search(r"background\s*:\s*([^;]+);", rule_body)
    assert bg_match, ".login-prompt-form .form-input missing background declaration"
    bg_val = bg_match.group(1).strip()
    assert "var(--surface)" in bg_val, (
        f".login-prompt-form .form-input background '{bg_val}' must use var(--surface)"
    )


def test_html_pages_carry_color_scheme_meta_tag():
    pages = ["index.html", "discover.html", "my_projects.html", "project_detail.html"]
    for page in pages:
        html = (FRONTEND_DIR / page).read_text(encoding="utf-8")
        assert '<meta name="color-scheme" content="light dark">' in html, f"{page} missing color-scheme meta tag"
