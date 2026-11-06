"""Unsaved changes warning tests for project submission form."""
from pathlib import Path


def test_index_html_has_beforeunload_warning_for_unsaved_project_changes():
    html_path = Path(__file__).resolve().parents[2] / 'frontend' / 'index.html'
    html = html_path.read_text(encoding='utf-8')

    assert 'projectFormDirty' in html
    assert 'beforeunload' in html
    assert "pForm.addEventListener('input', updateProjectFormDirty)" in html or 'addEventListener("input", updateProjectFormDirty)' in html or 'updateProjectFormDirty' in html
    assert 'clearProjectDraft' in html
