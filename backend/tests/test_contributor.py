"""Tests for scripts/contributor.py: assignment, review, finalize, thanks.

Every GitHub call is replaced by a fake. Nothing here assigns a real issue,
closes a real issue, merges a real pull request, or posts a real comment --
the fakes record writes so the tests can assert both that the right writes
happen and that the wrong ones never do.

The review half of this tool is `review_pr.py`, which has its own tests. The
tests here exercise the issue-side decisions and the seams between them:
consent before assignment, evidence before closure, confirmation before a
thank-you.
"""

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import contributor  # noqa: E402
import review_pr  # noqa: E402


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeGitHub:
    """Stands in for `gh`. Records every write. No network, ever."""

    def __init__(self, pr=None, issues=None, reviews=None, comments=None,
                 protection=None, repo=None, diff="", merge_error=None,
                 assign_ok=True, close_ok=True, comment_ok=True,
                 pr_after_merge_state="MERGED", pr_reread_error=None):
        self._pr = pr if pr is not None else clean_pr()
        self._issues = {n: copy.deepcopy(i) for n, i in (issues or {}).items()}
        self._reviews = list(reviews or [])
        self._comments = list(comments or [])
        self._protection = protection
        self._diff = diff
        self._merge_error = merge_error
        self._assign_ok = assign_ok
        self._close_ok = close_ok
        self._comment_ok = comment_ok
        self._pr_after_merge_state = pr_after_merge_state
        self._pr_reread_error = pr_reread_error

        self.repo = (repo or {}).get("name", "BistaDinesh03/critique")
        self.user = "maintainer"

        self.writes = {"assign": [], "close": [], "comment": [], "merge": []}
        self.attempted = {"assign": [], "close": [], "comment": [], "merge": []}

    # -- reads ------------------------------------------------------------
    def verify_auth(self):
        return self.user

    def repo_info(self):
        return copy.deepcopy(REPO_INFO)

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

    def issue(self, number):
        if number not in self._issues:
            raise review_pr.ReviewError(f"issue #{number} was not found")
        return copy.deepcopy(self._issues[number])

    def issue_locked(self, number):
        """Mirrors the real client: `locked` comes from the REST API, not the
        `gh --json` shape, so it is a separate call."""
        self.attempted.setdefault("locked", []).append(number)
        issue = self._issues.get(number) or {}
        return bool(issue.get("locked"))

    def issues(self, state="open"):
        return [copy.deepcopy(i) for i in self._issues.values()
                if (i.get("state") or "").upper() == state.upper()]

    # -- writes -----------------------------------------------------------
    def submit_review(self, number, event, body):
        """Used by `review_pr.post_review`. Recorded so a test can tell the
        difference between 'the review was submitted' and 'nobody tried'."""
        self.attempted.setdefault("review", []).append((number, event))
        if not self._comment_ok:
            return False
        self.writes.setdefault("review", []).append((number, event, body))
        self._reviews.append({
            # REST shape: reviews come from the REST API (`user`), not from
            # `gh --json` (`author`). Modelling the real transport here is
            # what keeps the approval gate tested against reality.
            "user": {"login": self.user},
            "state": "CHANGES_REQUESTED" if event == "REQUEST_CHANGES" else event,
            "body": body,
        })
        return True

    def assign_issue(self, number, user):
        self.attempted["assign"].append((number, user))
        if not self._assign_ok:
            return False
        self.writes["assign"].append((number, user))
        issue = self._issues.setdefault(number, {"number": number, "body": ""})
        issue.setdefault("assignees", []).append({"login": user})
        return True

    def close_issue(self, number):
        self.attempted["close"].append(number)
        if not self._close_ok:
            return False
        self.writes["close"].append(number)
        self._issues[number]["state"] = "CLOSED"
        return True

    def comment(self, number, body):
        self.attempted["comment"].append((number, body))
        if not self._comment_ok:
            return False
        self.writes["comment"].append((number, body))
        # REST shape: `issue_comments()` reads the REST API, which says `user`.
        self._comments.append({"user": {"login": self.user}, "body": body})
        return True

    def merge(self, number, method):
        self.attempted["merge"].append((number, method))
        if self._merge_error:
            return False, self._merge_error
        self.writes["merge"].append((number, method))
        self._pr["state"] = self._pr_after_merge_state
        return True, f"merged with a {method}"


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

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

APPROVAL = {"user": {"login": "maintainer"}, "state": "APPROVED",
            "commit_id": "a" * 40}

VOLUNTEER = ("Hi! I'd like to work on this issue. Could you please assign "
             "it to me?")


def clean_pr(**overrides):
    pr = {
        "number": 57,
        "title": "chore: add .editorconfig",
        "state": "OPEN",
        "isDraft": False,
        "url": "https://github.com/BistaDinesh03/critique/pull/57",
        "body": "Adds an editorconfig.\n\nFixes #38\n",
        "baseRefName": "main",
        "baseRefOid": "b" * 40,
        "headRefName": "chore/editorconfig",
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
        "commits": [{"oid": "a" * 40, "messageHeadline": "chore: editorconfig"}],
        "files": [
            {"path": ".editorconfig", "additions": 12, "deletions": 0,
             "status": "added"},
        ],
        "statusCheckRollup": [{"name": "test", "state": "SUCCESS"}],
    }
    pr.update(overrides)
    return pr


