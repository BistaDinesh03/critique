#!/usr/bin/env python3
"""Contributor management for Critique: first contact to appreciation.

This is the maintainer's workflow around the review engine in
`review_pr.py`. It deliberately contains no review logic of its own --
every finding, every gate and every merge decision comes from that module.
What lives here is the issue-side work the engine has no opinion about:
finding unclaimed work, assigning it safely, checking a pull request's
linked issues, closing the ones that are genuinely done, and thanking the
contributor once the merge is confirmed.

    python scripts/contributor.py triage                    # find unclaimed work
    python scripts/contributor.py assign 30 --user Venius24 # only with their consent
    python scripts/contributor.py review 57                 # read-only, adds issue context
    python scripts/contributor.py finalize 57 --merge       # merge, close, thank

What this tool will not do, ever:

- assign an issue to somebody who has not asked for it,
- mention a contributor who has not already spoken on the issue,
- close an issue that merely appears in a pull request description,
- merge without `--merge`, or merge while any gate fails,
- thank somebody before the merge is confirmed by re-reading the pull
  request from GitHub,
- push to a contributor's fork or modify their branch.

Exit codes match `review_pr.py`: 0 = done, 1 = refused or needs work,
2 = could not run (bad usage, no `gh`, no authentication).
"""

import argparse
import json
import os
import re
import shutil
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import review_pr  # noqa: E402  (sibling module, path set above)
from review_pr import Gate, ReviewError, resolve_repo  # noqa: E402

MARKER = "<!-- critique-contributor -->"

# Comment text that counts as somebody volunteering for an issue. These are
# the phrasings actually used in this repository's comments, plus the usual
# variants. Assignment requires one of these from the person being assigned.
VOLUNTEER_PATTERNS = (
    r"i'?d like to (?:work|contribute|take)",
    r"i(?:'d| would) (?:love|like) (?:to )?(?:have it|work)",
    r"can i (?:work on|take|have) (?:it|this|this issue)",
    r"could you please assign (?:it to me|me)",
    r"assign (?:it to )?me\b",
    r"i(?:'m| am) interested (?:in|to work)",
    r"i plan to\b",
    r"count me in",
    r"i'?ll take (?:it|this)\b",
    r"i want to work on\b",
    r"may i work on\b",
)
VOLUNTEER_RE = re.compile("|".join(f"(?:{p})" for p in VOLUNTEER_PATTERNS),
                          re.IGNORECASE)

# Findings that are inference rather than observation. They are reported in
# their own bucket so a maintainer can see which words are guesses.
HEURISTIC_CODES = {"UNRELATED", "TITLE_FORMAT"}

CLOSING_KEYWORD_RE = re.compile(
    r"\b(close[sd]?|fix(e[sd])?|resolve[sd]?)\s*:?\s*"
    r"((?:#\d+\s*,?\s*)+)",
    re.IGNORECASE,
)
MENTION_RE = re.compile(r"(?<![\w/])#(\d+)\b")
FENCED_RE = re.compile(r"```.*?```", re.DOTALL)

CRITERIA_RE = re.compile(r"^\s*[-*]\s*\[([ xX])\]\s*(.+?)\s*$", re.MULTILINE)
VERIFIED_FILES_RE = re.compile(
    r"^#{2,4}\s*Verified files\s*$(.*?)(?=^#{2,4}\s|\Z)",
    re.MULTILINE | re.DOTALL,
)
FILE_ITEM_RE = re.compile(r"^[-*]\s*`([^`]+)`", re.MULTILINE)

# Which commands to suggest, by the area labels an issue carries.
AREA_TESTS = (
    ("backend", "`cd backend && python -m pytest tests/ -q`"),
    ("frontend", "`cd backend && python -m pytest tests/ -q` "
                 "(render tests) plus a look at the page in a browser"),
    ("tests", "`cd backend && python -m pytest tests/ -q`"),
    ("documentation", "no tests apply; check every link you add by opening it"),
    ("security", "`cd backend && python -m pytest tests/ -q`"),
    ("performance", "`cd backend && python -m pytest tests/ -q`"),
    ("accessibility", "`cd backend && python -m pytest tests/ -q` "
                      "(render tests) plus a keyboard-only pass"),
)
DEFAULT_TEST_COMMAND = "`cd backend && python -m pytest tests/ -q`"

THANKS_TEMPLATE = (
    "Thanks for contributing to Critique, @{user}! Your PR #{number} has "
    "been merged \u2014 really appreciate you helping improve the project. "
    "If you're building something yourself, we'd love to see it on "
    "https://critique.page and hear your feedback. Welcome to the community!"
)


# ---------------------------------------------------------------------------
# GitHub client: the review engine's, plus issue operations
# ---------------------------------------------------------------------------

