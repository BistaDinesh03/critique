"""Exercise page-view classification through the real analytics JavaScript."""

import json
import shutil
import subprocess
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

ANALYTICS_JS = Path(__file__).resolve().parents[2] / "static" / "analytics.js"

pytestmark = [
    pytest.mark.frontend_render,
    pytest.mark.skipif(
        shutil.which("node") is None,
        reason="node is required to run the frontend rendering harness",
    ),
]

HARNESS = """
const fs = require('node:fs');
const vm = require('node:vm');
const requests = [];
const sandbox = {
    window: { location: new URL(process.argv[2], 'https://example.com') },
    fetch(url, options) {
        requests.push({ url, options });
        return Promise.resolve();
    },
};
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);
const analytics = sandbox.window.CritiqueAnalytics;
analytics.trackPageView();
process.stdout.write(JSON.stringify({ projectId: analytics.getProjectId(), requests }));
"""


@pytest.mark.parametrize(
    ("location", "event_name", "project_id"),
    [
        ("/project/7", "project_view", 7),
        ("/project/7/", "project_view", 7),
        ("/project/7?ref=discover#feedback", "project_view", 7),
        ("/project/7/#feedback", "project_view", 7),
        ("/project/7/results", "page_view", None),
        ("/project/7/results?ref=owner#responses", "page_view", None),
        ("/project/7/results/", "page_view", None),
        ("/project/7/edit", "page_view", None),
        ("/unrelated/project/7", "page_view", None),
        ("/project/7extra", "page_view", None),
        ("/project/not-a-number", "page_view", None),
        ("/", "page_view", None),
        ("/discover?sort=new#projects", "discover_view", None),
    ],
)
def test_page_view_request(location, event_name, project_id):
    proc = subprocess.run(
        ["node", "-e", HARNESS, str(ANALYTICS_JS), location],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert proc.returncode == 0, f"analytics harness crashed:\n{proc.stderr}"
    result = json.loads(proc.stdout)
    assert len(result["requests"]) == 1
    request = result["requests"][0]
    url = urlsplit(request["url"])
    assert url.path == "/api/analytics/track"
    expected_query = {"event_name": [event_name]}
    if project_id is not None:
        expected_query["project_id"] = [str(project_id)]
    assert parse_qs(url.query) == expected_query
    assert request["options"] == {"method": "POST", "credentials": "same-origin"}
    assert result["projectId"] == project_id