def open_issue(number=38, **overrides):
    issue = {
        "number": number,
        "title": "Add an .editorconfig",
        "state": "OPEN",
        "body": ("## The problem\n\nIndentation differs between files.\n\n"
                 "### Verified files\n\n- `.editorconfig`\n\n"
                 "## Acceptance criteria\n\n"
                 "- [ ] .editorconfig exists at the repository root\n"
                 "- [ ] It covers Python, JS and Markdown\n"),
        "labels": [{"name": "good first issue"}],
        "assignees": [],
        "author": {"login": "maintainer"},
        "comments": [],
        "createdAt": "2026-10-17T13:59:59Z",
        "updatedAt": "2026-10-17T13:59:59Z",
        "url": "https://github.com/BistaDinesh03/critique/issues/38",
        "locked": False,
        "closedAt": None,
    }
    issue.update(overrides)
    return issue


def comment(login, body):
    return {"author": {"login": login}, "body": body,
            "html_url": "https://example.test/c1"}


def finalize(pr=None, issues=None, protection=PROTECTION, reviews=(APPROVAL,),
             **kwargs):
    gh = FakeGitHub(pr=pr or clean_pr(), issues=issues or {38: open_issue()},
                    protection=protection, reviews=reviews, **kwargs)
    code = contributor.main(["finalize", "57", "--merge", "--skip-tests"], gh=gh)
    return gh, code


# ---------------------------------------------------------------------------
# Parsing: what counts as a link, a criterion, a file, a volunteer
# ---------------------------------------------------------------------------

def test_only_closing_keywords_mark_an_issue_as_closing():
    links = contributor.linked_issues(
        "Fixes #12\n\nCloses: #13\n\nResolves #14\n")
    assert links == {12: "closing", 13: "closing", 14: "closing"}


def test_a_bare_mention_is_not_a_closing_link():
    links = contributor.linked_issues("See #20 for background. Related to #21.")
    assert links == {20: "mentioned", 21: "mentioned"}


def test_numbers_inside_code_blocks_are_not_links():
    links = contributor.linked_issues("```\nFixes #99\n```\n\nFixes #7\n")
    assert links == {7: "closing"}


def test_a_comma_continuation_after_a_closing_keyword_closes_too():
    links = contributor.linked_issues("Fixes #30, #31 and also see #32")
    assert links[30] == "closing"
    assert links[31] == "closing"
    assert links[32] == "mentioned"


def test_acceptance_criteria_are_parsed_as_checked_and_unchecked():
    body = "- [x] done one\n- [ ] todo two\n- not a criterion\n"
    assert contributor.parse_criteria(body) == [(True, "done one"),
                                                (False, "todo two")]


def test_verified_files_are_parsed_from_the_issue_body():
    body = ("## Something\n\n### Verified files\n\n- `backend/app/main.py`\n"
            "- `docs/api.md`\n\n## Acceptance criteria\n")
    assert contributor.parse_verified_files(body) == ["backend/app/main.py",
                                                      "docs/api.md"]


def test_an_issue_without_the_section_names_no_files():
    assert contributor.parse_verified_files("just prose") == []


@pytest.mark.parametrize("text", [
    "I'd like to work on this issue.",
    "Could you please assign it to me?",
    "I plan to make this work with a cache header.",
    "Count me in!",
    "Can I take this one?",
    "I'm interested in contributing here.",
])
def test_the_phrasings_contributors_actually_use_are_recognised(text):
    assert contributor.VOLUNTEER_RE.search(text)


@pytest.mark.parametrize("text", [
    "This looks like a big change.",
    "I fixed a similar bug last year in another project.",
    "Assigning this to the backend module would be wrong.",
    "Nice issue!",
])
def test_casual_comments_are_not_read_as_a_volunteer(text):
    assert contributor.VOLUNTEER_RE.search(text) is None


# ---------------------------------------------------------------------------
# Assignment safety
# ---------------------------------------------------------------------------

def test_a_volunteer_is_assigned():
    issue = open_issue(comments=[comment("venius24", VOLUNTEER)])
    gh = FakeGitHub(issues={38: issue})
    outcome = contributor.build_assignment(gh, 38, "venius24", comment=False)
    assert outcome["action"] == "assigned"
    assert gh.writes["assign"] == [(38, "venius24")]
    assert outcome["evidence"].startswith("Hi! I'd like to work")


def test_nobody_is_assigned_without_a_request_from_them():
    gh = FakeGitHub(issues={38: open_issue()})
    outcome = contributor.build_assignment(gh, 38, "venius24", comment=False)
    assert outcome["action"] == "refused"
    assert "has not asked for" in outcome["reason"]
    assert gh.writes["assign"] == []
    assert gh.attempted["assign"] == []
    assert gh.writes["comment"] == []


def test_somebody_else_asking_does_not_count_as_that_person_volunteering():
    issue = open_issue(comments=[
        comment("dheeraj1174", "Could you please assign this to me?"),
    ])
    gh = FakeGitHub(issues={38: issue})
    outcome = contributor.build_assignment(gh, 38, "venius24", comment=False)
    assert outcome["action"] == "refused"
    assert gh.writes["assign"] == []


