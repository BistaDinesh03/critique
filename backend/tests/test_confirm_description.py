"""Each confirmation dialog references its own title and description."""

import shutil

import pytest

from tests.test_project_share import run

pytestmark = [
    pytest.mark.frontend_render,
    pytest.mark.skipif(shutil.which("node") is None, reason="node is required for rendering"),
]


def test_concurrent_dialogs_reference_their_own_content(tmp_path):
    result = run(tmp_path, "my_projects.html", [{
        "as": "dialogs",
        "evaluate": """
var first = CritiqueUI.showConfirmModal({title: 'Delete Alpha?', message: 'Remove Alpha and its feedback.'});
var second = CritiqueUI.showConfirmModal({title: 'Delete Beta?', message: 'Remove Beta and its feedback.'});
var dialogs = Array.from(document.body.children).slice(-2).map(function(backdrop) {
    var dialog = backdrop.children[0];
    var title = dialog.children[0];
    var description = dialog.children[1];
    return {
        titleId: title.id,
        descriptionId: description.id,
        titleRef: dialog.getAttribute('aria-labelledby'),
        descriptionRef: dialog.getAttribute('aria-describedby'),
        title: title.textContent,
        description: description.textContent
    };
});
second.close();
first.close();
dialogs;
""",
    }])
    first, second = result["values"]["dialogs"]
    assert first["titleId"] != second["titleId"]
    assert first["descriptionId"] != second["descriptionId"]
    for dialog, project in [(first, "Alpha"), (second, "Beta")]:
        assert dialog["titleRef"] == dialog["titleId"]
        assert dialog["descriptionRef"] == dialog["descriptionId"]
        assert dialog["title"] == f"Delete {project}?"
        assert dialog["description"] == f"Remove {project} and its feedback."
