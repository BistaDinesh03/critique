"""Every served page has a keyboard-reachable bypass to its main landmark."""
from html.parser import HTMLParser
from pathlib import Path

import pytest


class PageNavigation(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_body = False
        self.elements = []

    def handle_starttag(self, tag, attrs):
        if tag == "body":
            self.in_body = True
        elif self.in_body:
            self.elements.append((tag, dict(attrs)))


@pytest.mark.parametrize("page", sorted(
    (Path(__file__).resolve().parents[2] / "frontend").glob("*.html")
), ids=lambda path: path.name)
def test_first_body_element_skips_to_focusable_main(page):
    parser = PageNavigation()
    parser.feed(page.read_text(encoding="utf-8"))
    tag, link = parser.elements[0]
    assert tag == "a"
    assert link["href"] == "#main-content"
    assert "skip-link" in link["class"].split()
    assert "tabindex" not in link  # Native link remains in normal tab order.
    targets = [(tag, attrs) for tag, attrs in parser.elements
               if attrs.get("id") == "main-content"]
    assert len(targets) == 1
    tag, target = targets[0]
    assert tag == "main"
    assert target["tabindex"] == "-1"  # Can receive fragment focus, not an extra tab stop.
