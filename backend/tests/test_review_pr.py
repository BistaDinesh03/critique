"""Tests for the pull-request review tool: scripts/review_pr.py.

Every GitHub call is replaced by a fake, so nothing here can touch a real
pull request, post a real comment, or merge anything. The merge path is
exercised end to end through ``main()`` with an injected client, which is the
only way to prove the gate refuses when it should.

The tool itself lives outside the package, so it is put on ``sys.path``
before import -- the same thing the maintainer does by running it as a
script.
"""

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import review_pr  # noqa: E402


# ---------------------------------------------------------------------------
# Fakes and fixtures
# ---------------------------------------------------------------------------

class FakeGitHub:
    """Stands in for the gh CLI. Records everything it is asked to do."""

    def __init__(self, pr, diff="", reviews=None, comments=None,
                 protection=None, repo=None, review_api_ok=True):
        self._pr = pr
        self._diff = diff
        self._reviews = list(reviews or [])
        self._comments = list(comments or [])
        self._protection = protection
        self._review_api_ok = review_api_ok

        self.repo = (repo or {}).get("name", "BistaDinesh03/critique")
        self.user = "maintainer"

        self.merged = []
        self.posted_reviews = []
        self.attempted_reviews = []
        self.posted_comments = []

    # -- reads ------------------------------------------------------------
    def pr(self, number):
        return copy.deepcopy(self._pr)

    def pr_diff(self, number):
        return self._diff

    def reviews(self, number):
        return copy.deepcopy(self._reviews)

    def issue_comments(self, number):
        return copy.deepcopy(self._comments)

    def branch_protection(self, branch):
        return copy.deepcopy(self._protection)

    def verify_auth(self):
        return self.user

    def repo_info(self):
        return copy.deepcopy(getattr(self, "_repo_info", REPO_INFO))

    # -- writes -----------------------------------------------------------
    def submit_review(self, number, event, body):
        self.attempted_reviews.append({"number": number, "event": event,
                                       "body": body})
        if not self._review_api_ok:
            return False
        self.posted_reviews.append({"number": number, "event": event,
                                    "body": body})
        self._reviews.append({
            # REST shape: `gh.reviews()` hits the REST API, which reports the
            # reviewer as `user`, not `author` (gh's --json would say author).
            "user": {"login": self.user},
            # What GitHub actually reports back for an EVENT_REQUEST_CHANGES
            # review is a state of CHANGES_REQUESTED.
            "state": "CHANGES_REQUESTED" if event == "REQUEST_CHANGES" else event,
            "body": body,
        })
        return True

    def comment(self, number, body):
        self.posted_comments.append({"number": number, "body": body})
        self._comments.append({"user": {"login": self.user}, "body": body})
        return True

    def merge(self, number, method):
        self.merged.append((number, method))
        return True, "merged"


def make_diff(path="CONTRIBUTING.md", added=("A new line.",),
              removed=()):
    """A minimal unified diff the analyser can walk."""
    total = len(removed) + len(added) + 1
    lines = [
        f"diff --git a/{path} b/{path}",
        "index 1111111..2222222 100644",
        f"--- a/{path}",
        f"+++ b/{path}",
        f"@@ -1,2 +1,{total} @@",
        " existing context",
    ]
    lines += [f"-{line}" for line in removed]
    lines += [f"+{line}" for line in added]
    return "\n".join(lines) + "\n"


REPO_INFO = {
    "name": "BistaDinesh03/critique",
    "default_branch": "main",
    "url": "https://github.com/BistaDinesh03/critique",
    "visibility": "PUBLIC",
    "allow_merge_commit": True,
    "allow_squash_merge": True,
    "allow_rebase_merge": True,
    "delete_branch_on_merge": False,
    "viewer_default_merge_method": "merge",
    "viewer_permission": "ADMIN",
    "can_administer": True,
}

PROTECTION = {
    "required_pull_request_reviews": {
        "required_approving_review_count": 1,
        "dismiss_stale_approvals": False,
    },
    "required_status_checks": {"contexts": ["test"], "strict": False},
    "enforce_admins": {"enabled": True},
}

APPROVAL = {"user": {"login": "maintainer"}, "state": "APPROVED"}

CLEAN_BODY = (
    "## Summary\n\n"
    "Explain how to run one focused test instead of the whole suite.\n\n"
    "Fixes #22\n\n"
    "## Testing\n\n- `python -m pytest tests/ -q` — 355 passed\n"
)