class IssuesGitHub(review_pr.GitHub):
    """`review_pr.GitHub` with the issue-side calls this workflow needs.

    Subclassing rather than rewriting keeps one implementation of `api()`,
    one of authentication, and one place that knows how to talk to `gh`.
    """

    # `gh issue view --json` rejects a `locked` field -- it is not on the
    # list of accepted fields, so asking for it makes the whole command fail.
    # It is read from the REST API instead, in `issue_locked`, and only on the
    # path that is about to write.
    ISSUE_FIELDS = ",".join([
        "number", "title", "state", "body", "labels", "assignees",
        "author", "comments", "createdAt", "updatedAt", "url", "closedAt",
    ])

    def issue(self, number: int) -> Dict[str, Any]:
        args = ["issue", "view", str(number), "--json", self.ISSUE_FIELDS]
        if self.repo:
            args += ["--repo", self.repo]
        try:
            return self.gh_json(args)
        except ReviewError as exc:
            lowered = str(exc).lower()
            if "could not resolve to an issue" in lowered \
                    or "not found" in lowered:
                raise ReviewError(f"issue #{number} was not found")
            raise

    def issue_locked(self, number: int) -> bool:
        """Whether the issue is locked for conversation, via the REST API
        (the `gh --json` shape has no such field). Callers should only ask
        when they are about to write, so this costs nothing on a refusal."""
        status, body = self.api("GET", f"repos/{self.repo}/issues/{number}")
        if status != 200 or not body.strip():
            return False
        try:
            return bool(json.loads(body).get("locked"))
        except json.JSONDecodeError:
            return False

    def issues(self, state: str = "open") -> List[Dict[str, Any]]:
        """List issues. Raises rather than returning [] on failure: triage
        that silently reports "nothing unclaimed" because the API hiccuped
        would be worse than no triage at all."""
        args = ["issue", "list", "--state", state, "--limit", "200",
                "--json", self.ISSUE_FIELDS]
        if self.repo:
            args += ["--repo", self.repo]
        data = self.gh_json(args, timeout=180)
        # `gh issue list` never returns pull requests, but a caller reaching
        # for the REST API would get them, so filter either way.
        return [i for i in (data or []) if "pull_request" not in i]

    def assign_issue(self, number: int, user: str) -> bool:
        """Assign. Returns False if GitHub refused, so the caller reports it
        rather than claiming success."""
        status, _ = self.api(
            "PATCH", f"repos/{self.repo}/issues/{number}",
            {"assignees": [user]},
        )
        return status in (200, 201)

    def close_issue(self, number: int) -> bool:
        status, _ = self.api(
            "PATCH", f"repos/{self.repo}/issues/{number}", {"state": "closed"}
        )
        return status in (200, 201)

    def reopen_issue(self, number: int) -> bool:
        status, _ = self.api(
            "PATCH", f"repos/{self.repo}/issues/{number}", {"state": "open"}
        )
        return status in (200, 201)


# ---------------------------------------------------------------------------
# Reading issue and pull request text
# ---------------------------------------------------------------------------

def parse_criteria(body: str) -> List[Tuple[bool, str]]:
    """Acceptance criteria from an issue body: [(checked, text), ...]."""
    return [(m.group(1).lower() == "x", m.group(2))
            for m in CRITERIA_RE.finditer(body or "")]


def parse_verified_files(body: str) -> List[str]:
    """The files an issue says its fix should touch."""
    match = VERIFIED_FILES_RE.search(body or "")
    if not match:
        return []
    return [m.group(1).strip() for m in FILE_ITEM_RE.finditer(match.group(1))]


def strip_code(text: str) -> str:
    """Remove fenced code blocks, so an example `#42` is not read as a link."""
    return FENCED_RE.sub(" ", text or "")


def linked_issues(body: str) -> Dict[int, str]:
    """Issues a pull request refers to: {number: 'closing'|'mentioned'}.

    Only an explicit closing keyword (`fixes`, `closes`, `resolves`) marks an
    issue as closing. Everything else is a mention, and a mention never
    causes a close -- GitHub itself only auto-closes on those keywords, and
    neither does this tool.
    """
    text = strip_code(body)
    links: Dict[int, str] = {}
    for match in CLOSING_KEYWORD_RE.finditer(text):
        for number in re.findall(r"#(\d+)", match.group(3)):
            links[int(number)] = "closing"
    for number in MENTION_RE.findall(text):
        links.setdefault(int(number), "mentioned")
    return links


