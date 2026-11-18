# Frontend Render Test Harness

Critique tests frontend pages with
[`backend/tests/frontend_render_harness.js`](../backend/tests/frontend_render_harness.js).
It is a Node.js DOM harness invoked by Python (`pytest`). It executes a page's
real inline scripts and local `/static/*.js` scripts in a small DOM-like VM,
then returns the markup and browser state produced by the scenario.

Use this harness to test rendering, loading states, form behavior, fetch
calls, and accessibility attributes. Use the Playwright suite in
[`visual-regression.md`](visual-regression.md) for screenshots and responsive
visual layout.

## Run the tests

Node.js must be on `PATH`. CI uses Node.js 20; Node.js 18 or newer is a
reasonable local baseline.

From the repository root:

```bash
node --version
cd backend
GITHUB_CLIENT_ID=ci-test-client-id python -m pytest tests/ -m frontend_render -q
```

On Windows PowerShell:

```powershell
node --version
cd backend
$env:GITHUB_CLIENT_ID = "ci-test-client-id"
python -m pytest tests/ -m frontend_render -q
```

Run one module or test when iterating:

```bash
python -m pytest tests/test_loading_ux.py -q
python -m pytest tests/test_loading_ux.py::test_discover_skeleton_resolves_to_real_project_cards -q
```

Frontend render test modules declare `pytest.mark.frontend_render` and skip
locally when `node` is missing. CI does not allow those tests to skip silently.
When adding a module, copy the marker block from
[`CONTRIBUTING.md`](../CONTRIBUTING.md).

## Scenario JSON

The harness reads one scenario file:

```bash
node backend/tests/frontend_render_harness.js /tmp/scenario.json
```

The scenario fields used by the existing tests are:

| Field | Purpose |
|---|---|
| `page` | Absolute or repository-relative path to the HTML page. Use `Path(...).as_posix()` in Python. |
| `calls` | Ordered actions to run after the page scripts initialize. |
| `fetch` | Mock API routes and response specifications. |
| `location` | The simulated pathname and optional query string, such as `/project/1` or `/?auth=cancelled`. |
| `read` | Choose `{"byId": "content"}` or `{"created": true}` for the `html` output field. |

Typical structure:

```json
{
  "page": "/absolute/path/to/frontend/discover.html",
  "calls": [
    {"fn": "loadProjects", "args": [1]}
  ],
  "fetch": {
    "/api/projects/?": {
      "status": 200,
      "body": {
        "items": [],
        "total": 0,
        "page": 1,
        "total_pages": 1
      }
    }
  },
  "location": "/discover",
  "read": {"byId": "project-list"}
}
```

## Mock fetches and network behavior

Keys in `fetch` are matched as substrings of the requested URL. Existing tests
keep specific routes before a shorter route that could swallow them.

```json
{
  "/api/projects/1/responses": {
    "status": 201,
    "body": {}
  },
  "/api/projects/1": {
    "status": 200,
    "body": {"project": {"id": 1}, "question": {"id": 1}}
  }
}
```

A route can return a list of response specifications. The harness consumes
each response until the last one remains.

```json
{
  "/api/projects/1/responses": [
    {"status": 201, "body": {}},
    {"status": 409, "body": {"detail": "Already responded"}}
  ]
}
```

Use `networkError: true` to reject a fetch, optionally with a custom
`message`. Use `pending: true` to leave a request unresolved and inspect the
sending state. An unspecified route defaults to `{status: 404, body: {}}`.

The harness records every request in `result["requests"]`, including `url`,
`method`, and `body`.

## Calls, DOM reads, and assertions

`calls` is ordered and executed after the harness waits for initial page work.
Supported actions in the implementation include:

- `{"fn": "functionName", "args": [value]}`
- `{"evaluate": "expression", "as": "name"}`
- `{"checkInput": {"name": "clarity", "value": "very_clear"}}`
- `{"setValuePlaceholder": {"placeholder": "you@example.com", "value": "builder@example.com"}}`
- `{"submitId": "response-form"}` or `{"submitCreatedContaining": "Button text"}`
- `{"clickId": "share-toggle"}` or `{"clickCreatedContaining": "Try again"}`
- `{"dispatchDocumentClickId": "menu"}` or `{"dispatchDocumentClickCreated": "Sign out"}`
- `{"dispatchKeydown": "Escape"}` or `{"dispatchKeydown": {"key": "Escape"}}`