def clean_pr(**overrides):
    """An unremarkable, well-formed pull request."""
    pr = {
        "number": 56,
        "title": "docs: explain how to run focused tests",
        "state": "OPEN",
        "isDraft": False,
        "url": "https://github.com/BistaDinesh03/critique/pull/56",
        "body": CLEAN_BODY,
        "baseRefName": "main",
        "baseRefOid": "b" * 40,
        "headRefName": "docs/single-test-commands",
        "headRefOid": "a" * 40,
        "mergeable": "MERGEABLE",
        "mergeStateStatus": "CLEAN",
        "reviewDecision": None,
        "additions": 12,
        "deletions": 0,
        "changedFiles": 1,
        "author": {"login": "contributor"},
        "labels": [],
        "createdAt": "2026-10-17T13:59:59Z",
        "updatedAt": "2026-10-17T13:59:59Z",
        "headRepositoryOwner": {"login": "contributor"},
        "headRepository": {"name": "critique", "isFork": True},
        "commits": [{"oid": "a" * 40, "messageHeadline": "docs: focused tests"}],
        "files": [
            {"path": "CONTRIBUTING.md", "additions": 12, "deletions": 0,
             "status": "modified"},
        ],
        "statusCheckRollup": [{"name": "test", "state": "SUCCESS"}],
    }
    pr.update(overrides)
    return pr


def review_of(pr, diff=None, reviews=(APPROVAL,), protection=PROTECTION,
              run_tests=False):
    gh = FakeGitHub(pr, diff=diff if diff is not None else make_diff(),
                    reviews=reviews, protection=protection)
    result = review_pr.build_review(gh, pr["number"], REPO_INFO,
                                    run_tests=run_tests)
    return gh, result


def codes(result, severity=None):
    return [f.code for f in result.findings
            if severity is None or f.severity == severity]


# ---------------------------------------------------------------------------
# A clean pull request
# ---------------------------------------------------------------------------

def test_clean_pull_request_is_ready():
    _, result = review_of(clean_pr())
    assert result.status == "READY"
    assert result.blocking == []
    assert result.important == []


def test_clean_pull_request_passes_every_gate():
    gh, result = review_of(clean_pr())
    assert all(gate.ok for gate in result.gates)
    assert result.gates_ok is True


def test_clean_merge_uses_the_repository_default_method():
    gh, result = review_of(clean_pr())
    exit_code = review_pr.main(["56", "--merge", "--skip-tests"], gh=gh)
    assert exit_code == 0
    assert gh.merged == [(56, "merge")]
    assert gh.posted_reviews == []
    assert gh.posted_comments == []


def test_review_is_the_default_and_never_merges():
    gh, result = review_of(clean_pr())
    exit_code = review_pr.main(["56", "--skip-tests"], gh=gh)
    assert exit_code == 0          # READY
    assert gh.merged == []         # nothing merged without --merge
    assert gh.posted_reviews == []
    assert gh.posted_comments == []


# ---------------------------------------------------------------------------
# Review transport shapes: REST says `user`, gh --json says `author`
# ---------------------------------------------------------------------------

def test_rest_shaped_approval_satisfies_the_gate():
    """`gh.reviews()` calls the REST API, whose reviews carry `user.login`.
    An approval in that exact shape must count -- reading only the GraphQL
    `author` field dropped every real approval and made the merge gate
    refuse even a fully approved pull request."""
    approval = {"user": {"login": "maintainer"}, "state": "APPROVED",
                "commit_id": "a" * 40}
    _, result = review_of(clean_pr(), reviews=(approval,))
    gate = next(g for g in result.gates if g.name.startswith("Approvals"))
    assert gate.ok, gate.detail
    assert "1 present" in gate.detail


def test_rest_shaped_approval_still_merges_end_to_end():
    approval = {"user": {"login": "maintainer"}, "state": "APPROVED"}
    gh, _ = review_of(clean_pr(), reviews=(approval,))
    assert review_pr.main(["56", "--merge", "--skip-tests"], gh=gh) == 0
    assert gh.merged == [(56, "merge")]


def test_approval_state_reads_both_shapes():
    """Both transports keep working: REST `user` and GraphQL `author`."""
    rest = {"user": {"login": "rest-reviewer"}, "state": "APPROVED"}
    graphql = {"author": {"login": "json-reviewer"}, "state": "APPROVED"}
    approvals, changes = review_pr.approval_state([rest, graphql])
    assert sorted(approvals) == ["json-reviewer", "rest-reviewer"]
    assert changes == []