def volunteer_evidence(issue: Dict[str, Any], user: str) -> Optional[Dict[str, Any]]:
    """The comment in which `user` asked to work on this issue, if any."""
    wanted = user.lower()
    for comment in issue.get("comments") or []:
        author = ((comment.get("author") or {}).get("login") or "")
        if author.lower() != wanted:
            continue
        if VOLUNTEER_RE.search(comment.get("body") or ""):
            return comment
    return None


def assignee_logins(issue: Dict[str, Any]) -> List[str]:
    return sorted(((a.get("login") or "") for a in (issue.get("assignees") or [])),
                  key=str.lower)


def test_commands_for(labels: Sequence[str]) -> List[str]:
    names = {l.lower() for l in labels or []}
    commands = [cmd for area, cmd in AREA_TESTS if area in names]
    return commands or [DEFAULT_TEST_COMMAND]


def classify_findings(result: review_pr.ReviewResult) -> Dict[str, List[Any]]:
    """Confirmed defects, suggestions, and guesses -- kept apart on purpose.

    Confirmed: blocking and important findings that come from reading the
    diff, the checks, or the suite. Suggestions: everything minor.
    Uncertainty: the two heuristic checks, which are pattern matching and
    say so.
    """
    confirmed, suggestions, uncertain = [], [], []
    for finding in result.findings:
        if finding.code in HEURISTIC_CODES:
            uncertain.append(finding)
        elif finding.severity == "MINOR":
            suggestions.append(finding)
        else:
            confirmed.append(finding)
    return {"confirmed": confirmed, "suggestions": suggestions,
            "uncertain": uncertain}


# ---------------------------------------------------------------------------
# Command: triage
# ---------------------------------------------------------------------------

def suitable_for_contribution(issue: Dict[str, Any],
                               claimed_by_others: Sequence[str]) -> bool:
    """An issue is worth offering when it is open, unclaimed, and labelled
    as suitable work."""
    if (issue.get("state") or "").upper() != "OPEN":
        return False
    if assignee_logins(issue):
        return False
    if claimed_by_others:
        return False
    if issue.get("locked"):
        return False
    return True


def build_triage(gh: IssuesGitHub, labels: Sequence[str],
                 limit: int = 12) -> Dict[str, Any]:
    """Gather unclaimed issues with the context a contributor needs."""
    issues = gh.issues("open")
    wanted = {l.lower() for l in labels} if labels else None

    rows: List[Dict[str, Any]] = []
    claimed: List[Dict[str, Any]] = []
    for issue in issues:
        number = issue.get("number")
        names = sorted({(l.get("name") or "") for l in issue.get("labels") or []})
        others = sorted({
            (c.get("author") or {}).get("login") or ""
            for c in issue.get("comments") or []
            if VOLUNTEER_RE.search(c.get("body") or "")
        } - {""})
        body = issue.get("body") or ""
        criteria = parse_criteria(body)
        entry = {
            "number": number,
            "title": issue.get("title") or "",
            "labels": names,
            "assignees": assignee_logins(issue),
            "claimed_by": others,
            "verified_files": parse_verified_files(body),
            "criteria_total": len(criteria),
            "criteria_done": sum(1 for done, _ in criteria if done),
            "tests": test_commands_for(names),
            "suitable": False,
        }
        if not suitable_for_contribution(issue, others):
            if not entry["assignees"] and others:
                entry["reason"] = (
                    f"commented on by {', '.join(others)}; ask whether they "
                    "are still on it before offering it to somebody else")
                claimed.append(entry)
            continue
        if wanted is not None and not (set(names) & wanted):
            continue
        entry["suitable"] = True
        rows.append(entry)

    def rank(row: Dict[str, Any]) -> Tuple[int, int, int]:
        names = {n.lower() for n in row["labels"]}
        tier = 0 if "good first issue" in names else 1
        return (tier, -row["criteria_total"], row["number"])

    rows.sort(key=rank)
    return {
        "issues": rows[:limit],
        "claimed": claimed,
        "total_open": len(issues),
        "total_suitable": len(rows),
    }


