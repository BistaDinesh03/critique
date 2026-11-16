"""Behavioral tests for the project delete confirmation dialog (Issue #201)."""

import shutil
from pathlib import Path

import pytest
from tests.test_project_share import run

pytestmark = [
    pytest.mark.frontend_render,
    pytest.mark.skipif(
        shutil.which("node") is None,
        reason="node is required to run the frontend rendering harness",
    ),
]

CONFIRM_CLICK = {
    "evaluate": """
        var backdrop = document.body.children.find(function(c) { return c.className === 'modal-backdrop'; });
        var confirmBtn = backdrop ? backdrop.children[0].children[2].children[1] : null;
        var handler = confirmBtn ? confirmBtn.handlers.find(function(h) { return h.type === 'click'; }) : null;
        if (handler) handler.fn({});
        'confirmed'
    """,
    "as": "confirmed",
}

WAIT_TICK = {
    "evaluate": "new Promise(function(resolve){ setTimeout(resolve, 0); })",
    "as": "waited",
}

SPY_FETCH = {
    "evaluate": """
        var captured = [];
        var origFetch = fetch;
        fetch = function(url, opts) {
            captured.push({url: url, options: opts});
            return origFetch(url, opts);
        };
        window.__capturedFetch = captured;
        'spied'
    """,
    "as": "spied",
}


def test_delete_dialog_cancel_issues_no_delete(tmp_path):
    """Scenario 1: Clicking Cancel must not issue any DELETE request, and closes modal."""
    fetch = {
        "/api/projects/my/list": {"status": 200, "body": {"projects": [{"id": 1, "title": "Test Project"}]}},
        "/auth/check": {"status": 200, "body": {"logged_in": True, "user": {"id": 1, "username": "tester"}}},
    }
    calls = [
        {"fn": "deleteProject", "args": [1, None]},
        {"clickCreatedContaining": "Cancel"},
        {
            "evaluate": "document.body.children.some(function(c) { return c.className === 'modal-backdrop'; })",
            "as": "hasBackdrop",
        },
    ]
    result = run(tmp_path, "my_projects.html", calls, fetch=fetch)
    assert result["errors"] == []
    assert not any(r.get("method") == "DELETE" for r in result["requests"])
    assert result["values"]["hasBackdrop"] is False


def test_delete_dialog_confirm_issues_delete_with_csrf_token(tmp_path):
    """Scenario 2: Confirming must issue exactly one DELETE to /api/projects/{id} with X-CSRF-Token."""
    fetch = {
        "/api/projects/my/list": {"status": 200, "body": {"projects": [{"id": 42, "title": "To Delete"}]}},
        "/api/projects/42": {"status": 204, "body": ""},
        "/auth/check": {"status": 200, "body": {"logged_in": True, "user": {"id": 1, "username": "tester"}}},
    }
    calls = [
        SPY_FETCH,
        {"fn": "deleteProject", "args": [42, None]},
        CONFIRM_CLICK,
        WAIT_TICK,
        {"evaluate": "window.__capturedFetch", "as": "capturedFetches"},
    ]
    result = run(tmp_path, "my_projects.html", calls, fetch=fetch)
    assert result["errors"] == []

    delete_reqs = [r for r in result["requests"] if r.get("method") == "DELETE"]
    assert len(delete_reqs) == 1
    assert delete_reqs[0]["url"] == "/api/projects/42"

    captured = result["values"]["capturedFetches"]
    captured_deletes = [f for f in captured if f.get("options", {}).get("method") == "DELETE"]
    assert len(captured_deletes) == 1
    assert captured_deletes[0]["url"] == "/api/projects/42"
    headers = captured_deletes[0]["options"].get("headers", {})
    assert "X-CSRF-Token" in headers
    assert headers["X-CSRF-Token"] == "test-token"


def test_delete_dialog_failed_delete_reenables_button_and_restores_label(tmp_path):
    """Scenario 3: A failed DELETE must re-enable the button and restore its label ('Delete')."""
    fetch = {
        "/api/projects/my/list": {"status": 200, "body": {"projects": [{"id": 1, "title": "Test Project"}]}},
        "/api/projects/1": {"status": 500, "body": {"detail": "Database error"}},
        "/auth/check": {"status": 200, "body": {"logged_in": True, "user": {"id": 1, "username": "tester"}}},
    }
    calls = [
        {"fn": "deleteProject", "args": [1, None]},
        CONFIRM_CLICK,
        WAIT_TICK,
        {
            "evaluate": """
                var backdrop = document.body.children.find(function(c) { return c.className === 'modal-backdrop'; });
                var confirmBtn = backdrop ? backdrop.children[0].children[2].children[1] : null;
                ({
                    hasBackdrop: !!backdrop,
                    disabled: confirmBtn ? confirmBtn.disabled : null,
                    text: confirmBtn ? confirmBtn.textContent : null
                })
            """,
            "as": "btnState",
        },
    ]
    result = run(tmp_path, "my_projects.html", calls, fetch=fetch)
    assert result["errors"] == []
    btn_state = result["values"]["btnState"]
    assert btn_state["hasBackdrop"] is True
    assert btn_state["disabled"] is False
    assert btn_state["text"] == "Delete"


def test_delete_dialog_success_detaches_modal_and_refreshes_list(tmp_path):
    """Scenario 4: Successful DELETE must close the modal (backdrop detached) and refresh project list."""
    fetch = {
        "/api/projects/my/list": {"status": 200, "body": {"projects": []}},
        "/api/projects/99": {"status": 204, "body": ""},
        "/auth/check": {"status": 200, "body": {"logged_in": True, "user": {"id": 1, "username": "tester"}}},
    }
    calls = [
        {"fn": "deleteProject", "args": [99, None]},
        CONFIRM_CLICK,
        WAIT_TICK,
        {
            "evaluate": "document.body.children.some(function(c) { return c.className === 'modal-backdrop'; })",
            "as": "hasBackdrop",
        },
    ]
    result = run(tmp_path, "my_projects.html", calls, fetch=fetch)
    assert result["errors"] == []
    assert result["values"]["hasBackdrop"] is False
    get_reqs = [r for r in result["requests"] if r.get("method") == "GET" and "/api/projects/my/list" in r.get("url")]
    assert len(get_reqs) >= 1