The harness returns these fields:

| Field | Use |
|---|---|
| `errors` | JavaScript exceptions; tests should assert this is empty. |
| `html` | Markup selected by `read.byId` or `read.created`. |
| `created` | Markup for attached elements created during the scenario. |
| `createdMeta` | Attached element metadata: `tag`, `id`, `className`, `href`, `text`, form state, and ARIA attributes. |
| `ids` | The inner HTML for elements keyed by ID. |
| `flags` | Visibility and ARIA state keyed by element ID. |
| `requests` | Fetch URL, method, and body. |
| `storage` | `session` and `local` storage snapshots. |
| `values` | Values returned by `evaluate` calls. |
| `focused` | The element last moved to with `focus()`. |
| `clipboard` | Clipboard text writes. |
| `opened` | Popups opened through `window.open()`. |

## Complete example: successful discover rendering

This pattern is adapted from `backend/tests/test_loading_ux.py`:

```python
import json
import shutil
import subprocess
from pathlib import Path

import pytest

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
HARNESS = Path(__file__).resolve().parent / "frontend_render_harness.js"

pytestmark = [
    pytest.mark.frontend_render,
    pytest.mark.skipif(
        shutil.which("node") is None,
        reason="node is required to run the frontend rendering harness",
    ),
]


def run_harness(tmp_path):
    project = {
        "id": 7,
        "title": "Ship the thing",
        "description": "A short description",
        "question_text": "Is the pricing clear?",
        "response_count": 2,
        "image_url": None,
    }
    scenario = {
        "page": (FRONTEND_DIR / "discover.html").as_posix(),
        "calls": [{"fn": "loadProjects", "args": [1]}],
        "fetch": {
            "/api/projects/": {
                "status": 200,
                "body": {"items": [project], "total": 1, "page": 1, "total_pages": 1},
            }
        },
        "location": "/discover",
        "read": {"created": True},
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
    return result


def test_discover_renders_project_and_clears_busy_state(tmp_path):
    result = run_harness(tmp_path)

    assert "Ship the thing" in result["html"]
    assert any(meta["className"] == "project-card" for meta in result["createdMeta"])
    assert result["flags"]["project-list"]["ariaBusy"] == "false"
    assert result["flags"]["project-list"]["role"] == "list"
    assert result["flags"]["project-list"]["ariaLabel"] == "Projects asking for feedback"
```

## Complete example: submit a feedback form

This pattern is adapted from `backend/tests/test_disable_response_form.py`.
It selects radio inputs, submits the hydrated form, and verifies browser-like
control state after a successful response.

```python
import json
import shutil
import subprocess
from pathlib import Path

import pytest

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
HARNESS = Path(__file__).resolve().parent / "frontend_render_harness.js"

pytestmark = [
    pytest.mark.frontend_render,
    pytest.mark.skipif(
        shutil.which("node") is None,
        reason="node is required to run the frontend rendering harness",
    ),
]


def test_feedback_form_disables_controls_after_success(tmp_path):
    project = {
        "project": {
            "id": 1,
            "title": "Sentry bot",
            "description": "Watches your logs",
            "image_url": None,
            "url": None,
            "response_count": 3,
        },
        "question": {
            "id": 1,
            "text": "Is the alerting clear enough?",
            "is_active": True,
            "project_id": 1,
        },
    }
    scenario = {
        "page": (FRONTEND_DIR / "project_detail.html").as_posix(),
        "calls": [
            {"checkInput": {"name": "clarity", "value": "very_clear"}},
            {"checkInput": {"name": "would_use", "value": "yes"}},
            {"submitId": "response-form"},
            {
                "evaluate": (
                    "document.getElementById('response-form')"
                    ".querySelectorAll('input, textarea, button').length"
                ),
                "as": "controls_found",
            },
            {
                "evaluate": "document.getElementById('submit-btn').disabled",
                "as": "submit_disabled",
            },
        ],
        "fetch": {
            "/api/projects/1/responses": {"status": 201, "body": {}},
            "/api/projects/1": {"status": 200, "body": project},
        },
        "location": "/project/1",
        "read": {"created": True},
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

    assert result["errors"] == []
    assert result["values"]["controls_found"] >= 8
    assert result["values"]["submit_disabled"] is True
    assert any(
        request["method"] == "POST"
        and request["url"] == "/api/projects/1/responses"
        for request in result["requests"]
    )
```