def render_triage(data: Dict[str, Any]) -> str:
    out = []
    out.append("=" * 78)
    out.append("Unclaimed issues, best first")
    out.append("=" * 78)
    out.append(f"{data['total_open']} open issues; "
               f"{data['total_suitable']} unclaimed and offered as suitable.")
    out.append("")
    if not data["issues"]:
        out.append("Nothing unclaimed matches. Issues move quickly; re-run "
                   "later, or widen the filter with --label.")
    for row in data["issues"]:
        labels = ", ".join(row["labels"]) or "no labels"
        out.append(f"#{row['number']}  {row['title']}")
        out.append(f"    labels      : {labels}")
        if row["verified_files"]:
            out.append(f"    touches     : {', '.join(row['verified_files'])}")
        else:
            out.append("    touches     : not stated in the issue")
        if row["criteria_total"]:
            out.append(f"    criteria    : {row['criteria_done']} of "
                       f"{row['criteria_total']} acceptance criteria recorded")
        out.append(f"    run         : {'; '.join(row['tests'])}")
        out.append(f"    claim       : unclaimed -- comment on the issue to "
                   f"ask for it")
        out.append("")
    if data["claimed"]:
        out.append("-" * 78)
        out.append("Already spoken for, but nobody assigned (check before "
                   "offering these):")
        for row in data["claimed"]:
            out.append(f"#{row['number']}  {row['title']}")
            out.append(f"    commented by : {', '.join(row['claimed_by'])}")
        out.append("")
    out.append("To assign one: python scripts/contributor.py assign ISSUE "
               "--user USERNAME")
    out.append("(assignment still requires that person to have asked for it "
               "in a comment)")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Command: assign
# ---------------------------------------------------------------------------

def build_assignment(gh: IssuesGitHub, number: int, user: str,
                     comment: bool) -> Dict[str, Any]:
    """Decide whether an assignment is safe, and perform it if so.

    Refuses, without writing anything, when the issue is missing or closed,
    when somebody else already holds it, when the same person is already
    assigned (so re-running is a no-op), or when there is no comment from
    that person asking for the work.
    """
    outcome: Dict[str, Any] = {
        "number": number, "user": user, "assigned": False,
        "action": "", "reason": "", "evidence": "", "commented": False,
    }
    try:
        issue = gh.issue(number)
    except ReviewError as exc:
        outcome["action"] = "refused"
        outcome["reason"] = str(exc)
        return outcome

    if (issue.get("state") or "").upper() != "OPEN":
        outcome["action"] = "refused"
        outcome["reason"] = f"issue #{number} is not open, so it cannot be assigned"
        return outcome

    holders = assignee_logins(issue)
    if holders and user.lower() not in {h.lower() for h in holders}:
        outcome["action"] = "refused"
        outcome["reason"] = (f"issue #{number} is already assigned to "
                             f"{', '.join(holders)}; ask them first rather "
                             "than taking it away")
        return outcome
    if holders:
        outcome["action"] = "already-assigned"
        outcome["reason"] = (f"{user} is already assigned to issue #{number}; "
                             "nothing to do")
        return outcome

    evidence = volunteer_evidence(issue, user)
    if evidence is None:
        outcome["action"] = "refused"
        outcome["reason"] = (
            f"{user} has not asked for issue #{number}. Assignment needs a "
            "comment from them on the issue -- this tool never assigns work "
            "to somebody who has not volunteered, and never mentions them "
            "out of the blue.")
        return outcome

    outcome["evidence"] = (evidence.get("body") or "").strip()
    outcome["evidence_url"] = evidence.get("html_url") or issue.get("url") or ""

    # Checked here, not earlier: it costs an extra API call, so it is only
    # worth making once every other reason to refuse has been ruled out.
    if gh.issue_locked(number):
        outcome["action"] = "refused"
        outcome["reason"] = (f"issue #{number} is locked for conversation, so "
                             "nothing can be posted on it")
        return outcome

    if not gh.assign_issue(number, user):
        outcome["action"] = "failed"
        outcome["reason"] = (f"GitHub refused the assignment of issue "
                             f"#{number} to {user} -- check that you have "
                             "permission to assign issues in this repository")
        return outcome

    outcome["assigned"] = True
    outcome["action"] = "assigned"

    if comment:
        body = (f"@{user} this issue is yours -- thanks for picking it up. "
                f"Anything unclear in the issue, ask here and I will answer.")
        if gh.comment(number, f"{MARKER}\n{body}"):
            outcome["commented"] = True
    return outcome