def test_already_requested_changes_recognises_rest_shaped_reviews():
    """The idempotency check reads the same REST payload; it must find our
    own past review there or every re-run would post the same request."""
    gh = FakeGitHub(clean_pr(), reviews=[{
        "user": {"login": "maintainer"},
        "state": "CHANGES_REQUESTED",
        "body": f"{review_pr.REVIEW_MARKER}\nfindings:sig-123",
    }])
    assert review_pr.already_requested_changes(gh, 56, "sig-123") is True
    assert review_pr.already_requested_changes(gh, 56, "different") is False


# ---------------------------------------------------------------------------
# Blocking states
# ---------------------------------------------------------------------------

def test_closed_pull_request_is_blocked():
    _, result = review_of(clean_pr(state="CLOSED"))
    assert result.status == "BLOCKED"
    assert "UNREACHABLE" in codes(result)


def test_draft_pull_request_is_blocked():
    _, result = review_of(clean_pr(isDraft=True))
    assert result.status == "BLOCKED"
    assert "DRAFT" in codes(result)


def test_wrong_base_branch_is_blocked():
    _, result = review_of(clean_pr(baseRefName="develop"))
    assert result.status == "BLOCKED"
    assert "WRONG_BASE" in codes(result)
    finding = next(f for f in result.findings if f.code == "WRONG_BASE")
    assert "main" in finding.fix


def test_merge_conflict_is_blocked():
    _, result = review_of(clean_pr(mergeable="CONFLICTING",
                                   mergeStateStatus="DIRTY"))
    assert result.status == "BLOCKED"
    assert "CONFLICT" in codes(result)


def test_failing_ci_is_blocked():
    pr = clean_pr(statusCheckRollup=[
        {"name": "test", "state": "COMPLETED", "conclusion": "FAILURE",
         "description": "1 failed", "detailsUrl": "https://example.test/1"},
    ])
    _, result = review_of(pr)
    assert result.status == "BLOCKED"
    assert "CHECKS_FAILED" in codes(result, "BLOCKING")


def test_running_checks_block_a_merge():
    pr = clean_pr(statusCheckRollup=[
        {"name": "test", "state": "IN_PROGRESS"},
    ])
    gh, result = review_of(pr)
    assert result.status == "BLOCKED"
    assert "CHECKS_RUNNING" in codes(result)
    assert review_pr.main(["56", "--merge", "--skip-tests"], gh=gh) == 1
    assert gh.merged == []


def test_existing_request_for_changes_blocks():
    reviews = [APPROVAL,
               {"user": {"login": "other"}, "state": "CHANGES_REQUESTED"}]
    _, result = review_of(clean_pr(), reviews=reviews)
    assert result.status == "CHANGES_REQUESTED"
    assert "CHANGES_REQUESTED_EXISTING" in codes(result, "BLOCKING")


# ---------------------------------------------------------------------------
# Diff analysis
# ---------------------------------------------------------------------------

def test_a_leaked_secret_is_blocking():
    diff = make_diff("backend/app/config.py",
                     added=['TOKEN = "ghp_abcdefghijklmnopqrstuv"'])
    _, result = review_of(clean_pr(), diff=diff)
    assert "SECRET" in codes(result, "BLOCKING")
    finding = next(f for f in result.findings if f.code == "SECRET")
    assert finding.path == "backend/app/config.py"
    assert finding.line > 0
    assert "rotate" in finding.fix


def test_env_and_database_files_are_blocking():
    pr = clean_pr(files=[
        {"path": ".env", "additions": 3, "deletions": 0, "status": "added"},
        {"path": "critique.db", "additions": 9, "deletions": 0,
         "status": "added"},
    ], changedFiles=2)
    _, result = review_of(pr, diff=make_diff(".env", added=["SECRET=1"]))
    assert codes(result, "BLOCKING").count("FORBIDDEN_PATH") == 2


def test_unsafe_code_is_important_and_explains_itself():
    diff = make_diff("backend/app/jobs.py",
                     added=["    subprocess.run(cmd, shell=True)"])
    _, result = review_of(clean_pr(), diff=diff)
    assert "UNSAFE_CODE" in codes(result, "IMPORTANT")
    finding = next(f for f in result.findings if f.code == "UNSAFE_CODE")
    assert "shell=True" in finding.message
    assert "injection" in finding.why


def test_source_change_without_tests_is_important():
    pr = clean_pr(files=[
        {"path": "static/share.js", "additions": 40, "deletions": 0,
         "status": "modified"},
    ])
    _, result = review_of(pr, diff=make_diff("static/share.js",
                                             added=["navigator.share();"]))
    assert "TESTS_MISSING" in codes(result, "IMPORTANT")


