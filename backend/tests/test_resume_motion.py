"""Both authentication resume flows respect motion preferences and safe fallbacks."""
import shutil

import pytest

from tests.test_project_share import run

pytestmark = [pytest.mark.frontend_render, pytest.mark.skipif(
    shutil.which("node") is None, reason="node is required for rendering")]


@pytest.mark.parametrize("page,form,resume,callback", [
    ("index.html", "submit", "project_submit", "maybeResumeToSubmit"),
    ("project_detail.html", "response-form", "feedback", "maybeResumeToFeedback"),
])
@pytest.mark.parametrize("media,expected", [
    ("function() { return {matches: true}; }", "auto"),
    ("function() { return {matches: false}; }", "smooth"),
    ("undefined", "smooth"),
    ("42", "smooth"),
    ("function() { throw new Error('unavailable'); }", "smooth"),
    ("function() { return null; }", "smooth"),
    ("function() { return {matches: 'true'}; }", "smooth"),
])
def test_resume_scroll_behavior(tmp_path, page, form, resume, callback, media, expected):
    result = run(tmp_path, page, [{"evaluate": f"""
window.matchMedia = {media};
window.location.search = '?resume={resume}';
var scrolls = [];
document.getElementById('{form}').scrollIntoView = function(options) {{ scrolls.push(options); }};
{callback}();
new Promise(function(resolve) {{ setTimeout(function() {{ resolve(scrolls); }}, 20); }})
""", "as": "scrolls"}])
    assert result["values"]["scrolls"] == [{"behavior": expected, "block": "start"}]