def render_assignment(outcome: Dict[str, Any]) -> str:
    number, user = outcome["number"], outcome["user"]
    action = outcome["action"]
    lines = []
    if action == "assigned":
        lines.append(f"ISSUED: issue #{number} is now assigned to {user}.")
        if outcome.get("evidence"):
            quote = outcome["evidence"].splitlines()[0][:120]
            lines.append(f"  basis: their comment asking for the work "
                         f'("{quote}")')
        if outcome.get("commented"):
            lines.append("  also posted a short reply on the issue")
        else:
            lines.append("  no comment posted -- GitHub notifies them of the "
                         "assignment; pass --comment to also reply")
    elif action == "already-assigned":
        lines.append(f"NOTHING TO DO: {outcome['reason']}")
    elif action == "failed":
        lines.append(f"FAILED: {outcome['reason']}")
    else:
        lines.append(f"REFUSED: {outcome['reason']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Command: review
# ---------------------------------------------------------------------------

def build_review_with_context(gh: IssuesGitHub, number: int,
                              repo_info: Dict[str, Any], run_tests: bool,
                              test_timeout: int = 900
                              ) -> Dict[str, Any]:
    """The engine's review, plus what the linked issues say.

    Every finding and gate here comes from `review_pr.build_review`. This
    adds only issue context: which issues the body links, whether they are
    open, and what they still ask for.
    """
    result = review_pr.build_review(
        gh, number, repo_info, run_tests=run_tests, test_timeout=test_timeout)

    links = linked_issues(result.pr.get("body") or "")
    context = []
    for issue_number, kind in sorted(links.items()):
        entry: Dict[str, Any] = {"number": issue_number, "kind": kind}
        try:
            issue = gh.issue(issue_number)
        except ReviewError as exc:
            entry["error"] = str(exc)
            context.append(entry)
            continue
        body = issue.get("body") or ""
        criteria = parse_criteria(body)
        entry.update({
            "state": (issue.get("state") or "").upper(),
            "title": issue.get("title") or "",
            "criteria_total": len(criteria),
            "criteria_open": [text for done, text in criteria if not done],
            "verified_files": parse_verified_files(body),
        })
        context.append(entry)

    return {"result": result, "linked": context,
            "findings": classify_findings(result)}


def render_review(pack: Dict[str, Any], user: str = "") -> str:
    result = pack["result"]
    out = [review_pr.render_report(result, user=user)]

    out.append("")
    out.append("Linked issues")
    out.append("-" * 78)
    if not pack["linked"]:
        out.append("  No issues are linked in the description. If this fixes "
                   "one, add \"Fixes #N\" so it closes on merge.")
    for entry in pack["linked"]:
        if entry.get("error"):
            out.append(f"  #{entry['number']} ({entry['kind']}) -- "
                       f"{entry['error']}")
            continue
        verb = ("closes on merge" if entry["kind"] == "closing"
                else "mentioned only -- will NOT be closed by this PR")
        out.append(f"  #{entry['number']} {entry['title'][:52]}")
        out.append(f"      {entry['state']}, {verb}")
        if entry["verified_files"]:
            out.append(f"      expects changes in: "
                       f"{', '.join(entry['verified_files'])}")
        if entry["criteria_total"]:
            out.append(f"      acceptance criteria: "
                       f"{entry['criteria_total'] - len(entry['criteria_open'])}"
                       f"/{entry['criteria_total']} ticked")
            for text in entry["criteria_open"][:6]:
                out.append(f"        [ ] {text[:70]}")

    out.append("")
    out.append("What is confirmed, what is a suggestion, what is a guess")
    out.append("-" * 78)
    groups = pack["findings"]
    out.append(f"  confirmed defects ({len(groups['confirmed'])}): found by "
               "reading the diff, the checks, or the test suite")
    for finding in groups["confirmed"]:
        out.append(f"    [{finding.severity}] {finding.code}: "
                   f"{finding.message[:88]}")
    if not groups["confirmed"]:
        out.append("    (none)")
    out.append(f"  suggestions ({len(groups['suggestions'])}): worth "
               "considering, never a blocker")
    for finding in groups["suggestions"]:
        out.append(f"    {finding.code}: {finding.message[:88]}")
    if not groups["suggestions"]:
        out.append("    (none)")
    out.append(f"  uncertainty ({len(groups['uncertain'])}): pattern matching, "
               "not verified findings -- read the diff yourself")
    for finding in groups["uncertain"]:
        out.append(f"    {finding.code}: {finding.message[:88]}")
    if not groups["uncertain"]:
        out.append("    (none)")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Command: finalize
# ---------------------------------------------------------------------------

def verify_closable(issue: Dict[str, Any],
                    changed_files: Sequence[str]) -> Dict[str, Any]:
    """Evidence about whether a linked issue is genuinely done.

    The tool can check three things objectively: the issue is still open, the
    pull request touches at least one file the issue itself names, and the
    merge gates pass. It cannot tick the issue's acceptance checkboxes --
    those describe judgement ("language is welcoming"), and pretending to
    verify them would be worse than admitting it. Unchecked criteria are
    therefore reported for a human, not silently passed.
    """
    body = issue.get("body") or ""
    criteria = parse_criteria(body)
    named = parse_verified_files(body)
    touched = sorted(set(named) & set(changed_files)) if named else []
    state = (issue.get("state") or "").upper()

    if state != "OPEN":
        verdict = "skip"
        why = f"already {state.lower()}"
    elif named and not touched:
        verdict = "hold"
        why = (f"the pull request touches none of the files this issue names "
               f"({', '.join(named[:4])}), so it may not address it")
    else:
        verdict = "close"
        why = ("the description links it with a closing keyword and the "
               "change touches the area the issue describes"
               if named else
               "the description links it with a closing keyword; this issue "
               "names no specific files, so check its criteria by eye")

    return {
        "number": issue.get("number"),
        "state": state,
        "title": issue.get("title") or "",
        "verdict": verdict,
        "why": why,
        "named_files": named,
        "touched": touched,
        "criteria_total": len(criteria),
        "criteria_open": [text for done, text in criteria if not done],
    }


def build_finalize(gh: IssuesGitHub, number: int, repo_info: Dict[str, Any],
                   run_tests: bool, test_timeout: int = 900) -> Dict[str, Any]:
    """Run the review and decide what a merge would need. Writes nothing.

    `merge_method` is deliberately absent: which method is used is decided
    inside `perform_merge`, from the repository's own configuration, and is
    never a reason to skip a gate here.
    """
    result = review_pr.build_review(
        gh, number, repo_info, run_tests=run_tests, test_timeout=test_timeout)

    links = linked_issues(result.pr.get("body") or "")
    changed = [f.get("path") for f in (result.pr.get("files") or [])]
    checks: List[Dict[str, Any]] = []
    gates = list(result.gates)

    for issue_number, kind in sorted(links.items()):
        entry: Dict[str, Any] = {"number": issue_number, "kind": kind}
        try:
            issue = gh.issue(issue_number)
        except ReviewError as exc:
            entry["verdict"] = "unknown"
            entry["why"] = str(exc)
            checks.append(entry)
            continue
        if kind == "closing":
            entry.update(verify_closable(issue, changed))
            entry["kind"] = kind
            if entry["verdict"] == "hold":
                gates.append(Gate(
                    f"Issue #{issue_number} is addressed",
                    False,
                    entry["why"],
                    manual_fix="If this pull request does fix it, say so in "
                               "the description with a closing keyword; if "
                               "it does not, remove the reference so the "
                               "issue stays open.",
                ))
        else:
            # Not a closing link, so nothing here is evidence of anything:
            # report it and leave it open. The title is carried through so
            # the report can name the issue it is talking about.
            entry.update({
                "title": issue.get("title") or "",
                "verdict": "mention-only",
                "why": "referenced without a closing keyword; it stays open",
            })
        checks.append(entry)

    return {"result": result, "issues": checks, "gates": gates,
            "author": ((result.pr.get("author") or {}).get("login") or ""),
            "merged": (result.pr.get("state") or "").upper() == "MERGED"}


def render_premerge(pack: Dict[str, Any], user: str = "") -> str:
    result = pack["result"]
    out = [review_pr.render_report(result, user=user)]
    out.append("")
    out.append("Linked issues, checked against what they ask for")
    out.append("-" * 78)
    if not pack["issues"]:
        out.append("  None linked. Merging will close nothing.")
    for entry in pack["issues"]:
        if entry.get("verdict") == "unknown":
            out.append(f"  #{entry['number']} ({entry['kind']}) -- "
                       f"{entry['why']}")
            continue
        mark = {"close": "WILL CLOSE", "hold": "HELD OPEN",
                "skip": "ALREADY CLOSED", "mention-only": "STAYS OPEN"}
        out.append(f"  #{entry['number']} {entry['title'][:50]}")
        out.append(f"      {mark.get(entry['verdict'], 'STAYS OPEN')} -- "
                   f"{entry['why']}")
        if entry.get("criteria_open"):
            out.append(f"      {len(entry['criteria_open'])} acceptance "
                       f"criteria still unticked -- confirm by eye:")
            for text in entry["criteria_open"][:6]:
                out.append(f"        [ ] {text[:70]}")
    out.append("")
    out.append("Merge gate")
    out.append("-" * 78)
    for gate in pack["gates"]:
        out.append(gate.line())
        if not gate.ok and gate.manual_fix:
            out.append(f"         fix: {gate.manual_fix}")
    return "\n".join(out)


def perform_merge(gh: IssuesGitHub, pack: Dict[str, Any], number: int,
                  repo_info: Dict[str, Any],
                  merge_method: Optional[str],
                  close_issues: bool = True) -> Dict[str, Any]:
    """Merge, then confirm, then close the verified issues. Writes.

    Called only after `build_finalize` reported every gate passing and the
    operator passed `--merge`. The PR is re-read afterwards: nothing is
    closed and nobody is thanked on the strength of an assumption that the
    merge worked.

    `close_issues=False` (`--no-close`) suppresses issue closure here, not
    in the reporting -- a flag that only changed what the output said would
    be worse than no flag at all.
    """
    action: Dict[str, Any] = {"merged": False, "closed": [], "thanked": False,
                              "method": "", "detail": ""}
    if merge_method and not review_pr._method_allowed(repo_info, merge_method):
        # `choose_method` falls back to any other enabled method, which is
        # right when nobody asked for a particular one and wrong when they
        # did: silently squashing a pull request the maintainer asked to
        # merge-commit is not honouring the request.
        action["detail"] = (f"the repository does not allow a {merge_method} "
                            f"merge, so --merge-method {merge_method} cannot "
                            "be honoured; nothing was merged")
        return action
    method = review_pr.choose_method(repo_info, merge_method)
    if method is None:
        action["detail"] = ("no merge method is enabled on this repository, "
                            "so it cannot be merged at all")
        return action

    ok, detail = gh.merge(number, method)
    action["method"] = method
    if not ok:
        action["detail"] = detail or "GitHub refused the merge"
        return action

    # Re-read rather than trust the response: a merge can be rejected by
    # branch protection even when the command looks like it ran.
    try:
        state = (gh.pr(number).get("state") or "").upper()
    except ReviewError as exc:
        action["detail"] = (f"the merge command was accepted but the pull "
                            f"request could not be re-read ({exc}); nothing "
                            "was closed and nobody was thanked")
        return action
    if state != "MERGED":
        action["detail"] = (f"the merge command was accepted but #{number} "
                            f"reports state {state}; nothing was closed and "
                            "nobody was thanked")
        return action

    action["merged"] = True
    action["detail"] = detail or f"merged with a {method}"

    if not close_issues:
        action["detail"] += "; linked issues left open by request"
        return action

    for entry in pack["issues"]:
        if entry.get("verdict") != "close":
            continue
        try:
            fresh = gh.issue(entry["number"])
        except ReviewError:
            continue
        if (fresh.get("state") or "").upper() == "OPEN":
            if gh.close_issue(entry["number"]):
                action["closed"].append(entry["number"])
    return action


def post_thanks(gh: IssuesGitHub, number: int, author: str) -> Tuple[bool, str]:
    """Thank the contributor -- only once the merge is confirmed.

    The pull request is re-read here as well, so this cannot praise a merge
    that did not happen, and the marker in the comment makes a second run a
    no-op.
    """
    if not author:
        return False, "the pull request has no author to thank"
    try:
        state = (gh.pr(number).get("state") or "").upper()
    except ReviewError as exc:
        return False, f"could not re-read #{number}: {exc}"
    if state != "MERGED":
        return False, (f"#{number} is {state or 'in an unknown state'}, not "
                       "merged; no thank-you was posted")

    body = (MARKER + "\n"
            + THANKS_TEMPLATE.format(user=author, number=number))
    for comment in gh.issue_comments(number):
        if MARKER in (comment.get("body") or ""):
            return False, "a thank-you was already posted on this pull request"
    if gh.comment(number, body):
        return True, "thanked the contributor"
    return False, "GitHub refused the comment"


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contributor.py",
        description="Manage contributors on Critique: triage, assign, review, "
                    "finalize. Reviews are performed by review_pr.py; this "
                    "adds the issue-side work.",
    )
    sub = parser.add_subparsers(dest="command")

    p_triage = sub.add_parser("triage", help="find unclaimed issues")
    p_triage.add_argument("--label", action="append", default=[],
                          help="only issues carrying this label (repeatable)")
    p_triage.add_argument("--limit", type=int, default=12)
    p_triage.add_argument("--json", action="store_true", dest="as_json")
    p_triage.add_argument("--repo", default=None, help="OWNER/NAME")

    p_assign = sub.add_parser("assign", help="assign an issue to a volunteer")
    p_assign.add_argument("number", type=int, help="issue number")
    p_assign.add_argument("--user", required=True, help="GitHub login")
    p_assign.add_argument("--comment", action="store_true",
                          help="also post a short reply on the issue")
    p_assign.add_argument("--repo", default=None, help="OWNER/NAME")

    p_review = sub.add_parser("review", help="read-only review with issue "
                                             "context")
    p_review.add_argument("number", type=int, help="pull request number")
    p_review.add_argument("--request-changes", action="store_true")
    p_review.add_argument("--repo", default=None)
    p_review.add_argument("--skip-tests", action="store_true")
    p_review.add_argument("--test-timeout", type=int, default=900)

    p_final = sub.add_parser("finalize", help="merge, close verified issues, "
                                              "thank the contributor")
    p_final.add_argument("number", type=int, help="pull request number")
    p_final.add_argument("--merge", action="store_true",
                         help="required; nothing merges without it")
    p_final.add_argument("--merge-method", choices=["merge", "squash", "rebase"],
                         default=None)
    p_final.add_argument("--no-close", action="store_true",
                         help="merge but leave every issue open")
    p_final.add_argument("--no-thanks", action="store_true",
                         help="skip the thank-you comment after a confirmed "
                              "merge")
    p_final.add_argument("--repo", default=None)
    p_final.add_argument("--skip-tests", action="store_true")
    p_final.add_argument("--test-timeout", type=int, default=900)
    return parser


