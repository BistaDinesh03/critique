# Frontend Render Test Harness

Critique uses a dedicated Node.js-based rendering harness located at [`backend/tests/frontend_render_harness.js`](../backend/tests/frontend_render_harness.js) to test frontend user interface code, loading states, accessibility attributes, and DOM mutations directly from Python (`pytest`).

---

## 1. Why the Harness Exists

Frontend pages in Critique (`frontend/*.html`) declare vanilla JavaScript and shared scripts (`/static/ui.js`, `/static/share.js`). Instead of spinning up heavy headless browsers (like full Playwright/Puppeteer instances) for every component test or relying on mocked helper functions that don't reflect browser behavior, the harness:

- Executes the page's actual `<script>` tags inside a deterministic Node.js VM context with a lightweight DOM stub.
- Accurately captures real DOM assignments (`innerHTML`, text node escaping, attached elements).
- Allows `pytest` test suites to assert against true browser-rendered DOM output, reflected attributes, accessibility roles (`aria-busy`, `role`, `aria-live`), and network requests.

---

## 2. Invocation & Scenario Specification

The harness is invoked by pytest via Node:

```bash
node backend/tests/frontend_render_harness.js <scenario.json>
```

A scenario JSON specifies the target page, mocked fetch responses, browser location, and actions to execute:

```json
{
  "page": "frontend/discover.html",
  "calls": [
    { "fn": "loadProjects", "args": [1] },
    { "clickCreatedContaining": "Try again" },
    { "checkInput": { "name": "clarity", "value": "very_clear" } },
    { "submitId": "response-form" },
    { "evaluate": "formatAge('2026-09-24T10:00:00Z')", "as": "age" }
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
  "read": { "byId": "project-list" }
}
```

---

## 3. Harness Output Structure

The harness executes the scenario and writes a single structured JSON payload to `stdout`:

| Field | Description |
|---|---|
| `errors` | Array of uncaught JavaScript exceptions during execution. |
| `html` | The serialized HTML markup of the target element. |
| `created` | Text content of all nodes appended to the DOM. |
| `createdMeta` | Reflected properties (`href`, `type`, `name`, `className`, `text`) of attached elements. |
| `flags` | Map of element IDs to computed attributes (`ariaBusy`, `role`, `ariaLabel`, visibility). |
| `requests` | List of all HTTP `fetch()` calls issued during the run. |
| `storage` | Snapshot of `localStorage` and `sessionStorage`. |
| `ids` | Content map indexed by DOM element IDs. |
| `values` | Values of form inputs. |
| `focused` | ID or descriptor of the currently focused element. |

---

## 4. Python Pytest Integration

Tests in `backend/tests/` (such as `test_loading_ux.py`, `test_discover_freshness.py`, and `test_delete_dialog_ui.py`) wrap the harness using a Python helper function:

```python
from backend.tests.test_loading_ux import run

def test_discover_shows_empty_state(tmp_path):
    result = run(
        tmp_path,
        "discover.html",
        [{"fn": "loadProjects", "args": [1]}],
        fetch={
            "/api/projects/": {
                "status": 200,
                "body": {"items": [], "total": 0, "page": 1, "total_pages": 1},
            }
        },
    )
    assert "empty-state" in result["ids"]["project-list"]
    assert result["flags"]["project-list"]["ariaBusy"] == "false"
```

---

## 5. Running Harness Tests Locally

Prerequisite: Ensure `node` is available on your `$PATH`.

Run all frontend rendering tests:
```bash
pytest -m frontend_render
```

Run specific loading UX or UI behavioral suites:
```bash
pytest backend/tests/test_loading_ux.py
pytest backend/tests/test_delete_dialog_ui.py
```
