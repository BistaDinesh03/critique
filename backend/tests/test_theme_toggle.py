"""Frontend rendering and CSS tests for the manual dark/light theme toggle."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT / "frontend"
CSS_PATH = ROOT / "static" / "shared.css"
HARNESS = Path(__file__).resolve().parent / "frontend_render_harness.js"

PAGES = [
    "index.html",
    "discover.html",
    "my_projects.html",
    "project_detail.html",
    "project_results.html",
    "404.html",
]

pytestmark = [
    pytest.mark.frontend_render,
    pytest.mark.skipif(
        shutil.which("node") is None,
        reason="node is required to run the frontend rendering harness",
    ),
]


def _run_harness(
    tmp_path,
    page_path,
    calls=None,
    local_storage=None,
    prefers_color_scheme=None,
    location="/",
    name="scenario.json",
):
    scenario = {
        "page": Path(page_path).as_posix(),
        "calls": calls or [],
        "fetch": {},
        "location": location,
        "read": {"created": True},
    }
    if local_storage is not None:
        scenario["localStorage"] = local_storage
    if prefers_color_scheme is not None:
        scenario["prefersColorScheme"] = prefers_color_scheme

    scenario_file = tmp_path / name
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


def test_all_pages_render_accessible_theme_toggle_and_head_bootstrap():
    for page in PAGES:
        html = (FRONTEND_DIR / page).read_text(encoding="utf-8")
        assert 'class="theme-toggle"' in html, f"{page} missing .theme-toggle button"
        assert 'id="theme-toggle"' in html, f"{page} missing #theme-toggle id"
        assert re.search(
            r'<button\b[^>]*type="button"[^>]*class="theme-toggle"[^>]*aria-label="[^"]+"[^>]*aria-pressed="(?:true|false)"',
            html,
        ), f"{page} theme-toggle must declare type=button, aria-label, and aria-pressed"

        head_match = re.search(r"<head>(.*?)</head>", html, re.DOTALL)
        assert head_match, f"{page} missing <head>"
        head_html = head_match.group(1)
        assert "critique-theme" in head_html, f"{page} missing <head> theme bootstrap"
        assert head_html.index("critique-theme") < head_html.index("/static/shared.css"), (
            f"{page} theme bootstrap must execute before shared.css"
        )


def test_shared_css_supports_manual_theme_override_and_focus_visible():
    css = CSS_PATH.read_text(encoding="utf-8")
    assert ':root[data-theme="dark"]' in css
    assert ':root[data-theme="light"]' in css
    assert ':root:not([data-theme="light"])' in css
    assert re.search(r"\.theme-toggle:focus-visible\s*\{[^}]*outline\s*:", css)


def test_unset_storage_respects_prefers_color_scheme_without_forcing_attribute(tmp_path):
    light_result = _run_harness(
        tmp_path,
        FRONTEND_DIR / "index.html",
        calls=[
            {
                "evaluate": "document.documentElement.getAttribute('data-theme')",
                "as": "data_theme",
            },
        ],
        prefers_color_scheme="light",
        name="light.json",
    )
    assert light_result["values"]["data_theme"] is None
    assert light_result["storage"]["local"] == {}
    assert light_result["flags"]["theme-toggle"]["ariaPressed"] == "false"
    assert light_result["flags"]["theme-toggle"]["ariaLabel"] == "Switch to dark theme"

    dark_result = _run_harness(
        tmp_path,
        FRONTEND_DIR / "index.html",
        calls=[
            {
                "evaluate": "document.documentElement.getAttribute('data-theme')",
                "as": "data_theme",
            },
        ],
        prefers_color_scheme="dark",
        name="dark.json",
    )
    assert dark_result["values"]["data_theme"] is None
    assert dark_result["storage"]["local"] == {}
    assert dark_result["flags"]["theme-toggle"]["ariaPressed"] == "true"
    assert dark_result["flags"]["theme-toggle"]["ariaLabel"] == "Switch to light theme"


def test_clicking_toggle_switches_theme_and_persists_to_local_storage(tmp_path):
    # From light OS: first click -> dark, second click -> light.
    first_click = _run_harness(
        tmp_path,
        FRONTEND_DIR / "index.html",
        calls=[
            {"clickId": "theme-toggle"},
            {
                "evaluate": "document.documentElement.getAttribute('data-theme')",
                "as": "data_theme",
            },
        ],
        prefers_color_scheme="light",
        name="light_to_dark.json",
    )
    assert first_click["values"]["data_theme"] == "dark"
    assert first_click["storage"]["local"]["critique-theme"] == "dark"
    assert first_click["flags"]["theme-toggle"]["ariaPressed"] == "true"
    assert first_click["flags"]["theme-toggle"]["ariaLabel"] == "Switch to light theme"

    second_click = _run_harness(
        tmp_path,
        FRONTEND_DIR / "index.html",
        calls=[
            {"clickId": "theme-toggle"},
            {"clickId": "theme-toggle"},
            {
                "evaluate": "document.documentElement.getAttribute('data-theme')",
                "as": "data_theme",
            },
        ],
        prefers_color_scheme="light",
        name="dark_to_light.json",
    )
    assert second_click["values"]["data_theme"] == "light"
    assert second_click["storage"]["local"]["critique-theme"] == "light"
    assert second_click["flags"]["theme-toggle"]["ariaPressed"] == "false"
    assert second_click["flags"]["theme-toggle"]["ariaLabel"] == "Switch to dark theme"

    # From dark OS with unset storage: first click switches to opposite (light).
    dark_os_first_click = _run_harness(
        tmp_path,
        FRONTEND_DIR / "discover.html",
        calls=[
            {"clickId": "theme-toggle"},
            {
                "evaluate": "document.documentElement.getAttribute('data-theme')",
                "as": "data_theme",
            },
        ],
        prefers_color_scheme="dark",
        location="/discover",
        name="dark_os_to_light.json",
    )
    assert dark_os_first_click["values"]["data_theme"] == "light"
    assert dark_os_first_click["storage"]["local"]["critique-theme"] == "light"
    assert dark_os_first_click["flags"]["theme-toggle"]["ariaPressed"] == "false"
    assert dark_os_first_click["flags"]["theme-toggle"]["ariaLabel"] == "Switch to dark theme"


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("saved_theme", ["dark", "light"])
def test_prepopulated_storage_applies_in_head_bootstrap_across_pages(
    tmp_path, page, saved_theme
):
    full_html = (FRONTEND_DIR / page).read_text(encoding="utf-8")
    head_only_html = full_html.split("</head>", 1)[0] + "</head></html>"
    head_page = tmp_path / f"head_{page}"
    head_page.write_text(head_only_html, encoding="utf-8")

    # Head bootstrap alone (before ui.js or body) must set data-theme immediately.
    head_result = _run_harness(
        tmp_path,
        head_page,
        calls=[
            {
                "evaluate": "document.documentElement.getAttribute('data-theme')",
                "as": "data_theme",
            },
        ],
        local_storage={"critique-theme": saved_theme},
        name=f"head_{page}_{saved_theme}.json",
    )
    assert head_result["values"]["data_theme"] == saved_theme

    # Full page also initializes the toggle button to match the persisted theme.
    full_result = _run_harness(
        tmp_path,
        FRONTEND_DIR / page,
        calls=[
            {
                "evaluate": "document.documentElement.getAttribute('data-theme')",
                "as": "data_theme",
            },
        ],
        local_storage={"critique-theme": saved_theme},
        name=f"full_{page}_{saved_theme}.json",
    )
    assert full_result["values"]["data_theme"] == saved_theme
    expected_pressed = "true" if saved_theme == "dark" else "false"
    expected_label = "Switch to light theme" if saved_theme == "dark" else "Switch to dark theme"
    assert full_result["flags"]["theme-toggle"]["ariaPressed"] == expected_pressed
    assert full_result["flags"]["theme-toggle"]["ariaLabel"] == expected_label
    assert full_result["storage"]["local"]["critique-theme"] == saved_theme


def test_storage_exceptions_do_not_break_toggle(tmp_path):
    result = _run_harness(
        tmp_path,
        FRONTEND_DIR / "404.html",
        calls=[
            {
                "evaluate": (
                    "localStorage.getItem = function() { throw new Error('blocked'); };"
                    "localStorage.setItem = function() { throw new Error('blocked'); };"
                ),
                "as": "poison",
            },
            {"clickId": "theme-toggle"},
            {
                "evaluate": "document.documentElement.getAttribute('data-theme')",
                "as": "data_theme",
            },
        ],
        name="blocked_storage.json",
    )
    assert result["values"]["data_theme"] == "dark"
    assert result["flags"]["theme-toggle"]["ariaPressed"] == "true"
