"""Live-region semantics from real delete callbacks and the shared toast helper."""
import shutil
import pytest
from tests.test_project_share import run

pytestmark = [pytest.mark.frontend_render, pytest.mark.skipif(shutil.which('node') is None, reason='node is required for rendering')]

# Missing IDs are normally fabricated by the harness. Exercise real creation.
SETUP = {'evaluate': """
var originalTimer = setTimeout; var toastDelays = [];
setTimeout = function(fn, ms) { if (ms >= 200) { toastDelays.push(ms); return 0; } return originalTimer(fn, ms); };
var originalGet = document.getElementById.bind(document);
document.getElementById = function(id) {
 if (id === 'toast-container') return document.body.children.find(function(el) { return el.id === id; }) || null;
 return originalGet(id);
};
CritiqueUI.showConfirmModal = function(options) { options.onConfirm(function(){}, function(){}); };
true
"""}
READ = {'evaluate': "document.getElementById('toast-container').getAttribute('aria-live')", 'as': 'containerLive'}

@pytest.mark.parametrize('status,role,message', [(500, 'alert', 'Could not delete. Try again.'), (204, 'status', 'Project deleted')])
def test_delete_toast_announcement(tmp_path, status, role, message):
    result = run(tmp_path, 'my_projects.html', [SETUP, {'fn': 'deleteProject', 'args': [7, None]}, {'evaluate': 'new Promise(function(resolve){ setTimeout(resolve, 0); })'}, READ], fetch={'/api/projects/7': {'status': status}, '/api/projects/my/list': {'json': []}})
    toasts = [item for item in result['createdMeta'] if item.get('className', '').startswith('toast toast-')]
    assert len(toasts) == 1
    assert toasts[0]['role'] == role
    assert result['values']['containerLive'] is None
    assert any(item.get('text') == message for item in result['createdMeta'])

def test_info_toast_remains_status(tmp_path):
    result = run(tmp_path, 'my_projects.html', [SETUP, {'fn': 'CritiqueUI.showToast', 'args': ['Information', 'info']}, READ])
    toasts = [item for item in result['createdMeta'] if item.get('className') == 'toast toast-info']
    assert len(toasts) == 1
    assert toasts[0]['role'] == 'status'
    assert result['values']['containerLive'] is None
