"""Meta-test ensuring all modules using frontend_render_harness.js carry the frontend_render marker.

Issues #132 and #142 hardened CI so that if Node.js is missing on PATH during CI runs,
tests needing frontend render harness are not silently skipped without error.
Issue #154 added this self-policing test to ensure no module forgets `pytestmark = [pytest.mark.frontend_render, ...]`,
which would prevent `backend/tests/conftest.py:pytest_collection_modifyitems` from protecting it.
"""

import ast
from pathlib import Path


def _module_has_frontend_render_marker(source: str, filename: str) -> bool:
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError:
        return False

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "pytestmark":
                    val_str = ast.unparse(node.value)
                    if "frontend_render" in val_str:
                        return True
    return False


def test_every_frontend_render_harness_module_has_marker():
    """Any test module referencing frontend_render_harness.js must include
    pytest.mark.frontend_render in its pytestmark.
    """
    tests_dir = Path(__file__).resolve().parent
    offending_files = []

    for test_file in sorted(tests_dir.glob("test_*.py")):
        if test_file.name == Path(__file__).name:
            continue

        source = test_file.read_text(encoding="utf-8")
        if "frontend_render_harness.js" in source:
            if not _module_has_frontend_render_marker(source, str(test_file)):
                offending_files.append(test_file.name)

    assert not offending_files, (
        f"The following test module(s) reference 'frontend_render_harness.js' "
        f"but do not declare 'pytest.mark.frontend_render' in their 'pytestmark':\n"
        + "\n".join(f"  - {f}" for f in offending_files)
        + "\n\nPlease add the following to each offending module:\n"
        "    pytestmark = [\n"
        "        pytest.mark.frontend_render,\n"
        "        pytest.mark.skipif(shutil.which('node') is None, reason='node is required for rendering'),\n"
        "    ]"
    )