def test_an_issue_already_held_by_somebody_else_is_not_taken_away():
    issue = open_issue(assignees=[{"login": "shyama-05"}],
                       comments=[comment("venius24", VOLUNTEER)])
    gh = FakeGitHub(issues={38: issue})
    outcome = contributor.build_assignment(gh, 38, "venius24", comment=False)
    assert outcome["action"] == "refused"
    assert "already assigned to shyama-05" in outcome["reason"]
    assert gh.writes["assign"] == []


def test_re_assigning_the_same_person_is_a_no_op():
    issue = open_issue(assignees=[{"login": "venius24"}],
                       comments=[comment("venius24", VOLUNTEER)])
    gh = FakeGitHub(issues={38: issue})
    outcome = contributor.build_assignment(gh, 38, "venius24", comment=False)
    assert outcome["action"] == "already-assigned"
    assert gh.writes["assign"] == []
    assert gh.attempted["assign"] == []


def test_a_closed_issue_is_not_assigned():
    issue = open_issue(state="CLOSED",
                       comments=[comment("venius24", VOLUNTEER)])
    gh = FakeGitHub(issues={38: issue})
    outcome = contributor.build_assignment(gh, 38, "venius24", comment=False)
    assert outcome["action"] == "refused"
    assert gh.writes["assign"] == []


def test_a_locked_issue_is_not_assigned():
    issue = open_issue(locked=True,
                       comments=[comment("venius24", VOLUNTEER)])
    gh = FakeGitHub(issues={38: issue})
    outcome = contributor.build_assignment(gh, 38, "venius24", comment=False)
    assert outcome["action"] == "refused"
    assert "locked" in outcome["reason"]
    assert gh.writes["assign"] == []


def test_the_extra_locked_call_is_not_made_when_the_answer_is_already_no():
    """`issue_locked` costs an extra API call, so it is only asked once every
    other reason to refuse has been ruled out. A refusal for want of a
    volunteer's comment must not spend it."""
    gh = FakeGitHub(issues={38: open_issue()})
    contributor.build_assignment(gh, 38, "venius24", comment=False)
    assert gh.attempted.get("locked", []) == []

    # ...but it is asked on the path that is about to write.
    asked = FakeGitHub(issues={38: open_issue(
        comments=[comment("venius24", VOLUNTEER)])})
    contributor.build_assignment(asked, 38, "venius24", comment=False)
    assert asked.attempted["locked"] == [38]


def test_the_locked_check_read_from_the_rest_api_failing_does_not_block():
    """If the locked lookup errors, the client reports "not locked" rather
    than crashing -- but the write itself still happens, so the guardrail
    that matters (GitHub's own refusal) still applies."""
    gh = FakeGitHub(issues={38: open_issue(
        comments=[comment("venius24", VOLUNTEER)])})
    gh.issue_locked = lambda number: False
    outcome = contributor.build_assignment(gh, 38, "venius24", comment=False)
    assert outcome["action"] == "assigned"


def test_a_missing_issue_is_reported_not_invented():
    gh = FakeGitHub(issues={})
    outcome = contributor.build_assignment(gh, 999, "venius24", comment=False)
    assert outcome["action"] == "refused"
    assert "was not found" in outcome["reason"]
    assert gh.writes["assign"] == []


def test_the_username_match_is_case_insensitive():
    issue = open_issue(comments=[comment("Venius24", VOLUNTEER)])
    gh = FakeGitHub(issues={38: issue})
    outcome = contributor.build_assignment(gh, 38, "venius24", comment=False)
    assert outcome["action"] == "assigned"


def test_a_refusal_does_not_claim_success_in_its_wording():
    gh = FakeGitHub(issues={38: open_issue()})
    outcome = contributor.build_assignment(gh, 38, "venius24", comment=False)
    text = contributor.render_assignment(outcome)
    assert text.startswith("REFUSED:")
    assert "ISSUED" not in text


def test_no_comment_is_posted_unless_asked_for():
    issue = open_issue(comments=[comment("venius24", VOLUNTEER)])
    gh = FakeGitHub(issues={38: issue})
    contributor.build_assignment(gh, 38, "venius24", comment=False)
    assert gh.writes["comment"] == []


def test_a_comment_is_posted_only_when_requested_and_only_to_a_volunteer():
    issue = open_issue(comments=[comment("venius24", VOLUNTEER)])
    gh = FakeGitHub(issues={38: issue})
    outcome = contributor.build_assignment(gh, 38, "venius24", comment=True)
    assert outcome["commented"] is True
    assert len(gh.writes["comment"]) == 1
    assert "@venius24" in gh.writes["comment"][0][1]

    # ...and never to somebody who did not volunteer.
    silent = FakeGitHub(issues={38: open_issue()})
    outcome = contributor.build_assignment(silent, 38, "someone", comment=True)
    assert outcome["action"] == "refused"
    assert silent.writes["comment"] == []


