"""Frontend rendering tests for dynamic copyright year in the site footer."""

from datetime import datetime
from html.parser import HTMLParser
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT / "frontend"
UI_JS = ROOT / "static" / "ui.js"
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


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def text(self):
        return " ".join("".join(self.parts).split())


def _footer_bottom_text(html: str) -> str:
    match = re.search(
        r'<div\s+class="footer-bottom">(.*?)</div>',
        html,
        re.DOTALL,
    )
    assert match is not None, "missing .footer-bottom block"
    parser = _TextExtractor()
    parser.feed(match.group(1))
    return parser.text()


def _run_harness(tmp_path, page: str, calls: list, name: str):
    scenario = {
        "page": (FRONTEND_DIR / page).as_posix(),
        "calls": calls,
        "fetch": {},
        "location": "/",
        "read": {"created": True},
    }
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


@pytest.mark.parametrize("page", PAGES)
def test_no_literal_hardcoded_copyright_2026_and_js_disabled_fallback(page):
    html = (FRONTEND_DIR / page).read_text(encoding="utf-8")
    assert "© 2026" not in html, f"{page} contains literal copyright 2026"
    assert "&copy; 2026" not in html, f"{page} contains literal HTML-entity copyright 2026"
    assert "/static/ui.js" in html, f"{page} must load /static/ui.js"
    assert 'class="footer-year"' in html, f"{page} missing .footer-year span"

    assert _footer_bottom_text(html) == (
        "© 2026 Critique · Open source · Free to use"
    )


@pytest.mark.parametrize("page", PAGES)
def test_runtime_populates_footer_year_from_date(tmp_path, page):
    expected_year = str(datetime.now().year)
    result = _run_harness(
        tmp_path,
        page,
        calls=[
            {
                "evaluate": (
                    "(function() {"
                    "  CritiqueUI.initFooterYear();"
                    "  var el = document.querySelector('.footer-year');"
                    "  return el ? el.textContent : null;"
                    "})()"
                ),
                "as": "current_year",
            },
            {
                "evaluate": (
                    "(function() {"
                    "  var OrigDate = Date;"
                    "  Date = function() { return { getFullYear: function() { return 2029; } }; };"
                    "  try {"
                    "    CritiqueUI.initFooterYear();"
                    "    var el = document.querySelector('.footer-year');"
                    "    return el ? el.textContent : null;"
                    "  } finally {"
                    "    Date = OrigDate;"
                    "  }"
                    "})()"
                ),
                "as": "future_year",
            },
        ],
        name=f"footer_year_{page}.json",
    )
    assert result["values"]["current_year"] == expected_year
    assert result["values"]["future_year"] == "2029"


@pytest.mark.parametrize("ready_state", ["loading", "complete"])
def test_ui_js_updates_footer_year_automatically_on_load(ready_state):
    driver = r"""
const fs = require('fs');
const vm = require('vm');
const uiPath = process.argv[1];
const readyState = process.argv[2];
const yearNode = { textContent: '2026' };
const domListeners = [];
const doc = {
  readyState,
  documentElement: { getAttribute() { return null; }, setAttribute() {} },
  body: { appendChild() {} },
  getElementById() { return null; },
  querySelectorAll(sel) { return sel === '.footer-year' ? [yearNode] : []; },
  addEventListener(type, fn) { if (type === 'DOMContentLoaded') domListeners.push(fn); },
  removeEventListener() {},
};
const win = {
  document: doc,
  location: { pathname: '/', search: '' },
  addEventListener() {},
  removeEventListener() {},
  matchMedia() { return { matches: false }; },
};
win.window = win;
const FakeDate = function() { return { getFullYear() { return 2031; } }; };
const ctx = vm.createContext({ window: win, document: doc, Date: FakeDate, console, setTimeout, clearTimeout });
vm.runInContext(fs.readFileSync(uiPath, 'utf8'), ctx);
const beforeDomReady = yearNode.textContent;
domListeners.forEach((fn) => fn());
const afterDomReady = yearNode.textContent;
process.stdout.write(JSON.stringify({ beforeDomReady, afterDomReady }));
"""
    proc = subprocess.run(
        ["node", "-e", driver, str(UI_JS), ready_state],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    if ready_state == "loading":
        assert data["beforeDomReady"] == "2026"
        assert data["afterDomReady"] == "2031"
    else:
        assert data["beforeDomReady"] == "2031"
        assert data["afterDomReady"] == "2031"
