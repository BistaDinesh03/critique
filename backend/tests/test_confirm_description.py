"""Confirmation dialogs describe the full consequence, including on reuse."""
import shutil
import pytest
from tests.test_project_share import run

pytestmark = [pytest.mark.frontend_render, pytest.mark.skipif(
    shutil.which('node') is None, reason='node is required for rendering')]


def test_confirmation_description_survives_reopening(tmp_path):
    result = run(tmp_path, 'my_projects.html', [{'evaluate': """
var descriptions = [], ids = [];
for (var i = 0; i < 2; i++) {
 var opened = CritiqueUI.showConfirmModal({title: 'Delete project?', message: 'Permanently delete Project ' + i + ' and all feedback.'});
 var backdrop = document.body.children[document.body.children.length - 1];
 var dialog = backdrop.children[0];
 var body = dialog.children[1];
 ids.push(body.id);
 descriptions.push([dialog.getAttribute('aria-describedby'), body.id, body.textContent, dialog.getAttribute('aria-labelledby')]);
 opened.close();
}
({descriptions: descriptions, unique: new Set(ids).size})
""", 'as': 'dialogs'}])
    observed = result['values']['dialogs']
    assert observed['unique'] == 2
    for i, (reference, identifier, text, label) in enumerate(observed['descriptions']):
        assert reference == identifier
        assert text == f'Permanently delete Project {i} and all feedback.'
        assert label == 'modal-title'