def test_a_github_refusal_to_assign_is_reported_as_a_failure():
    issue = open_issue(comments=[comment("venius24", VOLUNTEER)])
    gh = FakeGitHub(issues={38: issue}, assign_ok=False)
    outcome = contributor.build_assignment(gh, 38, "venius24", comment=False)
    assert outcome["action"] == "failed"
    assert outcome["assigned"] is False
    assert "GitHub refused" in outcome["reason"]
    assert gh.writes["assign"] == []


def test_the_assign_command_exit_code_reflects_the_refusal(capsys):
    gh = FakeGitHub(issues={38: open_issue()})
    code = contributor.main(["assign", "38", "--user", "venius24"], gh=gh)
    assert code == 1
    assert gh.writes["assign"] == []
    assert "REFUSED" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Triage
# ---------------------------------------------------------------------------

def test_triage_offers_unclaimed_issues_with_what_a_contributor_needs():
    issues = {38: open_issue()}
    gh = FakeGitHub(issues=issues)
    data = contributor.build_triage(gh, labels=[], limit=5)
    assert [i["number"] for i in data["issues"]] == [38]
    row = data["issues"][0]
    assert row["suitable"] is True
    assert row["verified_files"] == [".editorconfig"]
    assert row["criteria_total"] == 2
    assert any("pytest" in t for t in row["tests"])


def test_triage_skips_issues_somebody_already_asked_for():
    issues = {38: open_issue(comments=[comment("dheeraj1174", VOLUNTEER)])}
    gh = FakeGitHub(issues=issues)
    data = contributor.build_triage(gh, labels=[], limit=5)
    assert data["issues"] == []
    assert [c["number"] for c in data["claimed"]] == [38]
    assert "dheeraj1174" in data["claimed"][0]["claimed_by"]


def test_triage_skips_assigned_and_closed_issues():
    issues = {
        1: open_issue(number=1, assignees=[{"login": "someone"}]),
        2: open_issue(number=2, state="CLOSED"),
        3: open_issue(number=3),
    }
    gh = FakeGitHub(issues=issues)
    data = contributor.build_triage(gh, labels=[], limit=5)
    assert [i["number"] for i in data["issues"]] == [3]


def test_triage_filters_by_label_when_asked():
    issues = {
        1: open_issue(number=1),
        2: open_issue(number=2, labels=[{"name": "backend"}]),
    }
    gh = FakeGitHub(issues=issues)
    data = contributor.build_triage(gh, labels=["backend"], limit=5)
    assert [i["number"] for i in data["issues"]] == [2]


def test_triage_puts_good_first_issue_before_everything_else():
    issues = {
        1: open_issue(number=1, labels=[{"name": "backend"}]),
        2: open_issue(number=2, labels=[{"name": "good first issue"}]),
    }
    gh = FakeGitHub(issues=issues)
    data = contributor.build_triage(gh, labels=[], limit=5)
    assert [i["number"] for i in data["issues"]] == [2, 1]


def test_triage_writes_nothing():
    gh = FakeGitHub(issues={38: open_issue()})
    contributor.build_triage(gh, labels=[], limit=5)
    assert gh.attempted == {"assign": [], "close": [], "comment": [],
                            "merge": []}


def test_a_failing_issue_list_is_reported_not_swallowed(monkeypatch):
    gh = FakeGitHub(issues={38: open_issue()})

    def boom(state="open"):
        raise review_pr.ReviewError("gh issue list failed: rate limited")

    monkeypatch.setattr(gh, "issues", boom)
    code = contributor.main(["triage"], gh=gh)
    assert code == 2


# ---------------------------------------------------------------------------
# Review: engine findings, issue context, and posting only once
# ---------------------------------------------------------------------------

def test_review_reports_the_engine_verdict_unchanged():
    gh = FakeGitHub(pr=clean_pr(), issues={38: open_issue()},
                    protection=PROTECTION, reviews=(APPROVAL,))
    pack = contributor.build_review_with_context(gh, 57, REPO_INFO,
                                                 run_tests=False)
    assert pack["result"].status == "READY"
    assert pack["result"].gates_ok is True


def test_review_separates_confirmed_from_suggestions_from_guesses():
    diff = ("diff --git a/backend/app/config.py b/backend/app/config.py\n"
            "--- a/backend/app/config.py\n+++ b/backend/app/config.py\n"
            "@@ -1,3 +1,4 @@\n"
            " x\n"
            "+API_KEY = \"ghp_abcdefghijklmnopqrstuv\"\n"
            "+FLAG = 1   \n")
    pr = clean_pr(
        # Not `type: summary`, so the title heuristic fires.
        title="Add an editorconfig file",
        body=("Adds an editorconfig so editors stop disagreeing about "
              "indentation. Formatting only, so no behaviour changes; "
              "`python -m pytest tests/ -q` was still run.\n"),
        files=[{"path": "backend/app/config.py", "additions": 2,
                "deletions": 0, "status": "modified"}],
    )
    gh = FakeGitHub(pr=pr, diff=diff, protection=PROTECTION, reviews=(APPROVAL,))
    pack = contributor.build_review_with_context(gh, 57, REPO_INFO,
                                                 run_tests=False)
    groups = pack["findings"]
    # Confirmed: observed in the diff.
    assert any(f.code == "SECRET" for f in groups["confirmed"])
    # Suggestions: a real, minor observation -- not one of the heuristics.
    assert any(f.code == "TRAILING_WHITESPACE" for f in groups["suggestions"])
    assert all(f.code not in contributor.HEURISTIC_CODES
               for f in groups["suggestions"])
    # Uncertainty: only pattern matching, and said to be.
    assert any(f.code == "TITLE_FORMAT" for f in groups["uncertain"])
    assert all(f.code in contributor.HEURISTIC_CODES
               for f in groups["uncertain"])
    # Anything important lands in confirmed, never in suggestions.
    for finding in groups["suggestions"]:
        assert finding.severity == "MINOR"


