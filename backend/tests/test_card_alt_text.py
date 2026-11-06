import json
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path
import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent
FRONTEND_DIR = REPO_DIR / "frontend"
HARNESS = Path(__file__).resolve().parent / "frontend_render_harness.js"

pytestmark = [
    pytest.mark.frontend_render,
    pytest.mark.skipif(
        shutil.which("node") is None,
        reason="node is required to run the frontend rendering harness",
    ),
]


class ParsedHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, attrs))

    def handle_startendtag(self, tag, attrs):
        self.tags.append((tag, attrs))


def render(tmp_path, page, calls, read, fetch=None, location="/"):
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
    return result["html"]


def test_discover_card_image_alt_text(tmp_path):
    project = {
        "id": 1,
        "title": "Akiya Scout",
        "description": "Find abandoned homes in Japan.",
        "question_text": "Is the map easy to understand?",
        "image_url": "https://example.com/scout.png",
        "response_count": 3,
    }
    html = render(
        tmp_path,
        "discover.html",
        [{"fn": "showProjects", "args": [[project]]}],
        {"created": True},
    )
    parser = ParsedHTML()
    parser.feed(html)
    img_tag = next((attrs for tag, attrs in parser.tags if tag == "img" and any(k == "class" and "project-screenshot" in v for k, v in attrs)), None)
    assert img_tag is not None
    attrs_dict = dict(img_tag)
    assert attrs_dict.get("alt") == "Screenshot of Akiya Scout"