def main(argv: Optional[Sequence[str]] = None,
         gh: Optional[IssuesGitHub] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 2
    if shutil_which("gh") is None and gh is None:
        print("gh CLI not found. Install it: https://cli.github.com",
              file=sys.stderr)
        return 2

    gh = gh or IssuesGitHub()
    try:
        if not gh.repo:
            gh.repo = resolve_repo(getattr(args, "repo", None))
        user = gh.verify_auth()
        repo_info = gh.repo_info()
    except ReviewError as exc:
        print(f"cannot start: {exc}", file=sys.stderr)
        return 2

    if args.command == "triage":
        try:
            data = build_triage(gh, args.label, limit=args.limit)
        except ReviewError as exc:
            print(f"cannot list issues: {exc}", file=sys.stderr)
            return 2
        if args.as_json:
            print(json.dumps(data, indent=2))
        else:
            print(render_triage(data))
        return 0

    if args.command == "assign":
        outcome = build_assignment(gh, args.number, args.user, args.comment)
        print(render_assignment(outcome))
        return 0 if outcome["action"] in ("assigned", "already-assigned") else 1

    if args.command == "review":
        try:
            pack = build_review_with_context(
                gh, args.number, repo_info, run_tests=not args.skip_tests,
                test_timeout=args.test_timeout)
        except ReviewError as exc:
            print(f"cannot review #{args.number}: {exc}", file=sys.stderr)
            return 2
        print(render_review(pack, user=user))
        exit_code = 0 if pack["result"].status == "READY" else 1
        if args.request_changes:
            print("")
            if pack["result"].blocking or pack["result"].important:
                ok, detail = review_pr.post_review(
                    gh, pack["result"], args.number)
                print(("Posted: " if ok else "Not posted: ") + detail)
                if not ok:
                    exit_code = 1
            else:
                print("No blocking or important findings, so nothing was "
                      "posted.")
        return exit_code

    # finalize
    if not args.merge:
        print("finalize without --merge only reports what a merge would "
              "need; nothing was merged, closed, or posted.\n", file=sys.stderr)
    try:
        pack = build_finalize(
            gh, args.number, repo_info,
            run_tests=not args.skip_tests, test_timeout=args.test_timeout)
    except ReviewError as exc:
        print(f"cannot finalize #{args.number}: {exc}", file=sys.stderr)
        return 2
    print(render_premerge(pack, user=user))
    if not args.merge:
        return 0 if pack["result"].status == "READY" else 1

    # Checked before the gates: a pull request that is already merged has
    # nothing left to gate, and refusing here would report failure for an
    # outcome that already happened. No writes follow -- this run merged
    # nothing, so it claims nothing.
    if pack["merged"]:
        print(f"#{args.number} is already merged; nothing to do.")
        return 0

    print("")
    failed = [g for g in pack["gates"] if not g.ok]
    if failed:
        print(f"REFUSING TO MERGE #{args.number}: every gate must pass, and "
              "--merge does not override a failure.")
        for gate in failed:
            print(f"  failed: {gate.name} -- {gate.detail}")
            if gate.manual_fix:
                print(f"         fix: {gate.manual_fix}")
        return 1

    print(f"Merging #{args.number}...")
    action = perform_merge(gh, pack, args.number, repo_info, args.merge_method,
                           close_issues=not args.no_close)
    print(action["detail"])
    if not action["merged"]:
        return 1

    closable = [e["number"] for e in pack["issues"]
                if e.get("verdict") == "close"]
    if args.no_close:
        print(f"Left {len(closable)} linked issue(s) open (--no-close).")
    else:
        closed = set(action["closed"])
        for number in closable:
            if number in closed:
                print(f"Closed issue #{number}, which this pull request "
                      "resolved.")
            else:
                print(f"Issue #{number} was already closed by GitHub's own "
                      "closing keyword handling.")
    for entry in pack["issues"]:
        if entry.get("verdict") in ("hold", "mention-only"):
            print(f"Issue #{entry['number']} left open: {entry['why']}")

    if not args.no_thanks:
        ok, detail = post_thanks(gh, args.number, pack["author"])
        print(("Thanked: " if ok else "Not thanked: ") + detail)
    return 0


def shutil_which(name: str) -> Optional[str]:
    """`shutil.which`, wrapped in one place so a test can stand in for a
    missing `gh` without monkeypatching the whole module."""
    return shutil.which(name)


if __name__ == "__main__":
    sys.exit(main())