def test_review_shows_linked_issues_and_their_unticked_criteria():
    gh = FakeGitHub(pr=clean_pr(), issues={38: open_issue()},
                    protection=PROTECTION, reviews=(APPROVAL,))
    pack = contributor.build_review_with_context(gh, 57, REPO_INFO,
                                                 run_tests=False)
    assert pack["linked"][0]["number"] == 38
    assert pack["linked"][0]["kind"] == "closing"
    assert len(pack["linked"][0]["criteria_open"]) == 2


def test_review_reports_an_unreadable_linked_issue_without_failing():
    gh = FakeGitHub(pr=clean_pr(), issues={}, protection=PROTECTION,
                    reviews=(APPROVAL,))
    pack = contributor.build_review_with_context(gh, 57, REPO_INFO,
                                                 run_tests=False)
    assert pack["linked"][0]["error"]


def test_review_posts_changes_once_and_never_twice():
    """The posting itself is `review_pr.post_review`, which is idempotent;
    this checks the seam -- that `review` uses it rather than its own logic,
    and that a second run against the state the first run created does
    nothing at all."""
    diff = ("diff --git a/backend/app/config.py b/backend/app/config.py\n"
            "--- a/backend/app/config.py\n+++ b/backend/app/config.py\n"
            "@@ -1,2 +1,3 @@\n"
            " x\n+API_KEY = \"ghp_abcdefghijklmnopqrstuv\"\n")
    pr = clean_pr(files=[{"path": "backend/app/config.py", "additions": 1,
                          "deletions": 0, "status": "modified"}])
    gh = FakeGitHub(pr=pr, diff=diff, protection=PROTECTION, reviews=())
    contributor.main(["review", "57", "--request-changes", "--skip-tests"],
                     gh=gh)
    assert len(gh.writes.get("review", [])) == 1

    # A second run, against the reviews that first run created.
    gh2 = FakeGitHub(pr=pr, diff=diff, protection=PROTECTION,
                     reviews=copy.deepcopy(gh._reviews),
                     comments=copy.deepcopy(gh._comments))
    contributor.main(["review", "57", "--request-changes", "--skip-tests"],
                     gh=gh2)
    assert gh2.attempted.get("review", []) == []
    assert gh2.writes.get("review", []) == []
    assert gh2.writes["comment"] == []


def test_review_posts_nothing_when_there_is_nothing_to_ask_for():
    gh = FakeGitHub(pr=clean_pr(), issues={38: open_issue()},
                    protection=PROTECTION, reviews=(APPROVAL,))
    code = contributor.main(["review", "57", "--request-changes",
                             "--skip-tests"], gh=gh)
    assert code == 0
    assert gh.writes["comment"] == []


def test_the_review_command_never_merges():
    gh = FakeGitHub(pr=clean_pr(), issues={38: open_issue()},
                    protection=PROTECTION, reviews=(APPROVAL,))
    contributor.main(["review", "57", "--skip-tests"], gh=gh)
    assert gh.writes["merge"] == []
    assert gh.writes["close"] == []


# ---------------------------------------------------------------------------
# Finalize: refusal, closure, thanks
# ---------------------------------------------------------------------------

def test_finalize_without_merge_flag_writes_nothing(capsys):
    gh = FakeGitHub(pr=clean_pr(), issues={38: open_issue()},
                    protection=PROTECTION, reviews=(APPROVAL,))
    code = contributor.main(["finalize", "57", "--skip-tests"], gh=gh)
    assert code == 0
    assert gh.attempted == {"assign": [], "close": [], "comment": [],
                            "merge": []}
    out = capsys.readouterr().out
    assert "WILL CLOSE" in out


def test_finalize_refuses_without_the_merge_flag_when_the_status_is_not_ready():
    pr = clean_pr(body="", isDraft=True)
    gh = FakeGitHub(pr=pr, issues={38: open_issue()},
                    protection=PROTECTION, reviews=(APPROVAL,))
    code = contributor.main(["finalize", "57", "--skip-tests"], gh=gh)
    assert code == 1


def test_a_clean_pull_request_merges_closes_and_thanks():
    gh, code = finalize()
    assert code == 0
    assert gh.writes["merge"] == [(57, "merge")]
    assert gh.writes["close"] == [38]
    assert len(gh.writes["comment"]) == 1
    body = gh.writes["comment"][0][1]
    assert "@contributor" in body
    assert "has been merged" in body
    assert "critique.page" in body
    assert contributor.MARKER in body