def test_source_change_with_tests_is_not_flagged():
    pr = clean_pr(files=[
        {"path": "static/share.js", "additions": 40, "deletions": 0,
         "status": "modified"},
        {"path": "backend/tests/test_share.py", "additions": 20, "deletions": 0,
         "status": "added"},
    ])
    _, result = review_of(pr, diff=make_diff("static/share.js",
                                             added=["navigator.share();"]))
    assert "TESTS_MISSING" not in codes(result)


def test_deleted_tests_are_important():
    pr = clean_pr(files=[
        {"path": "backend/tests/test_old.py", "additions": 0, "deletions": 50,
         "status": "removed"},
    ])
    _, result = review_of(pr)
    assert "TESTS_DELETED" in codes(result, "IMPORTANT")


def test_security_and_deploy_files_are_important():
    pr = clean_pr(files=[
        {"path": "SECURITY.md", "additions": 5, "deletions": 1,
         "status": "modified"},
        {"path": "render.yaml", "additions": 2, "deletions": 0,
         "status": "modified"},
    ])
    _, result = review_of(pr, diff=make_diff("render.yaml", added=["env: x"]))
    assert "SENSITIVE_PATH" in codes(result, "IMPORTANT")


def test_empty_description_is_important():
    _, result = review_of(clean_pr(body=""))
    assert "NO_DESCRIPTION" in codes(result, "IMPORTANT")
    assert "NO_TEST_EVIDENCE" in codes(result, "IMPORTANT")


def test_description_reported_as_existing_failures_is_only_minor():
    body = ("## Testing\n\n- `python -m pytest tests/ -q` — 344 passed, "
            "2 existing failures in tests/test_oauth_state.py\n")
    _, result = review_of(clean_pr(body=body))
    finding = next(f for f in result.findings if f.code == "BODY_REPORTS_FAILURES")
    assert finding.severity == "MINOR"
    assert result.status == "READY"


def test_unexplained_failures_in_the_body_are_important():
    body = ("## Testing\n\nRan the suite. 2 failures, will look later.\n")
    _, result = review_of(clean_pr(body=body))
    finding = next(f for f in result.findings if f.code == "BODY_REPORTS_FAILURES")
    assert finding.severity == "IMPORTANT"
    assert result.status == "CHANGES_REQUESTED"


def test_conflict_markers_are_blocking():
    diff = make_diff("static/app.js", added=["<<<<<<< HEAD"])
    _, result = review_of(clean_pr(), diff=diff)
    assert "CONFLICT_MARKERS" in codes(result, "BLOCKING")


def test_oversized_change_is_important():
    files = [{"path": f"backend/app/module_{i}.py", "additions": 5,
              "deletions": 0, "status": "added"} for i in range(25)]
    _, result = review_of(clean_pr(files=files, changedFiles=25))
    assert "SCOPE" in codes(result, "IMPORTANT")


def test_unrelated_files_are_flagged_as_a_heuristic_only():
    pr = clean_pr(title="docs: explain how to run focused tests",
                  body=CLEAN_BODY,
                  files=[
                      {"path": "CONTRIBUTING.md", "additions": 12,
                       "deletions": 0, "status": "modified"},
                      {"path": "static/analytics.js", "additions": 4,
                       "deletions": 0, "status": "modified"},
                  ])
    _, result = review_of(pr, diff=make_diff("static/analytics.js",
                                             added=["var x = 1;"]))
    finding = next(f for f in result.findings if f.code == "UNRELATED")
    assert finding.severity == "MINOR"
    assert "heuristic" in finding.evidence
    # A documentation file name is not a topic, so it never counts as stray.
    assert "CONTRIBUTING.md" not in finding.message


def test_github_urls_in_the_body_do_not_read_as_issue_links():
    body = CLEAN_BODY.replace("Fixes #22", "See the project page.")
    _, result = review_of(clean_pr(body=body))
    assert "NO_ISSUE_LINK" in codes(result, "MINOR")


# ---------------------------------------------------------------------------
# Test-run comparison: who is to blame for a failure
# ---------------------------------------------------------------------------

def run(passed=300, failed=0, failures=(), ran=True, reason="", details=None):
    """The shape ``run_suite`` returns. ``details`` maps a failing node to the
    normalised reason it failed, which is what the blame comparison weighs."""
    return {"ran": ran, "passed": passed, "failed": failed, "errors": 0,
            "failures": sorted(failures),
            "failure_details": dict(details or {}),
            "reason": reason, "elapsed": 1.0, "tail": []}


