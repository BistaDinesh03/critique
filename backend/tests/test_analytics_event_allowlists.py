import ast
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

# Directories holding the client-side analytics call sites.
FRONTEND_DIRS = ("frontend", "static")

# trackEvent / trackAuthEvent take the event name as their first argument.
# static/share.js wraps them in a local track() helper, so it is included too —
# otherwise every share_* call site would slip past this check.
TRACK_CALL = re.compile(
    r"\b(?:trackEvent|trackAuthEvent|track)\s*\(\s*(['\"])([a-z0-9_]+)\1"
)


def _backend_events():
    """Read the server-side allowlist straight out of the route module."""
    backend_source = (ROOT / "backend/app/routes_analytics.py").read_text(
        encoding="utf-8-sig")
    events_assignment = next(
        (
            node.value
            for node in ast.parse(backend_source).body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "VALID_EVENTS" for target in node.targets)
        ),
        None,
    )
    assert events_assignment is not None, "Backend VALID_EVENTS declaration is missing"
    return set(ast.literal_eval(events_assignment))


def _frontend_events():
    """Read the client-side allowlist out of static/analytics.js."""
    frontend_source = (ROOT / "static/analytics.js").read_text(encoding="utf-8-sig")
    match = re.search(r"\b(?:const|let|var)\s+VALID_EVENTS\s*=\s*\[([^\]]*)\]", frontend_source)
    assert match is not None, "Frontend VALID_EVENTS declaration is missing"
    return set(re.findall(r"['\"]([a-z0-9_]+)['\"]", match.group(1)))


def _fired_events():
    """
    Map every literal event name actually fired by the client to where it fires

    Event names built at runtime (``trackPageView`` picks page_view /
    discover_view / project_view from the current URL) are not literals at the
    call site and cannot be recovered here; everything written as a string
    literal can, and that is the case this check exists for.
    """
    fired = defaultdict(list)
    for directory in FRONTEND_DIRS:
        for path in sorted((ROOT / directory).rglob("*")):
            if path.suffix not in (".js", ".html"):
                continue
            source = path.read_text(encoding="utf-8-sig", errors="replace")
            for match in TRACK_CALL.finditer(source):
                line = source[:match.start()].count("\n") + 1
                fired[match.group(2)].append(f"{path.relative_to(ROOT).as_posix()}:{line}")
    return fired


def test_frontend_and_backend_analytics_events_match():
    backend_events = _backend_events()
    frontend_events = _frontend_events()

    assert backend_events == frontend_events, (
        f"Backend-only analytics events: {sorted(backend_events - frontend_events)}; "
        f"frontend-only analytics events: {sorted(frontend_events - backend_events)}"
    )


def test_fired_events_are_in_the_backend_allowlist():
    """
    Regression test for the direction the list comparison cannot see

    A list-vs-list test passes when both lists agree to omit a name, so a call
    site firing an event nobody allowlisted went unnoticed and every such event
    was dropped twice: once by the client guard (the request never leaves the
    browser) and once by the server with a 400. Comparing against what the
    client actually fires is what catches it.
    """
    backend_events = _backend_events()
    fired = _fired_events()

    assert fired, "No analytics call site found - the scanner is broken, not the code"

    invalid = sorted(name for name in fired if name not in backend_events)
    assert not invalid, (
        "These events are fired by the client but absent from the server "
        "allowlist (backend/app/routes_analytics.py VALID_EVENTS), so they are "
        "discarded instead of recorded: "
        + "; ".join(f"{name} at {', '.join(fired[name])}" for name in invalid)
    )
