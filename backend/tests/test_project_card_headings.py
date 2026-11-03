"""Project cards remain discoverable through heading navigation."""
from html.parser import HTMLParser
import shutil

import pytest

from tests.test_project_share import HOMEPAGE_URL, MY_PROJECTS_URL, run

pytestmark = [pytest.mark.frontend_render, pytest.mark.skipif(
    shutil.which("node") is None, reason="node is required for rendering")]


class CardHeadings(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cards = []
        self.active = False

    def handle_starttag(self, tag, attrs):
        self.active = "project-title" in dict(attrs).get("class", "").split()
        if self.active:
            self.cards.append([tag, ""])

    def handle_data(self, data):
        if self.active:
            self.cards[-1][1] += data

    def handle_endtag(self, tag):
        self.active = False


@pytest.mark.parametrize("page,url,container,level", [
    ("index.html", HOMEPAGE_URL, "homepage-projects", "h3"),
    ("my_projects.html", MY_PROJECTS_URL, "content", "h2"),
])
def test_rendered_cards_have_sequential_headings(tmp_path, page, url, container, level):
    projects = [{"id": i, "title": title, "response_count": 0}
                for i, title in enumerate(["First <project>", "Second & project"], 1)]
    body = {"items": projects, "total": 2} if page == "index.html" else projects
    loader = "loadHomepageProjects" if page == "index.html" else "loadProjects"
    result = run(tmp_path, page, [{"fn": loader, "args": []}],
                 fetch={url: {"status": 200, "body": body}})
    parser = CardHeadings()
    parser.feed(result["ids"][container])
    assert parser.cards == [[level, project["title"]] for project in projects]