def test_missing_ci_blocks_the_merge():
    gh = FakeGitHub(pr=clean_pr(statusCheckRollup=[]), issues={38: open_issue()},
                    protection=PROTECTION, reviews=(APPROVAL,))
    code = contributor.main(["finalize", "57", "--merge", "--skip-tests"], gh=gh)
    assert code == 1
    assert gh.writes["merge"] == []
    assert gh.writes["close"] == []
    assert gh.writes["comment"] == []


def test_failing_ci_blocks_the_merge():
    gh = FakeGitHub(
        pr=clean_pr(statusCheckRollup=[
            {"name": "test", "state": "COMPLETED", "conclusion": "FAILURE"}]),
        issues={38: open_issue()}, protection=PROTECTION, reviews=(APPROVAL,))
    code = contributor.main(["finalize", "57", "--merge", "--skip-tests"], gh=gh)
    assert code == 1
    assert gh.writes["merge"] == []


def test_missing_approval_blocks_the_merge():
    gh, code = finalize(reviews=())
    assert code == 1
    assert gh.writes["merge"] == []


def test_a_rest_shaped_approval_unblocks_the_merge():
    """Reviews reach the tool through the REST API, which reports the
    reviewer as `user`. An approval in that real shape must be enough to
    merge -- reading only the GraphQL `author` field counted zero and made
    this merge refuse forever, despite GitHub itself saying APPROVED."""
    rest_approval = {"user": {"login": "maintainer"}, "state": "APPROVED",
                     "commit_id": "a" * 40}
    gh, code = finalize(reviews=(rest_approval,))
    assert code == 0
    assert gh.writes["merge"] == [(57, "merge")]


def test_missing_approval_blocks_the_merge_when_the_shape_is_wrong():
    """Fail closed in the other direction too: a review nobody can identify
    (neither `user` nor `author`) counts as no approval at all."""
    gh, code = finalize(reviews=({"state": "APPROVED"},))
    assert code == 1
    assert gh.writes["merge"] == []


def test_unconfigured_branch_protection_blocks_the_merge():
    gh, code = finalize(protection=None)
    assert code == 1
    assert gh.writes["merge"] == []


def test_a_conflicted_pull_request_blocks_the_merge():
    gh = FakeGitHub(pr=clean_pr(mergeable="DIRTY", mergeStateStatus="DIRTY"),
                    issues={38: open_issue()}, protection=PROTECTION,
                    reviews=(APPROVAL,))
    code = contributor.main(["finalize", "57", "--merge", "--skip-tests"], gh=gh)
    assert code == 1
    assert gh.writes["merge"] == []


def test_finalize_never_weakens_the_engines_own_gates():
    """The gates reported are the review engine's, unchanged."""
    gh = FakeGitHub(pr=clean_pr(), issues={38: open_issue()},
                    protection=PROTECTION, reviews=(APPROVAL,))
    pack = contributor.build_finalize(gh, 57, REPO_INFO, run_tests=False)
    engine_gates = review_pr.build_gates(
        pack["result"], pack["result"].pr, REPO_INFO,
        review_pr.protection_requirements(PROTECTION), ["maintainer"])
    assert [g.name for g in pack["gates"][:len(engine_gates)]] == \
        [g.name for g in engine_gates]
    assert all(g.ok for g in engine_gates)


# ---------------------------------------------------------------------------
# Issue validation: closing what is done, leaving the rest open
# ---------------------------------------------------------------------------

def test_an_issue_linked_with_a_closing_keyword_is_closed():
    gh, code = finalize()
    assert gh.writes["close"] == [38]


def test_a_mentioned_issue_is_never_closed():
    pr = clean_pr(body="See #38 for background.\n")
    gh, code = finalize(pr=pr)
    assert code == 0
    assert gh.writes["merge"] == [(57, "merge")]
    assert gh.writes["close"] == []
    # The only comment is the thank-you; the issue was not named in it.
    assert len(gh.writes["comment"]) == 1
    assert contributor.MARKER in gh.writes["comment"][0][1]
    assert "#38" not in gh.writes["comment"][0][1]
    assert gh.attempted["close"] == []


def test_an_issue_whose_files_are_not_touched_holds_the_merge_open():
    """`Fixes #38` but the change does not touch anything the issue names."""
    pr = clean_pr(body="Fixes #38\n",
                  files=[{"path": "README.md", "additions": 1,
                          "deletions": 0, "status": "modified"}])
    gh = FakeGitHub(pr=pr, issues={38: open_issue()}, protection=PROTECTION,
                    reviews=(APPROVAL,))
    code = contributor.main(["finalize", "57", "--merge", "--skip-tests"], gh=gh)
    assert code == 1
    assert gh.writes["merge"] == []
    assert gh.writes["close"] == []


def test_no_close_merges_but_leaves_the_issue_open():
    gh = FakeGitHub(pr=clean_pr(), issues={38: open_issue()},
                    protection=PROTECTION, reviews=(APPROVAL,))
    code = contributor.main(["finalize", "57", "--merge", "--skip-tests", "--no-close"],
                            gh=gh)
    assert code == 0
    assert gh.writes["merge"] == [(57, "merge")]
    assert gh.writes["close"] == []