def test_new_failure_is_blamed_on_the_branch():
    head = run(failed=1, failures=["tests/test_new.py::test_x"])
    base = run()
    findings = review_pr.compare_runs(head, base)
    assert [f.code for f in findings] == ["TEST_FAILURES"]
    assert findings[0].severity == "BLOCKING"


def test_failure_present_on_base_is_not_blamed_on_the_branch():
    head = run(failed=1, failures=["tests/test_oauth.py::test_login"])
    base = run(failed=1, failures=["tests/test_oauth.py::test_login"])
    findings = review_pr.compare_runs(head, base)
    assert [f.code for f in findings] == ["PREEXISTING_FAILURES"]
    assert findings[0].severity == "MINOR"


def test_passing_suite_produces_no_findings():
    assert review_pr.compare_runs(run(), run()) == []


def test_tests_that_could_not_run_are_reported_not_assumed():
    findings = review_pr.compare_runs(run(ran=False, reason="no node"), None)
    assert [f.code for f in findings] == ["TESTS_NOT_RUN"]
    assert findings[0].severity == "IMPORTANT"
    assert "no node" in findings[0].message


# ---------------------------------------------------------------------------
# Approvals and the merge gate
# ---------------------------------------------------------------------------

def test_missing_approval_fails_the_gate_but_not_the_status():
    gh, result = review_of(clean_pr(), reviews=[])
    assert result.status == "READY"
    gate = next(g for g in result.gates if g.name.startswith("Approvals"))
    assert gate.ok is False
    assert review_pr.main(["56", "--merge", "--skip-tests"], gh=gh) == 1
    assert gh.merged == []


def test_unconfigured_branch_protection_fails_the_gate():
    gh, result = review_of(clean_pr(), protection=None)
    gate = next(g for g in result.gates if "Branch protection" in g.name)
    assert gate.ok is False
    assert gate.manual_fix
    assert review_pr.main(["56", "--merge", "--skip-tests"], gh=gh) == 1
    assert gh.merged == []


def test_unreadable_branch_protection_is_reported_as_unverified():
    gh, result = review_of(
        clean_pr(), protection=review_pr.BranchProtectionUnreadable(403))
    gate = next(g for g in result.gates if "Branch protection" in g.name)
    assert gate.ok is False
    assert "could not verify" in gate.detail
    assert "HTTP 403" in gate.detail
    assert "not enabled" not in gate.detail
    assert "not enabled" not in gate.manual_fix
    assert gate.manual_fix
    approvals = next(g for g in result.gates if g.name.startswith("Approvals"))
    assert "requirements unknown" in approvals.detail
    assert review_pr.main(["56", "--merge", "--skip-tests"], gh=gh) == 1
    assert gh.merged == []


def test_branch_protection_maps_http_status_to_outcome():
    class Proc:
        def __init__(self, returncode, stdout="", stderr=""):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def client(status):
        def runner(*_args, **_kwargs):
            if status == 200:
                return Proc(0, stdout='{"enforce_admins": {"enabled": true}}')
            return Proc(1, stderr=f"gh: Forbidden (HTTP {status})")
        return review_pr.GitHub("owner/repo", runner=runner)

    assert client(404).branch_protection("main") is None
    unreadable = client(403).branch_protection("main")
    assert isinstance(unreadable, review_pr.BranchProtectionUnreadable)
    assert unreadable.status == 403
    assert client(200).branch_protection("main") == {
        "enforce_admins": {"enabled": True}}


def test_no_ci_configuration_fails_the_gate():
    pr = clean_pr(statusCheckRollup=[])
    gh, result = review_of(pr)
    gate = next(g for g in result.gates if g.name == "Continuous integration")
    assert gate.ok is False
    assert review_pr.main(["56", "--merge", "--skip-tests"], gh=gh) == 1
    assert gh.merged == []


def test_blockers_stop_a_merge_even_with_the_flag():
    diff = make_diff("backend/app/config.py",
                     added=['API_KEY = "ghp_abcdefghijklmnopqrstuv"'])
    gh, result = review_of(clean_pr(), diff=diff)
    assert result.status == "CHANGES_REQUESTED"
    assert review_pr.main(["56", "--merge", "--skip-tests"], gh=gh) == 1
    assert gh.merged == []


