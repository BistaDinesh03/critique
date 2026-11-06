import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_frontend_and_backend_analytics_events_match():
    backend_source = (ROOT / "backend/app/routes_analytics.py").read_text(
        encoding="utf-8-sig"
    )

    events_assignment = next(
        (
            node.value
            for node in ast.parse(backend_source).body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "VALID_EVENTS"
                for target in node.targets
            )
        ),
        None,
    )

    assert events_assignment is not None, "Backend VALID_EVENTS declaration is missing"

    backend_events = set(ast.literal_eval(events_assignment))

    frontend_file = ROOT / "static/analytics_events.js"
    frontend_source = frontend_file.read_text(encoding="utf-8")

    expected_content = (
        "window.CRITIQUE_VALID_ANALYTICS_EVENTS = "
        + json.dumps(sorted(backend_events), indent=4)
        + ";\n"
    )

    assert frontend_source == expected_content, (
        "Generated frontend analytics events do not match backend VALID_EVENTS"
    )