def test_an_already_closed_issue_is_not_closed_again():
    issue = open_issue(state="CLOSED")
    gh = FakeGitHub(pr=clean_pr(), issues={38: issue}, protection=PROTECTION,
                    reviews=(APPROVAL,))
    code = contributor.main(["finalize", "57", "--merge", "--skip-tests"], gh=gh)
    assert code == 0
    assert gh.writes["close"] == []


def test_a_linked_issue_that_cannot_be_read_is_reported_and_left_alone():
    gh = FakeGitHub(pr=clean_pr(), issues={}, protection=PROTECTION,
                    reviews=(APPROVAL,))
    code = contributor.main(["finalize", "57", "--merge", "--skip-tests"], gh=gh)
    assert code == 0
    assert gh.writes["merge"] == [(57, "merge")]
    assert gh.writes["close"] == []


def test_a_close_failure_is_reported_instead_of_claimed(capsys):
    gh = FakeGitHub(pr=clean_pr(), issues={38: open_issue()},
                    protection=PROTECTION, reviews=(APPROVAL,), close_ok=False)
    code = contributor.main(["finalize", "57", "--merge", "--skip-tests"], gh=gh)
    assert code == 0
    out = capsys.readouterr().out
    assert "was already closed by GitHub" in out
    assert "Closed issue #38" not in out


def test_unticked_criteria_are_shown_to_the_maintainer(capsys):
    gh, code = finalize()
    out = capsys.readouterr().out
    assert "acceptance criteria still unticked" in out
    assert ".editorconfig exists at the repository root" in out


# ---------------------------------------------------------------------------
# Thank-you timing
# ---------------------------------------------------------------------------

def test_nobody_is_thanked_before_the_merge_is_confirmed():
    gh = FakeGitHub(pr=clean_pr(), issues={38: open_issue()},
                    protection=PROTECTION, reviews=(APPROVAL,))
    ok, detail = contributor.post_thanks(gh, 57, "contributor")
    assert ok is False
    assert "not merged" in detail
    assert gh.writes["comment"] == []


def test_a_merge_command_accepted_but_not_reflected_gets_no_thanks():
    gh = FakeGitHub(pr=clean_pr(), issues={38: open_issue()},
                    protection=PROTECTION, reviews=(APPROVAL,),
                    pr_after_merge_state="OPEN")
    gh.merge(57, "merge")           # pretend the command ran
    gh.writes["comment"] = []
    ok, detail = contributor.post_thanks(gh, 57, "contributor")
    assert ok is False
    assert "OPEN" in detail


def test_finalize_that_cannot_confirm_the_merge_closes_and_thanks_nothing():
    """`perform_merge` re-reads the pull request after `gh.merge` returns.
    If GitHub accepted the command but the PR does not report MERGED, the
    run must claim nothing: no issue closed, no thank-you, exit 1."""
    gh = FakeGitHub(pr=clean_pr(), issues={38: open_issue()},
                    protection=PROTECTION, reviews=(APPROVAL,),
                    pr_after_merge_state="OPEN")
    code = contributor.main(["finalize", "57", "--merge", "--skip-tests"], gh=gh)
    assert code == 1
    assert gh.writes["merge"] == [(57, "merge")]     # the command ran...
    assert gh.writes["close"] == []                  # ...but nothing follows
    assert gh.writes["comment"] == []


def test_finalize_that_cannot_reread_the_pull_request_claims_nothing():
    """Same, but the re-read itself fails: an API error must not be read as
    success."""
    gh = FakeGitHub(pr=clean_pr(), issues={38: open_issue()},
                    protection=PROTECTION, reviews=(APPROVAL,))

    def boom(number):
        raise review_pr.ReviewError("gh pr view failed: HTTP 502")

    real_merge = gh.merge
    def merge_then_break(number, method):
        ok, detail = real_merge(number, method)
        gh.pr = boom
        return ok, detail

    gh.merge = merge_then_break
    code = contributor.main(["finalize", "57", "--merge", "--skip-tests"], gh=gh)
    assert code == 1
    assert gh.writes["close"] == []
    assert gh.writes["comment"] == []


def test_an_unreadable_pull_request_gets_no_thanks():
    gh = FakeGitHub(pr=clean_pr(), issues={38: open_issue()},
                    protection=PROTECTION, reviews=(APPROVAL,),
                    pr_reread_error=True)

    def boom(number):
        raise review_pr.ReviewError("gh pr view failed")

    gh.pr = boom
    ok, detail = contributor.post_thanks(gh, 57, "contributor")
    assert ok is False
    assert "could not re-read" in detail


# ---------------------------------------------------------------------------
# API errors that must not become tracebacks
# ---------------------------------------------------------------------------

def _missing_pr_gh(**kwargs):
    """A client whose pull request read fails the way `gh` reports a number
    that does not exist."""
    gh = FakeGitHub(pr=clean_pr(), issues={38: open_issue()},
                    protection=PROTECTION, reviews=(APPROVAL,), **kwargs)

    def boom(number):
        raise review_pr.ReviewError(f"pull request #{number} was not found")

    gh.pr = boom
    return gh


def test_review_of_a_missing_pull_request_exits_two_without_a_traceback(capsys):
    gh = _missing_pr_gh()
    code = contributor.main(["review", "99999", "--skip-tests"], gh=gh)
    assert code == 2                       # could not run, not refused
    out = capsys.readouterr()
    assert "Traceback" not in out.err
    assert "was not found" in out.err
    assert gh.writes == {"assign": [], "close": [], "comment": [], "merge": []}