def test_merge_method_can_be_overridden_but_only_if_allowed():
    assert review_pr.choose_method(REPO_INFO, "squash") == "squash"
    assert review_pr.choose_method(REPO_INFO, "rebase") == "rebase"
    assert review_pr.choose_method(REPO_INFO, None) == "merge"

    no_merge = dict(REPO_INFO, allow_merge_commit=False,
                    viewer_default_merge_method="MERGE")
    assert review_pr.choose_method(no_merge, None) == "squash"

    nothing_allowed = dict(REPO_INFO, allow_merge_commit=False,
                           allow_squash_merge=False, allow_rebase_merge=False)
    assert review_pr.choose_method(nothing_allowed, None) is None


def test_merge_is_refused_when_the_repository_allows_no_method():
    gh = FakeGitHub(clean_pr(), diff=make_diff(), reviews=[APPROVAL],
                    protection=PROTECTION)
    gh._repo_info = dict(REPO_INFO, allow_merge_commit=False,
                         allow_squash_merge=False, allow_rebase_merge=False)
    exit_code = review_pr.main(["56", "--merge", "--skip-tests"], gh=gh)
    assert exit_code == 1
    assert gh.merged == []


# ---------------------------------------------------------------------------
# Requesting changes, without duplication
# ---------------------------------------------------------------------------

def test_request_changes_posts_once_and_never_twice():
    diff = make_diff("backend/app/config.py",
                     added=['API_KEY = "ghp_abcdefghijklmnopqrstuv"'])
    gh = FakeGitHub(clean_pr(), diff=diff, reviews=[APPROVAL],
                    protection=PROTECTION)

    first = review_pr.build_review(gh, 56, REPO_INFO, run_tests=False)
    assert first.status == "CHANGES_REQUESTED"
    ok, _ = review_pr.post_review(gh, first, 56)
    assert ok is True
    assert len(gh.posted_reviews) == 1
    assert gh.posted_reviews[0]["event"] == "REQUEST_CHANGES"

    # The posted review now shows up as an unresolved request for changes,
    # which must not change what we would say -- or we would post again.
    second = review_pr.build_review(gh, 56, REPO_INFO, run_tests=False)
    assert "CHANGES_REQUESTED_EXISTING" in codes(second)
    assert second.signature() == first.signature()

    ok, detail = review_pr.post_review(gh, second, 56)
    assert ok is False
    assert "already posted" in detail
    assert len(gh.posted_reviews) == 1


def test_new_problem_after_a_previous_request_is_posted():
    """A genuinely different finding must still earn a fresh request."""
    gh = FakeGitHub(clean_pr(), reviews=[APPROVAL], protection=PROTECTION)
    first = review_pr.build_review(gh, 56, REPO_INFO, run_tests=False)
    assert first.status == "READY"
    assert review_pr.post_review(gh, first, 56)[0] is False   # nothing to say

    # Now a secret turns up.
    gh._diff = make_diff("backend/app/config.py",
                         added=['API_KEY = "ghp_abcdefghijklmnopqrstuv"'])
    second = review_pr.build_review(gh, 56, REPO_INFO, run_tests=False)
    assert second.signature() != first.signature()
    assert review_pr.post_review(gh, second, 56)[0] is True
    assert len(gh.posted_reviews) == 1


def test_review_api_failure_falls_back_to_a_comment():
    diff = make_diff("backend/app/config.py",
                     added=['API_KEY = "ghp_abcdefghijklmnopqrstuv"'])
    gh = FakeGitHub(clean_pr(), diff=diff, reviews=[APPROVAL],
                    protection=PROTECTION, review_api_ok=False)
    result = review_pr.build_review(gh, 56, REPO_INFO, run_tests=False)
    ok, detail = review_pr.post_review(gh, result, 56)
    assert ok is True
    assert "comment" in detail
    assert gh.posted_reviews == []
    assert len(gh.posted_comments) == 1


def test_clean_pull_request_posts_nothing():
    gh = FakeGitHub(clean_pr(), diff=make_diff(), reviews=[APPROVAL],
                    protection=PROTECTION)
    result = review_pr.build_review(gh, 56, REPO_INFO, run_tests=False)
    ok, detail = review_pr.post_review(gh, result, 56)
    assert ok is False
    assert gh.posted_reviews == []
    assert gh.posted_comments == []


def test_request_changes_command_respects_the_findings(capsys):
    diff = make_diff("backend/app/config.py",
                     added=['API_KEY = "ghp_abcdefghijklmnopqrstuv"'])
    gh = FakeGitHub(clean_pr(), diff=diff, reviews=[APPROVAL],
                    protection=PROTECTION)
    exit_code = review_pr.main(["56", "--request-changes", "--skip-tests"], gh=gh)
    assert exit_code == 1
    assert len(gh.posted_reviews) == 1
    body = gh.posted_reviews[0]["body"]
    assert review_pr.REVIEW_MARKER in body
    assert "SECRET" in body
    assert gh.merged == []