def test_finalize_of_a_missing_pull_request_exits_two_and_writes_nothing(capsys):
    gh = _missing_pr_gh()
    code = contributor.main(["finalize", "99999", "--merge", "--skip-tests"],
                            gh=gh)
    assert code == 2
    out = capsys.readouterr()
    assert "Traceback" not in out.err
    assert "was not found" in out.err
    # Critically: no merge was attempted for a pull request that could not
    # even be read.
    assert gh.writes["merge"] == []
    assert gh.writes["close"] == []
    assert gh.writes["comment"] == []


def test_finalize_of_a_missing_pull_request_still_reports_only_without_merge(capsys):
    gh = _missing_pr_gh()
    code = contributor.main(["finalize", "99999", "--skip-tests"], gh=gh)
    assert code == 2
    assert "Traceback" not in capsys.readouterr().err


def test_a_second_thank_you_is_not_posted():
    gh = FakeGitHub(pr=clean_pr(), issues={38: open_issue()},
                    protection=PROTECTION, reviews=(APPROVAL,))
    contributor.main(["finalize", "57", "--merge", "--skip-tests"], gh=gh)
    first = len(gh.writes["comment"])
    assert first == 1

    ok, detail = contributor.post_thanks(gh, 57, "contributor")
    assert ok is False
    assert "already posted" in detail
    assert len(gh.writes["comment"]) == 1


def test_no_thanks_flag_skips_the_comment():
    gh = FakeGitHub(pr=clean_pr(), issues={38: open_issue()},
                    protection=PROTECTION, reviews=(APPROVAL,))
    code = contributor.main(["finalize", "57", "--merge", "--skip-tests", "--no-thanks"],
                            gh=gh)
    assert code == 0
    assert gh.writes["merge"] == [(57, "merge")]
    assert gh.writes["comment"] == []


def test_an_authorless_pull_request_is_reported_not_thanked():
    gh = FakeGitHub(pr=clean_pr(author={"login": ""}), issues={38: open_issue()},
                    protection=PROTECTION, reviews=(APPROVAL,))
    ok, detail = contributor.post_thanks(gh, 57, "")
    assert ok is False
    assert "no author" in detail


def test_the_thank_you_names_the_contributor_and_does_not_demand_a_project():
    gh = FakeGitHub(pr=clean_pr(state="MERGED",
                                author={"login": "venius24"}),
                    issues={38: open_issue()}, protection=PROTECTION,
                    reviews=(APPROVAL,))
    ok, _ = contributor.post_thanks(gh, 57, "venius24")
    assert ok is True
    body = gh.writes["comment"][0][1]
    assert "@venius24" in body
    assert "has been merged" in body
    assert "If you're building something yourself" in body
    assert "must" not in body.lower()
    assert "should submit" not in body.lower()
    assert "required" not in body.lower()


# ---------------------------------------------------------------------------
# Merge mechanics
# ---------------------------------------------------------------------------

def test_the_merge_uses_the_repositorys_own_default_method():
    gh, code = finalize()
    assert gh.writes["merge"] == [(57, "merge")]


def test_a_requested_method_the_repository_disallows_is_refused():
    gh = FakeGitHub(pr=clean_pr(), issues={38: open_issue()},
                    protection=PROTECTION, reviews=(APPROVAL,),
                    repo={"name": "BistaDinesh03/critique"})
    gh.repo_info = lambda: dict(REPO_INFO, allow_merge_commit=False,
                                viewer_default_merge_method="MERGE")
    code = contributor.main(["finalize", "57", "--merge", "--skip-tests",
                             "--merge-method", "merge"], gh=gh)
    assert code == 1
    assert gh.writes["merge"] == []


def test_a_refused_merge_is_reported_and_nothing_downstream_happens():
    gh = FakeGitHub(pr=clean_pr(), issues={38: open_issue()},
                    protection=PROTECTION, reviews=(APPROVAL,),
                    merge_error="GraphQL: Pull Request is not mergeable")
    code = contributor.main(["finalize", "57", "--merge", "--skip-tests"], gh=gh)
    assert code == 1
    assert gh.writes["close"] == []
    assert gh.writes["comment"] == []


def test_an_already_merged_pull_request_is_not_merged_or_thanked_again():
    pr = clean_pr(state="MERGED")
    gh = FakeGitHub(pr=pr, issues={38: open_issue()}, protection=PROTECTION,
                    reviews=(APPROVAL,))
    code = contributor.main(["finalize", "57", "--merge", "--skip-tests"], gh=gh)
    assert code == 0
    assert gh.writes["merge"] == []
    assert gh.writes["comment"] == []


# ---------------------------------------------------------------------------
# Guardrails: the tool never touches a fork or a contributor's branch
# ---------------------------------------------------------------------------

def test_the_module_makes_no_call_that_could_push_to_a_fork():
    import inspect
    source = inspect.getsource(contributor)
    for forbidden in ("git push", "force-push", "--force", "git checkout",
                      "git commit", "head_ref", "refs/heads/"):
        assert forbidden not in source, forbidden