# ---------------------------------------------------------------------------
# Environment hygiene
# ---------------------------------------------------------------------------

def test_the_test_environment_carries_no_tokens():
    env = review_pr._sanitized_env()
    for name in ("GITHUB_TOKEN", "GH_TOKEN", "GIT_ASKPASS",
                 "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
        assert name not in env
    assert env.get("PYTHONIOENCODING") == "utf-8"
    assert "PATH" in env


def test_pytest_output_is_parsed_without_being_trusted():
    output = (
        "FAILED tests/test_a.py::test_one - AssertionError\n"
        "ERROR tests/test_b.py::test_two\n"
        "1 failed, 2 passed, 1 error, 1 warning in 0.50s\n"
    )
    parsed = review_pr._parse_pytest(output)
    assert parsed["failed"] == 1
    assert parsed["passed"] == 2
    assert parsed["errors"] == 1
    assert parsed["failures"] == ["tests/test_a.py::test_one",
                                  "tests/test_b.py::test_two"]


def test_missing_pull_request_is_an_environment_error(monkeypatch):
    class Boom:
        repo = "BistaDinesh03/critique"
        user = "maintainer"

        def verify_auth(self):
            return "maintainer"

        def repo_info(self):
            return REPO_INFO

        def pr(self, number):
            raise review_pr.ReviewError("pull request #999 was not found")

    monkeypatch.setattr(review_pr.shutil, "which", lambda name: "/usr/bin/gh")
    assert review_pr.main(["999"], gh=Boom()) == 2


# ---------------------------------------------------------------------------
# Fail-closed: unreadable is never read as "fine"
# ---------------------------------------------------------------------------

def test_a_changed_failure_reason_is_a_new_failure():
    node = "tests/test_oauth_state.py::test_login_sends_state_to_github"
    head = run(failed=1, failures=[node],
               details={node: "KeyError: 'client_id'"})
    base = run(failed=1, failures=[node],
               details={node: "AssertionError: the assertion changed"})
    findings = review_pr.compare_runs(head, base)
    assert [f.code for f in findings] == ["TEST_FAILURES"]
    assert findings[0].severity == "BLOCKING"
    assert "differently" in findings[0].message


def test_identical_failure_reasons_are_still_preexisting():
    node = "tests/test_oauth_state.py::test_login_sends_state_to_github"
    details = {node: "KeyError: 'client_id'"}
    head = run(failed=1, failures=[node], details=details)
    base = run(failed=1, failures=[node], details=details)
    findings = review_pr.compare_runs(head, base)
    assert [f.code for f in findings] == ["PREEXISTING_FAILURES"]
    assert findings[0].severity == "MINOR"


def test_failures_are_blocking_when_the_base_could_not_run():
    node = "tests/test_a.py::test_x"
    findings = review_pr.compare_runs(
        run(failed=1, failures=[node]), run(ran=False, reason="no git"))
    assert [f.code for f in findings] == ["TEST_FAILURES"]
    assert findings[0].severity == "BLOCKING"
    assert "could not be checked" in findings[0].message


def test_run_specific_values_are_normalised_out_of_a_reason():
    first = review_pr._normalize_reason(
        "FileNotFoundError: C:\\tmp\\clone-a\\backend\\.env id=0x7fabc123",
        "C:\\tmp\\clone-a")
    second = review_pr._normalize_reason(
        "FileNotFoundError: C:\\tmp\\clone-b\\backend\\.env id=0x7fdef456",
        "C:\\tmp\\clone-b")
    assert first == second
    # Only run-specific noise disappears; a different cause stays different.
    assert (review_pr._normalize_reason("KeyError: 'client_id'")
            != review_pr._normalize_reason("AssertionError: wrong value"))


def test_a_check_in_an_unreadable_state_is_not_a_pass():
    pr = clean_pr(statusCheckRollup=[
        {"name": "test", "state": "SOMETHING_GITHUB_ADDED"},
        {"name": "lint", "state": "COMPLETED", "conclusion": "STALE"},
    ])
    gh, result = review_of(pr)
    assert "CHECKS_UNKNOWN" in codes(result, "BLOCKING")
    assert result.status == "BLOCKED"
    gate = next(g for g in result.gates if g.name == "All checks passed")
    assert gate.ok is False
    assert "unreadable" in gate.detail
    assert review_pr.main(["56", "--merge", "--skip-tests"], gh=gh) == 1
    assert gh.merged == []


@pytest.mark.parametrize("state", ["BLOCKED", "UNKNOWN", ""])
def test_a_merge_state_that_is_not_a_green_light_fails_the_gate(state):
    gh, result = review_of(clean_pr(mergeStateStatus=state))
    gate = next(g for g in result.gates if "mergeable" in g.name)
    assert gate.ok is False
    assert review_pr.main(["56", "--merge", "--skip-tests"], gh=gh) == 1
    assert gh.merged == []


def test_github_saying_review_is_required_fails_the_approval_gate():
    gh, result = review_of(clean_pr(reviewDecision="REVIEW_REQUIRED"),
                           reviews=[APPROVAL])
    gate = next(g for g in result.gates if g.name.startswith("Approvals"))
    assert gate.ok is False
    assert "REVIEW_REQUIRED" in gate.detail
    assert review_pr.main(["56", "--merge", "--skip-tests"], gh=gh) == 1
    assert gh.merged == []


def test_a_dismissed_stale_approval_is_only_counted_when_the_policy_allows():
    stale = dict(APPROVAL, commit_id="b" * 40)     # approved an older commit
    fresh = dict(APPROVAL, commit_id="a" * 40)     # approved the current head

    def protection_dismissing_stale():
        value = copy.deepcopy(PROTECTION)
        value["required_pull_request_reviews"]["dismiss_stale_approvals"] = True
        return value

    _, dismissed = review_of(clean_pr(), reviews=[stale],
                             protection=protection_dismissing_stale())
    gate = next(g for g in dismissed.gates if g.name.startswith("Approvals"))
    assert gate.ok is False

    _, kept = review_of(clean_pr(), reviews=[fresh],
                        protection=protection_dismissing_stale())
    gate = next(g for g in kept.gates if g.name.startswith("Approvals"))
    assert gate.ok is True

    _, tolerated = review_of(clean_pr(), reviews=[stale], protection=PROTECTION)
    gate = next(g for g in tolerated.gates if g.name.startswith("Approvals"))
    assert gate.ok is True


def test_nothing_is_posted_when_the_authenticated_login_is_unknown():
    diff = make_diff("backend/app/config.py",
                     added=['API_KEY = "ghp_abcdefghijklmnopqrstuv"'])
    gh, result = review_of(clean_pr(), diff=diff)
    assert result.blocking                      # there is something to post
    gh.user = ""                                # cannot identify ourselves
    posted, reason = review_pr.post_review(gh, result, 56)
    assert posted is False
    assert "could not be determined" in reason
    assert gh.posted_reviews == []
    assert gh.posted_comments == []


def test_github_reviews_and_comments_paginate_beyond_single_page():
    import json
    import subprocess

    calls = []

    def fake_runner(cmd, **kwargs):
        calls.append(cmd)
        endpoint = cmd[-1]
        if endpoint.endswith("&page=1"):
            data = [{"id": i, "body": f"item {i}"} for i in range(1, 101)]
            return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(data), stderr="")
        elif endpoint.endswith("&page=2"):
            data = [{"id": i, "body": f"item {i}"} for i in range(101, 106)]
            return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(data), stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="[]", stderr="")

    gh = review_pr.GitHub(repo="test/repo", runner=fake_runner)
    reviews = gh.reviews(10)
    assert len(reviews) == 105
    assert reviews[0]["id"] == 1
    assert reviews[-1]["id"] == 105
    assert len(calls) == 2
    assert "per_page=100&page=1" in calls[0][-1]
    assert "per_page=100&page=2" in calls[1][-1]

    calls.clear()
    comments = gh.issue_comments(10)
    assert len(comments) == 105
    assert comments[0]["id"] == 1
    assert comments[-1]["id"] == 105
    assert len(calls) == 2
    assert "per_page=100&page=1" in calls[0][-1]
    assert "per_page=100&page=2" in calls[1][-1]


def test_github_paginate_stops_when_under_page_limit():
    import json
    import subprocess

    calls = []

    def fake_runner(cmd, **kwargs):
        calls.append(cmd)
        data = [{"id": i} for i in range(35)]  # > 30 items, but < 100
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(data), stderr="")

    gh = review_pr.GitHub(repo="test/repo", runner=fake_runner)
    reviews = gh.reviews(10)
    assert len(reviews) == 35
    assert len(calls) == 1


def test_github_paginate_handles_api_errors_gracefully():
    import subprocess

    def error_runner(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="(HTTP 404) Not Found")

    gh = review_pr.GitHub(repo="test/repo", runner=error_runner)
    assert gh.reviews(10) == []
    assert gh.issue_comments(10) == []
