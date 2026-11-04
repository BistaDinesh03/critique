#!/usr/bin/env python3
"""Review a Critique pull request with one command.

    python scripts/review_pr.py 123                      # review only (default)
    python scripts/review_pr.py 123 --request-changes    # post a review
    python scripts/review_pr.py 123 --merge              # merge if every gate passes

The default is deliberately non-destructive: it reads the pull request,
analyses the diff, optionally runs the test suite in an isolated clone, and
prints a report. Nothing is posted and nothing is merged unless asked.

What this script does not do:

  * It never pushes to a contributor's branch and never touches their fork.
  * It never bypasses branch protection, and `--merge` never overrides a
    failed gate.
  * It never treats its own static analysis as a substitute for reading the
    diff. Every finding carries evidence, and anything inferred rather than
    observed says so.

Authentication and repository identity come from the `gh` CLI and the local
`origin` remote. When the suite is run, it runs in a throwaway clone with a
stripped environment, so contributor code never sees the maintainer's tokens
or `.env`.

Exit codes:
    0   review completed and the pull request is READY (or a merge was done)
    1   review completed but the pull request is BLOCKED or CHANGES_REQUESTED
    2   the review could not run (bad usage, no gh, no auth, PR not found)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

# Left on every review and comment we post, so a later run can tell its own
# notes from a human's and avoid saying the same thing twice.
REVIEW_MARKER = "<!-- critique-review-pr -->"

# Paths that change how the project runs, depart from documented security
# behaviour, or record analytics. Changing them is legitimate, but a reviewer
# should be told why, so it is always worth one question.
SENSITIVE_PREFIXES = (
    ".github/",
    "render.yaml",
    "SECURITY.md",
    ".env.example",
    "backend/app/routes_analytics.py",
    "docs/analytics-snapshot.",
)

# Names that are file names rather than topics, so they cannot make an
# unrelated-looking path look related (or vice versa).
NON_TOPIC_TOKENS = {
    "contributing", "readme", "license", "changelog", "security", "docs",
    "doc", "file", "files", "source", "src", "test", "tests", "testmain",
    "html", "json", "yaml", "yml", "lock", "config", "index", "main",
    "static", "backend", "frontend", "app", "scripts",
}

# Documentation-only pull requests may be larger than changes that touch
# running code.
DOCS_SUFFIXES = (".md", ".svg", ".html", ".txt", ".rst")
SCOPE_CODE_FILES = 20
SCOPE_CODE_LINES = 1000
SCOPE_DOCS_FILES = 30
SCOPE_DOCS_LINES = 3000

# Patterns that mean "ask before merging". Each carries its reasoning, so the
# report can explain itself without the reader trusting a bare rule name.
UNSAFE_PATTERNS: Tuple[Tuple[str, str, str], ...] = (
    (r"shell\s*=\s*True", "subprocess with shell=True",
     "shell interpolation is the classic command-injection path; pass an "
     "argument list instead"),
    (r"\beval\s*\(", "eval()",
     "eval on anything derived from input executes it; use an explicit "
     "parser"),
    (r"\bexec\s*\(", "exec()",
     "exec turns text into running code; nothing in this project needs it"),
    (r"os\.system\s*\(", "os.system()",
     "fixed command string plus interpolation; use subprocess with a list"),
    (r"pickle\.loads?\s*\(", "pickle.loads()",
     "unpickling untrusted data executes arbitrary code"),
    (r"\byaml\.load\s*\(", "yaml.load() without SafeLoader",
     "an unsafe loader can construct arbitrary objects; use yaml.safe_load"),
    (r"verify\s*=\s*False", "TLS verification disabled",
     "disabling certificate checks exposes traffic to interception"),
    (r"CERT_NONE", "certificate checks disabled",
     "the same problem as verify=False, at the ssl layer"),
    (r"git\s+push\s+.*--force", "force push",
     "force-pushing rewrites history other people may have pulled"),
    (r"--no-verify", "hooks bypassed",
     "skipping pre-commit hooks usually hides a check the project wants"),
    (r"chmod\s+777", "world-writable permissions",
     "777 lets any local user modify the file"),
    (r"rm\s+-rf\s+/", "recursive delete from root",
     "this deletes a filesystem, not a build directory"),
    (r"pytest\.mark\.skip", "tests skipped",
     "newly skipped tests stop covering the behaviour they were written for"),
    (r"pytest\.mark\.xfail", "tests marked expected-failure",
     "xfail hides a regression unless it is expected-failure by design"),
    (r"GITHUB_TOKEN\s*=\s*[\"'][^\"']{8,}", "hard-coded GitHub token",
     "a token in the diff is a leak, even in a test fixture"),
)

# High-precision secret shapes. Precision matters more than recall here: a
# false "you leaked a secret" is worse than a missed exotic format, because it
# trains the maintainer to ignore the report.
SECRET_PATTERNS: Tuple[Tuple[str, str], ...] = (
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "a private key block"),
    (r"AKIA[0-9A-Z]{16}", "an AWS access key id"),
    (r"gh[pousr]_[A-Za-z0-9]{20,}", "a GitHub token"),
    (r"github_pat_[A-Za-z0-9_]{20,}", "a fine-grained GitHub token"),
    (r"xox[baprs]-[A-Za-z0-9-]{10,}", "a Slack token"),
    (r"AIza[0-9A-Za-z_\-]{35}", "a Google API key"),
    (r"sk-[A-Za-z0-9]{20,}", "an OpenAI-style secret key"),
    (r"(?i)(password|passwd|secret|api[_-]?key)\s*[:=]\s*[\"'][^\"'\s]{12,}[\"']",
     "a hard-coded credential"),
)

# Files that are never a legitimate part of a pull request.
FORBIDDEN_PATHS: Tuple[Tuple[str, str], ...] = (
    (r"(^|/)\.env$", ".env is gitignored and carries local secrets"),
    (r"\.db[0-9]*$", "database files are build artefacts and bloat the diff"),
    (r"__pycache__/", "byte-compiled output does not belong in a commit"),
    (r"node_modules/", "vendored dependencies do not belong in a commit"),
    (r"\.pytest_cache/", "test caches are local state"),
)

SOURCE_PREFIXES = ("backend/app/", "backend/routes_", "backend/models",
                   "static/", "frontend/")
TEST_PREFIXES = ("backend/tests/", "tests/")

# Findings that describe the state of the review rather than the code, and so
# must not influence the duplicate-detection signature.
SELF_REFERENTIAL = {"CHANGES_REQUESTED_EXISTING"}


@dataclass
class Finding:
    """One thing a reviewer would say out loud about this pull request."""

    severity: str          # BLOCKING | IMPORTANT | MINOR
    code: str              # short stable id, e.g. "SECRET", "TESTS_MISSING"
    message: str
    why: str = ""
    path: str = ""
    line: int = 0
    fix: str = ""
    evidence: str = ""

    def location(self) -> str:
        if not self.path:
            return ""
        return f"{self.path}:{self.line}" if self.line else self.path


@dataclass
class Gate:
    """One condition the merge path requires. Gates do not bend for --merge."""

    name: str
    ok: bool
    detail: str
    manual_fix: str = ""

    def line(self) -> str:
        mark = "x" if self.ok else " "
        return f"  [{mark}] {self.name} -- {self.detail}"


@dataclass
class ReviewResult:
    pr: Dict[str, Any]
    findings: List[Finding] = field(default_factory=list)
    gates: List[Gate] = field(default_factory=list)
    checks: List[Dict[str, Any]] = field(default_factory=list)
    test_head: Optional[Dict[str, Any]] = None
    test_base: Optional[Dict[str, Any]] = None
    repo: Dict[str, Any] = field(default_factory=dict)
    protection: Union[Dict[str, Any], BranchProtectionUnreadable, None] = None
    notes: List[str] = field(default_factory=list)

    @property
    def blocking(self) -> List[Finding]:
        return [f for f in self.findings if f.severity == "BLOCKING"]

    @property
    def important(self) -> List[Finding]:
        return [f for f in self.findings if f.severity == "IMPORTANT"]

    @property
    def minor(self) -> List[Finding]:
        return [f for f in self.findings if f.severity == "MINOR"]

    @property
    def gates_ok(self) -> bool:
        return all(g.ok for g in self.gates)

    @property
    def status(self) -> str:
        """READY, CHANGES_REQUESTED, or BLOCKED.

        BLOCKED means the pull request cannot be judged at all yet: closed,
        draft, conflicting, wrong base, or checks failing. Everything a
        contributor can fix is CHANGES_REQUESTED instead.
        """
        unsafe = {
            "CLOSED", "MERGED", "DRAFT", "WRONG_BASE", "CONFLICT",
            "UNREACHABLE", "CHECKS_FAILED", "CHECKS_RUNNING",
            "CHECKS_UNKNOWN",
        }
        codes = {f.code for f in self.findings}
        if codes & unsafe:
            return "BLOCKED"
        if self.blocking or self.important:
            return "CHANGES_REQUESTED"
        return "READY"

    def signature(self) -> str:
        """Stable hash of what we would say, for duplicate detection.

        Findings that describe the state of the review itself are excluded:
        without that, posting a request for changes would change the next
        run's signature, and every re-run would post again.
        """
        parts = sorted(
            f"{f.severity}:{f.code}:{f.location()}"
            for f in self.findings if f.code not in SELF_REFERENTIAL
        )
        return hashlib.sha1("\n".join(parts).encode("utf-8")).hexdigest()[:12]


class ReviewError(Exception):
    """The review could not run. Deliberately distinct from "has problems"."""


class BranchProtectionUnreadable:
    """The token cannot read branch protection (401/403).

    That is "could not verify", not "nothing is configured": reporting it as
    a missing configuration would tell a maintainer to enable something that
    may already be enabled.
    """

    def __init__(self, status: int) -> None:
        self.status = status


# ---------------------------------------------------------------------------
# Talking to GitHub
# ---------------------------------------------------------------------------

class GitHub:
    """A thin wrapper over the `gh` CLI.

    Every method returns plain data, so the analysis below never touches the
    network directly -- which is also what lets tests replace this whole class
    with a fake.
    """

    def __init__(self, repo: Optional[str] = None,
                 runner: Any = subprocess.run) -> None:
        self.repo = repo
        self.user = ""
        self._runner = runner

    # -- plumbing ---------------------------------------------------------
    def _run(self, args: Sequence[str], timeout: int = 120):
        proc = self._runner(
            list(args), capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout,
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""

    def gh(self, args: Sequence[str], timeout: int = 120) -> str:
        rc, out, err = self._run(["gh"] + list(args), timeout=timeout)
        if rc != 0:
            raise ReviewError(
                "gh " + " ".join(args[:4]) + " failed: "
                + (err.strip() or out.strip() or f"exit {rc}")
            )
        return out

    def gh_json(self, args: Sequence[str], timeout: int = 120) -> Any:
        try:
            return json.loads(self.gh(args, timeout=timeout))
        except json.JSONDecodeError as exc:      # pragma: no cover
            raise ReviewError(f"gh returned unparseable JSON: {exc}") from exc

    def api(self, method: str, path: str,
            fields: Optional[Dict[str, Any]] = None) -> Tuple[int, str]:
        """Low-level REST call. Returns (status, body) even on failure, so the
        caller can tell "not there" apart from "broken"."""
        args = ["api", "-X", method, path]
        for key, value in (fields or {}).items():
            args += ["-f", f"{key}={value}"]
        proc = self._runner(
            ["gh"] + args, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=120,
        )
        status = 0
        match = re.search(r"\(HTTP\s+(\d{3})\)", proc.stderr or "")
        if match:
            status = int(match.group(1))
        elif proc.returncode == 0:
            status = 200
        return status, (proc.stdout or "")

    # -- identity and authentication --------------------------------------
    def verify_auth(self) -> str:
        status, body = self.api("GET", "user")
        if status != 200 or not body.strip():
            raise ReviewError("gh is not authenticated. Run `gh auth login`.")
        try:
            self.user = json.loads(body).get("login", "")
        except json.JSONDecodeError:
            self.user = ""
        return self.user

    REPO_FIELDS = ",".join([
        "nameWithOwner", "defaultBranchRef", "url", "visibility",
        "mergeCommitAllowed", "squashMergeAllowed", "rebaseMergeAllowed",
        "deleteBranchOnMerge", "viewerDefaultMergeMethod",
        "viewerPermission", "viewerCanAdminister",
    ])

    def repo_info(self) -> Dict[str, Any]:
        args = ["repo", "view"]
        if self.repo:
            args.append(self.repo)
        args += ["--json", self.REPO_FIELDS]
        data = self.gh_json(args)
        default_ref = data.get("defaultBranchRef") or {}
        return {
            "name": data.get("nameWithOwner", self.repo or ""),
            "default_branch": default_ref.get("name", "main"),
            "url": data.get("url", ""),
            "visibility": data.get("visibility", ""),
            "allow_merge_commit": bool(data.get("mergeCommitAllowed", True)),
            "allow_squash_merge": bool(data.get("squashMergeAllowed", True)),
            "allow_rebase_merge": bool(data.get("rebaseMergeAllowed", True)),
            "delete_branch_on_merge": bool(data.get("deleteBranchOnMerge")),
            "viewer_default_merge_method":
                (data.get("viewerDefaultMergeMethod") or "").lower(),
            "viewer_permission": data.get("viewerPermission", ""),
            "can_administer": bool(data.get("viewerCanAdminister")),
        }

    # -- pull requests ----------------------------------------------------
    PR_FIELDS = ",".join([
        "number", "title", "state", "isDraft", "url", "body",
        "baseRefName", "baseRefOid", "headRefName", "headRefOid",
        "mergeable", "mergeStateStatus", "reviewDecision",
        "additions", "deletions", "changedFiles",
        "author", "labels", "createdAt", "updatedAt",
        "headRepositoryOwner", "headRepository",
        "commits", "files", "statusCheckRollup",
    ])

    def pr(self, number: int) -> Dict[str, Any]:
        args = ["pr", "view", str(number), "--json", self.PR_FIELDS]
        if self.repo:
            args += ["--repo", self.repo]
        try:
            return self.gh_json(args)
        except ReviewError as exc:
            lowered = str(exc).lower()
            if "could not resolve to a pullrequest" in lowered \
                    or "not found" in lowered:
                raise ReviewError(f"pull request #{number} was not found")
            raise

    def pr_diff(self, number: int) -> str:
        args = ["pr", "diff", str(number)]
        if self.repo:
            args += ["--repo", self.repo]
        return self.gh(args, timeout=180)

    def _paginate(self, path: str) -> List[Dict[str, Any]]:
        page = 1
        items: List[Dict[str, Any]] = []
        sep = "&" if "?" in path else "?"
        while True:
            status, body = self.api("GET", f"{path}{sep}per_page=100&page={page}")
            if status != 200 or not body.strip():
                break
            try:
                page_items = json.loads(body)
            except json.JSONDecodeError:
                break
            if not isinstance(page_items, list) or not page_items:
                break
            items.extend(page_items)
            if len(page_items) < 100:
                break
            page += 1
        return items

    def reviews(self, number: int) -> List[Dict[str, Any]]:
        return self._paginate(f"repos/{self.repo}/pulls/{number}/reviews")

    def issue_comments(self, number: int) -> List[Dict[str, Any]]:
        return self._paginate(f"repos/{self.repo}/issues/{number}/comments")

    def branch_protection(
        self, branch: str
    ) -> Union[Dict[str, Any], BranchProtectionUnreadable, None]:
        """None means "nothing is configured", which is worth reporting --
        it is not the same thing as "protection passed". A 401/403 means the
        token cannot read the setting at all, so the state is unknown."""
        status, body = self.api(
            "GET", f"repos/{self.repo}/branches/{branch}/protection"
        )
        if status in (401, 403):
            return BranchProtectionUnreadable(status)
        if status != 200 or not body.strip():
            return None
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return None

    # -- writing back -----------------------------------------------------
    def submit_review(self, number: int, event: str, body: str) -> bool:
        """Post a review. Returns False if the API refused (for example when
        reviewing your own pull request) so the caller can fall back."""
        status, _ = self.api(
            "POST", f"repos/{self.repo}/pulls/{number}/reviews",
            {"event": event, "body": body},
        )
        return status in (200, 201)

    def comment(self, number: int, body: str) -> bool:
        status, _ = self.api(
            "POST", f"repos/{self.repo}/issues/{number}/comments", {"body": body}
        )
        return status in (200, 201)

    def merge(self, number: int, method: str) -> Tuple[bool, str]:
        flag = {"merge": "--merge", "squash": "--squash",
                "rebase": "--rebase"}[method]
        args = ["pr", "merge", str(number), flag]
        if self.repo:
            args += ["--repo", self.repo]
        try:
            return True, self.gh(args, timeout=180).strip()
        except ReviewError as exc:
            return False, str(exc)


# ---------------------------------------------------------------------------
# Analysing the diff
# ---------------------------------------------------------------------------

def _iter_added_lines(diff: str) -> Iterable[Tuple[str, int, str]]:
    """Yield (path, line number, text) for every added line of a unified diff.

    The path comes from the `+++ b/<path>` line, because that is where a
    unified diff states which file the following hunks belong to. A deleted
    file has `+++ /dev/null` and contributes no added lines, which is right:
    there is nothing new to inspect in it.
    """
    path = ""
    new_line = 0
    for raw in diff.splitlines():
        if raw.startswith("diff --git"):
            path = ""
            new_line = 0
            continue
        if raw.startswith("--- "):
            continue
        if raw.startswith("+++ "):
            target = raw[4:].strip()
            if target.startswith("/dev/null"):
                path = ""
                continue
            if target.startswith("b/"):
                target = target[2:]
            path = target.strip('"')
            continue
        if raw.startswith("@@"):
            match = re.search(r"\+(\d+)", raw)
            new_line = int(match.group(1)) if match else 0
            continue
        if not path:
            continue
        if raw.startswith("+"):
            yield path, new_line, raw[1:]
            new_line += 1
        elif raw.startswith("-") or raw.startswith("\\"):
            continue
        else:
            new_line += 1


def check_secrets(diff: str) -> List[Finding]:
    findings: List[Finding] = []
    for path, line, text in _iter_added_lines(diff):
        for pattern, description in SECRET_PATTERNS:
            if re.search(pattern, text):
                findings.append(Finding(
                    "BLOCKING", "SECRET",
                    f"Added line looks like {description}.",
                    why="Secrets stay readable in history even after the file "
                        "is fixed, so they have to be rotated rather than "
                        "merely reverted.",
                    path=path, line=line,
                    fix="Remove the value, rotate the credential, and keep "
                        "the real one in .env (gitignored) or GitHub Secrets.",
                    evidence=text.strip()[:80],
                ))
                break
    return findings


def check_forbidden_paths(files: Sequence[Dict[str, Any]]) -> List[Finding]:
    findings: List[Finding] = []
    for entry in files:
        path = entry.get("path", "")
        for pattern, why in FORBIDDEN_PATHS:
            if re.search(pattern, path):
                findings.append(Finding(
                    "BLOCKING", "FORBIDDEN_PATH",
                    f"`{path}` should not be committed.",
                    why=why,
                    path=path,
                    fix="Remove it from the pull request, and add it to "
                        ".gitignore if it is not covered there already.",
                ))
                break
    return findings


def check_unsafe_code(diff: str) -> List[Finding]:
    findings: List[Finding] = []
    seen = set()
    for path, line, text in _iter_added_lines(diff):
        for pattern, label, why in UNSAFE_PATTERNS:
            if re.search(pattern, text) and (path, label) not in seen:
                seen.add((path, label))
                findings.append(Finding(
                    "IMPORTANT", "UNSAFE_CODE",
                    f"`{label}` added in `{path}`.",
                    why=why,
                    path=path, line=line,
                    fix="If this is genuinely required, say why in the "
                        "description; otherwise use the safer equivalent.",
                    evidence=text.strip()[:80],
                ))
    return findings


def check_scope(files: Sequence[Dict[str, Any]]) -> List[Finding]:
    if not files:
        return []
    docs_only = all(
        (entry.get("path", "") or "").lower().endswith(DOCS_SUFFIXES)
        for entry in files
    )
    limit_files = SCOPE_DOCS_FILES if docs_only else SCOPE_CODE_FILES
    limit_lines = SCOPE_DOCS_LINES if docs_only else SCOPE_CODE_LINES
    additions = sum(int(entry.get("additions") or 0) for entry in files)
    if len(files) <= limit_files and additions <= limit_lines:
        return []
    return [Finding(
        "IMPORTANT", "SCOPE",
        f"Touches {len(files)} files and adds {additions} lines, past the "
        f"{limit_files}-file / {limit_lines}-line guideline for this kind of "
        "change.",
        why="CONTRIBUTING asks for focused, small pull requests. A large "
            "change is hard to review well, and a defect hides inside it.",
        fix="Split it into stacked pull requests, or justify the size in the "
            "description so the reviewer knows it is deliberate.",
    )]


def check_tests_present(files: Sequence[Dict[str, Any]]) -> List[Finding]:
    """A code change with no test change is the most common real gap."""
    code_changed = [
        e for e in files
        if (e.get("path") or "").startswith(SOURCE_PREFIXES)
    ]
    tests_changed = [
        e for e in files if (e.get("path") or "").startswith(TEST_PREFIXES)
    ]
    if not code_changed or tests_changed:
        return []
    names = ", ".join(f"`{e.get('path')}`" for e in code_changed[:5])
    return [Finding(
        "IMPORTANT", "TESTS_MISSING",
        f"{len(code_changed)} source file(s) changed with no test change "
        f"({names}).",
        why="CONTRIBUTING asks for tests covering new behaviour. Without "
            "them the next change can break this one silently.",
        fix="Add a test under backend/tests/ that fails before your change "
            "and passes after it, and name it in the description.",
    )]


def check_test_deletions(files: Sequence[Dict[str, Any]]) -> List[Finding]:
    removed = [
        e for e in files
        if (e.get("path") or "").startswith(TEST_PREFIXES)
        and (e.get("status") or "") in ("removed", "renamed")
    ]
    if not removed:
        return []
    names = ", ".join(f"`{e.get('path')}`" for e in removed[:5])
    return [Finding(
        "IMPORTANT", "TESTS_DELETED",
        f"{len(removed)} test file(s) removed or renamed: {names}.",
        why="Losing coverage is easy to miss in review and hard to notice "
            "afterwards, because the suite stays green with less in it.",
        fix="Confirm the coverage still exists elsewhere; if a test is "
            "obsolete, say so in the description.",
    )]


def check_sensitive_paths(files: Sequence[Dict[str, Any]]) -> List[Finding]:
    hits = [
        e for e in files
        if (e.get("path") or "").startswith(SENSITIVE_PREFIXES)
    ]
    if not hits:
        return []
    names = ", ".join(f"`{e.get('path')}`" for e in hits[:6])
    return [Finding(
        "IMPORTANT", "SENSITIVE_PATH",
        f"Touches project configuration or security-relevant files: {names}.",
        why="These change how the deployed site behaves, what it may record, "
            "or how it is reviewed. A defect here reaches production rather "
            "than only the diff.",
        fix="Say in the description why each of these must change, and "
            "confirm the related issue agrees.",
    )]


def check_body(pr: Dict[str, Any]) -> List[Finding]:
    """Guidelines from CONTRIBUTING: describe the change, show the tests,
    link the issue."""
    body = pr.get("body") or ""
    findings: List[Finding] = []

    prose = re.sub(r"<!--.*?-->", "", body, flags=re.S).strip()
    if len(prose) < 60:
        findings.append(Finding(
            "IMPORTANT", "NO_DESCRIPTION",
            "The pull request body has almost no description.",
            why="CONTRIBUTING asks what changed and why. Without it the "
                "reviewer is guessing at intent, which is where most "
                "misunderstandings start.",
            fix="Add a short summary of the change and the reason for it.",
        ))

    if not re.search(r"(?i)\b(pytest|tests?/|passed|failed|test)\b", body):
        findings.append(Finding(
            "IMPORTANT", "NO_TEST_EVIDENCE",
            "The description does not say which tests were run.",
            why="CONTRIBUTING asks for the exact tests run; without it there "
                "is no evidence the change was exercised at all.",
            fix="List the commands you ran and their result, for example "
                "`python -m pytest tests/ -q`.",
        ))

    # "2 failures", "2 existing failures", "1 failed" -- with room for the
    # couple of words people put in between. "0 failures" is good news and is
    # deliberately not reported.
    reported = [
        int(m.group(1)) for m in re.finditer(
            r"(?i)\b(\d+)\b(?:\s+\S+){0,2}\s+(failed|failures?)\b", body
        )
        if int(m.group(1)) > 0
    ]
    if reported:
        # Somebody who writes "2 existing failures" has already told the
        # reviewer these are not theirs. That is worth noting, not demanding
        # a fix for -- the automated run below confirms it either way.
        explained = re.search(
            r"(?i)(existing|pre-?existing|unrelated|already (?:failing|known)"
            r"|not (?:related|introduced))", body
        )
        findings.append(Finding(
            "MINOR" if explained else "IMPORTANT", "BODY_REPORTS_FAILURES",
            f"The description reports failing tests ({reported[0]} of them)"
            + (", described as pre-existing." if explained else "."),
            why="CONTRIBUTING requires tests to pass with zero failures, so a "
                "reported failure always deserves a second look.",
            fix="Fix them, or explain precisely why they are unrelated to "
                "this change.",
        ))

    if not re.search(r"#\d+|issues/\d+", body):
        findings.append(Finding(
            "MINOR", "NO_ISSUE_LINK",
            "No issue is linked from the description.",
            why="CONTRIBUTING asks for related issues to be linked, so the "
                "history stays traceable.",
            fix="Reference it as `Fixes #123` if an issue exists.",
        ))
    return findings


def check_title(title: str) -> List[Finding]:
    if re.match(r"^(feat|fix|docs|refactor|test|chore|ci|perf|style|build)"
                r"(\([^)]*\))?:\s\S", title or ""):
        return []
    return [Finding(
        "MINOR", "TITLE_FORMAT",
        f"Title `{title}` does not follow the `type: summary` form.",
        why="Every commit in this repository's history uses that form, so a "
            "different shape stands out in `git log`.",
        fix="Rename it, for example `docs: explain how to run focused tests`.",
    )]


def check_unrelated(files: Sequence[Dict[str, Any]], pr: Dict[str, Any]) -> List[Finding]:
    """A heuristic, and said to be one.

    A file looks unexplained when none of the meaningful words in its path
    appear in the title or description. That is a prompt to ask, never proof
    of a mistake.
    """
    corpus = ((pr.get("title") or "") + " " + (pr.get("body") or "")).lower()
    corpus_tokens = {
        t for t in re.findall(r"[a-z]{4,}", corpus)
        if t not in NON_TOPIC_TOKENS
    }

    strays = []
    for entry in files:
        path = (entry.get("path") or "").lower()
        parts = re.split(r"[/_\-.]", path)
        tokens = {p for p in parts if len(p) >= 4} - NON_TOPIC_TOKENS
        if tokens and not (tokens & corpus_tokens):
            strays.append(entry.get("path") or path)

    if not strays:
        return []
    names = ", ".join(f"`{p}`" for p in strays[:5])
    return [Finding(
        "MINOR", "UNRELATED",
        f"{len(strays)} file(s) share no words with the title or "
        f"description: {names}.",
        why="This may be entirely correct -- wording is a weak signal -- but "
            "an unexplained file is exactly where an accidental change hides.",
        fix="If they belong here, say so in one line in the description.",
        evidence="heuristic: inferred, not observed",
    )]


def check_whitespace(diff: str) -> List[Finding]:
    findings: List[Finding] = []
    added = list(_iter_added_lines(diff))

    for path, line, text in added:
        if text != text.rstrip():
            findings.append(Finding(
                "MINOR", "TRAILING_WHITESPACE",
                "Added line has trailing whitespace.",
                why="Git flags it with --check, and it creates noise in later "
                    "diffs.",
                path=path, line=line,
                fix="Remove the trailing spaces.",
                evidence=repr(text[-10:]),
            ))
            break

    # Only the open and close markers count on their own: a line of seven
    # equals signs is also how a setext heading is underlined, so it is
    # evidence of a conflict only when a real marker is there with it.
    markers = [
        (path, line, text) for path, line, text in added
        if text.startswith("<<<<<<<") or text.startswith(">>>>>>>")
    ]
    if markers:
        path, line, _ = markers[0]
        findings.append(Finding(
            "BLOCKING", "CONFLICT_MARKERS",
            "Added lines contain merge conflict markers "
            f"(`{markers[0][2].strip()[:30]}`).",
            why="Conflict markers committed into source produce syntax errors "
                "or silently wrong behaviour.",
            path=path, line=line,
            fix="Resolve the conflict properly and push the resolved file.",
        ))
    return findings


def check_large_files(files: Sequence[Dict[str, Any]]) -> List[Finding]:
    big = [e for e in files if int(e.get("additions") or 0) > 800]
    if not big:
        return []
    names = ", ".join(
        f"`{e.get('path')}` (+{e.get('additions')})" for e in big[:4]
    )
    return [Finding(
        "MINOR", "LARGE_FILE",
        f"Large single-file change: {names}.",
        why="Big files are where reviewers skim, and skimming is how defects "
            "ship.",
        fix="Consider splitting it, or point the reviewer at the parts that "
            "matter most.",
    )]


def analyse_diff(pr: Dict[str, Any], diff: str,
                 files: Sequence[Dict[str, Any]]) -> List[Finding]:
    findings: List[Finding] = []
    findings += check_secrets(diff)
    findings += check_forbidden_paths(files)
    findings += check_unsafe_code(diff)
    findings += check_scope(files)
    findings += check_tests_present(files)
    findings += check_test_deletions(files)
    findings += check_sensitive_paths(files)
    findings += check_body(pr)
    findings += check_title(pr.get("title") or "")
    findings += check_unrelated(files, pr)
    findings += check_whitespace(diff)
    findings += check_large_files(files)
    return findings


# ---------------------------------------------------------------------------
# Pull-request state
# ---------------------------------------------------------------------------

def check_pr_state(pr: Dict[str, Any], default_branch: str) -> List[Finding]:
    """States that make a pull request unsafe or impossible to judge."""
    findings: List[Finding] = []
    state = (pr.get("state") or "").upper()

    if state != "OPEN":
        findings.append(Finding(
            "BLOCKING", "UNREACHABLE",
            f"Pull request is {state or 'unknown'}, not open.",
            why="Only open pull requests can be reviewed or merged.",
        ))
    if pr.get("isDraft"):
        findings.append(Finding(
            "BLOCKING", "DRAFT",
            "This is a draft pull request.",
            why="Drafts are work in progress; the author has not asked for a "
                "review yet.",
            fix="Mark it ready for review when the change is complete.",
        ))
    if (pr.get("baseRefName") or "") != default_branch:
        findings.append(Finding(
            "BLOCKING", "WRONG_BASE",
            f"Base branch is `{pr.get('baseRefName')}`, but the repository's "
            f"default is `{default_branch}`.",
            why="Reviewing against another base mixes a different line of "
                "work into the diff and makes the merge unsafe.",
            fix=f"Retarget the pull request at `{default_branch}`.",
        ))

    mergeable = (pr.get("mergeable") or "").upper()
    merge_state = (pr.get("mergeStateStatus") or "").upper()
    if mergeable == "CONFLICTING" or merge_state == "DIRTY":
        findings.append(Finding(
            "BLOCKING", "CONFLICT",
            f"The branch conflicts with `{default_branch}` "
            f"(mergeable={mergeable or 'unknown'}).",
            why="A conflicting pull request cannot be merged as it stands, "
                "and resolving it through GitHub's editor would bypass review "
                "of the result.",
            fix=f"Run `git fetch origin && git merge origin/{default_branch}` "
                "locally, resolve, and push.",
        ))
    elif merge_state == "BEHIND":
        findings.append(Finding(
            "IMPORTANT", "BEHIND",
            f"The branch is behind `{default_branch}`.",
            why="Tests would run against an older tree than the one that "
                "would actually be merged.",
            fix="Update the branch (GitHub's Update branch button, or merge "
                "the default branch in locally) and push.",
        ))
    return findings


def normalize_checks(rollup: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Reduce GitHub's two check shapes (check runs and status contexts) to
    one vocabulary: PASS, FAIL, PENDING, OTHER."""
    checks: List[Dict[str, Any]] = []
    for entry in rollup or []:
        name = entry.get("name") or entry.get("context") or "(unnamed check)"
        conclusion = (entry.get("conclusion") or "").upper()
        state = (entry.get("state") or "").upper()

        if conclusion:
            if conclusion in ("SUCCESS", "NEUTRAL", "SKIPPED"):
                status = "PASS"
            elif conclusion in ("FAILURE", "ERROR", "TIMED_OUT",
                                "ACTION_REQUIRED", "STARTUP_FAILURE",
                                "CANCELLED"):
                status = "FAIL"
            else:
                # A conclusion only exists once the check has finished, so an
                # unrecognised one means "done, and we cannot read how".
                status = "OTHER"
        elif state == "SUCCESS":
            status = "PASS"
        elif state in ("FAILURE", "ERROR", "CANCELLED"):
            status = "FAIL"
        elif state in ("PENDING", "QUEUED", "IN_PROGRESS", "REQUESTED",
                       "WAITING"):
            status = "PENDING"
        else:
            status = "OTHER"

        checks.append({
            "name": name,
            "status": status,
            "detail": (entry.get("description") or "").strip(),
            "url": entry.get("targetUrl") or entry.get("detailsUrl") or "",
        })
    return checks


def check_results(checks: Sequence[Dict[str, Any]]) -> List[Finding]:
    findings: List[Finding] = []
    failed = [c for c in checks if c["status"] == "FAIL"]
    pending = [c for c in checks if c["status"] == "PENDING"]

    for check in failed[:5]:
        findings.append(Finding(
            "BLOCKING", "CHECKS_FAILED",
            f"Check `{check['name']}` failed.",
            why="A failing check means the change does not work on the branch "
                "being merged.",
            fix=f"Open {check['url'] or 'the Checks tab'}, fix the failure, "
                "and push again.",
            evidence=check["detail"][:200],
        ))
    if pending and not failed:
        names = ", ".join(f"`{c['name']}`" for c in pending[:5])
        findings.append(Finding(
            "BLOCKING", "CHECKS_RUNNING",
            f"Checks still running: {names}.",
            why="Merging before checks finish means merging code nobody has "
                "seen pass.",
            fix="Wait for the checks to finish, then re-run this review.",
        ))
    for check in [c for c in checks if c["status"] == "OTHER"][:5]:
        findings.append(Finding(
            "BLOCKING", "CHECKS_UNKNOWN",
            f"Check `{check['name']}` is in a state this tool cannot read, so "
            "its result cannot be verified.",
            why="A check that cannot be understood is a check that might have "
                "failed. It is treated as a failure rather than a pass.",
            fix=f"Open {check['url'] or 'the Checks tab'} and confirm it "
                "passed, then re-run this review.",
            evidence=check["detail"][:200],
        ))
    return findings


def approval_state(reviews: Sequence[Dict[str, Any]], head_oid: Optional[str] = None,
                   dismiss_stale: bool = False) -> Tuple[List[str], List[str]]:
    """Latest decision per reviewer, so a later approval supersedes an earlier
    request for changes.

    When the repository dismisses stale approvals, an approval recorded against
    an older commit does not count -- GitHub would refuse it on merge, and so do
    we. A request for changes is not cleared by pushing new commits, so it is
    kept regardless of commit.
    """
    latest: Dict[str, str] = {}
    for review in reviews or []:
        # Two transports, two field names: the REST endpoint that
        # `GitHub.reviews()` calls reports the reviewer as `user`, while
        # `gh pr view --json` reports it as `author`. Reading only one of
        # them silently drops every review from the other, which turns the
        # approval gate into a permanent refusal, so accept both.
        login = ((review.get("author") or review.get("user")
                  or {}).get("login"))
        state = (review.get("state") or "").upper()
        if not login or state in ("", "PENDING"):
            continue
        if (dismiss_stale and state == "APPROVED" and head_oid
                and review.get("commit_id") not in (None, "", head_oid)):
            continue
        latest[login] = state
    approvals = [u for u, s in latest.items() if s == "APPROVED"]
    changes = [u for u, s in latest.items() if s == "CHANGES_REQUESTED"]
    return approvals, changes


def protection_requirements(
    protection: Union[Dict[str, Any], BranchProtectionUnreadable, None]
) -> Dict[str, Any]:
    """What the repository actually requires. No protection means nothing is
    required -- a fact about the repository, not a pass. An unreadable
    protection setting is unknown rather than absent."""
    if isinstance(protection, BranchProtectionUnreadable):
        return {"configured": False, "required_approvals": 0,
                "required_checks": [], "strict": False, "dismiss_stale": False,
                "unreadable": protection.status}
    if not protection:
        return {"configured": False, "required_approvals": 0,
                "required_checks": [], "strict": False, "dismiss_stale": False}
    reviews = protection.get("required_pull_request_reviews") or {}
    checks = protection.get("required_status_checks") or {}
    return {
        "configured": True,
        "required_approvals":
            int(reviews.get("required_approving_review_count") or 0),
        "required_checks": list(checks.get("contexts") or []),
        "strict": bool(checks.get("strict")),
        "dismiss_stale": bool(reviews.get("dismiss_stale_approvals")),
        "enforce_admins":
            bool((protection.get("enforce_admins") or {}).get("enabled")),
    }


# ---------------------------------------------------------------------------
# Running the test suite, safely
# ---------------------------------------------------------------------------

def _git(args: Sequence[str], cwd: str, timeout: int = 300):
    proc = subprocess.run(
        ["git"] + list(args), cwd=cwd, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
    )
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def _sanitized_env() -> Dict[str, str]:
    """Just enough environment to run Python, and nothing that carries a
    credential, so contributor code cannot read a token even if it wanted to.
    """
    keep = [
        "PATH", "PATHEXT", "HOME", "USERPROFILE", "HOMEPATH", "APPDATA",
        "LOCALAPPDATA", "SYSTEMROOT", "SYSTEMDRIVE", "COMSPEC", "WINDIR",
        "TEMP", "TMP", "NUMBER_OF_PROCESSORS", "LANG", "LC_ALL",
    ]
    env = {k: os.environ[k] for k in keep if os.environ.get(k)}
    env["PYTHONIOENCODING"] = "utf-8"
    for name in ("GITHUB_TOKEN", "GH_TOKEN", "GIT_ASKPASS", "AWS_ACCESS_KEY_ID",
                 "AWS_SECRET_ACCESS_KEY"):
        env.pop(name, None)
    return env


def _remove_tree(path: str) -> bool:
    """Windows hands back locked files for a moment after a process exits."""
    for attempt in range(5):
        try:
            shutil.rmtree(path, ignore_errors=True)
        except OSError:
            pass
        if not os.path.exists(path):
            return True
        time.sleep(0.4 * (attempt + 1))
    return not os.path.exists(path)


def _normalize_reason(reason: str, tmp: Optional[str] = None) -> str:
    """Strip the values that differ between two runs of the same failure.

    Paths, mock object ids, and generated ids change every run, so leaving
    them in would make an identical failure look new. Only infrastructure
    noise is removed: a KeyError versus an AssertionError still shows up as a
    difference, which is the whole point of comparing reasons at all.
    """
    if not reason:
        return ""
    if tmp:
        reason = reason.replace(tmp, "<tmp>")
    reason = re.sub(r"[A-Za-z]:[\\/][^\s'\"),;]+", "<path>", reason)  # C:\...
    reason = re.sub(r"/(?:home|tmp|Users|var|private)/[^\s'\"),;]+",
                    "<path>", reason)
    reason = re.sub(r"\b[0-9a-f]{32}\b", "<uuid>", reason)            # uuid4 hex
    reason = re.sub(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        "<uuid>", reason)
    reason = re.sub(r"\b(\w+)\s*=\s*0x[0-9a-f]+\b", r"\1=<id>", reason)
    reason = re.sub(r"\b(\w+)\s*=\s*\d{6,}\b", r"\1=<id>", reason)   # mock ids
    return " ".join(reason.split())


def _parse_pytest(output: str, tmp: Optional[str] = None) -> Dict[str, Any]:
    """Read pytest's short summary.

    Both the failing node id and the *reason* it failed are kept. Comparing
    only node ids would call a failure harmless just because the same test
    broke in two different ways, which is exactly the mistake this is here to
    prevent.
    """
    failures: List[str] = []
    details: Dict[str, str] = {}
    for line in output.splitlines():
        stripped = line.strip()
        if not (stripped.startswith("FAILED") or stripped.startswith("ERROR")):
            continue
        parts = stripped.split()
        if len(parts) < 2:
            continue
        node = parts[1]
        reason = stripped.split(" - ", 1)[1].strip() if " - " in stripped else ""
        failures.append(node)
        details[node] = _normalize_reason(reason, tmp)
    passed = failed = errors = 0
    match = re.search(r"(\d+) passed", output)
    if match:
        passed = int(match.group(1))
    match = re.search(r"(\d+) failed", output)
    if match:
        failed = int(match.group(1))
    match = re.search(r"(\d+) error", output)
    if match:
        errors = int(match.group(1))
    return {
        "passed": passed, "failed": failed, "errors": errors,
        "failures": sorted(set(failures)),
        "failure_details": details,
        "tail": [l for l in output.splitlines() if l.strip()][-6:],
    }


def _resolve_commit(clone: str, commit: str, fetch_url: Optional[str],
                    refs: Sequence[str]) -> bool:
    """Make sure `commit` exists in the throwaway clone.

    A local clone does not contain a fork's commits, so when the commit is
    missing we ask GitHub for it anonymously -- public repositories publish
    `refs/pull/<n>/head` to anyone. The fetch happens inside the temp clone,
    never in the maintainer's working repository.
    """
    if not commit:
        return False
    code, _, _ = _git(["cat-file", "-e", f"{commit}^{{commit}}"], cwd=clone)
    if code == 0:
        return True
    if not fetch_url:
        return False
    _git(["remote", "set-url", "origin", fetch_url], cwd=clone)
    for ref in refs:
        _git(["-c", "credential.helper=", "fetch", "--quiet", "origin", ref],
             cwd=clone, timeout=600)
        code, _, _ = _git(["cat-file", "-e", f"{commit}^{{commit}}"], cwd=clone)
        if code == 0:
            return True
    return False


def run_suite(source_dir: str, commit: str, fetch_url: Optional[str] = None,
              refs: Sequence[str] = (), timeout: int = 900) -> Dict[str, Any]:
    """Check out `commit` in a throwaway clone and run the suite there.

    The clone has no `.env`, no database files and no local git config, and
    the child process receives `_sanitized_env()`, so contributor code runs
    with none of the maintainer's secrets available to it.
    """
    tmp = tempfile.mkdtemp(prefix="critique-pr-")
    result: Dict[str, Any] = {
        "ran": False, "commit": commit, "reason": "",
        "passed": 0, "failed": 0, "errors": 0, "failures": [],
        "failure_details": {}, "elapsed": 0.0, "tail": [],
    }
    started = time.time()
    try:
        code, _, err = _git(
            ["clone", "--quiet", "--no-hardlinks", source_dir, tmp],
            cwd=tempfile.gettempdir(), timeout=600,
        )
        if code != 0:
            result["reason"] = f"clone failed: {err.strip()[:200]}"
            return result

        if not _resolve_commit(tmp, commit, fetch_url, refs):
            result["reason"] = (
                f"commit {commit[:9]} is not available locally and could not "
                "be fetched"
            )
            return result

        code, _, err = _git(["checkout", "--quiet", "--detach", commit], cwd=tmp)
        if code != 0:
            result["reason"] = f"checkout failed: {err.strip()[:200]}"
            return result

        backend = os.path.join(tmp, "backend")
        if not os.path.isdir(backend):
            result["reason"] = "no backend/ directory at that commit"
            return result

        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-q", "--no-header",
             "-p", "no:cacheprovider"],
            cwd=backend, env=_sanitized_env(), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        )
        result.update(_parse_pytest((proc.stdout or "") + "\n" + (proc.stderr or ""),
                                    tmp))
        result["ran"] = True
        return result
    except subprocess.TimeoutExpired:
        result["reason"] = f"test run exceeded {timeout}s"
        return result
    except OSError as exc:
        result["reason"] = f"could not run tests: {exc}"
        return result
    finally:
        result["elapsed"] = round(time.time() - started, 1)
        if not _remove_tree(tmp):
            result["notes"] = [f"temporary clone at {tmp} could not be removed"]


def compare_runs(head: Dict[str, Any],
                 base: Optional[Dict[str, Any]]) -> List[Finding]:
    """Blame this branch only for the failures it actually introduced.

    Both the node id and the normalised reason are compared. Matching node ids
    alone would wave through a test that broke here for a completely new
    reason just because it was already broken on the base, so a changed reason
    counts as introduced. When the base could not be run at all, nothing can be
    shown to be pre-existing, and that is reported as blocking rather than
    assumed benign.
    """
    findings: List[Finding] = []
    if not head.get("ran"):
        return [Finding(
            "IMPORTANT", "TESTS_NOT_RUN",
            f"The test suite could not be run here: {head.get('reason')}.",
            why="Nothing at all is claimed about the tests then; a review "
                "that says 'looks fine' without running anything is guessing.",
            fix="Run `cd backend && python -m pytest tests/ -q` locally and "
                "paste the result into the description.",
        )]

    base_ran = bool((base or {}).get("ran"))
    base_details = dict((base or {}).get("failure_details") or {})
    # A node the base failed is known even when no reason was recorded for it;
    # a reason recorded on either side takes part in the comparison.
    base_nodes = set(base_details) | set((base or {}).get("failures") or [])
    head_details = dict(head.get("failure_details") or {})
    for node in head.get("failures") or []:
        head_details.setdefault(node, "")

    introduced = [node for node in sorted(head_details)
                  if node not in base_nodes]
    changed = [(node, base_details.get(node, ""), head_details[node])
               for node in sorted(head_details)
               if node in base_nodes
               and base_details.get(node, "") != head_details[node]]

    if introduced or changed:
        if not base_ran:
            names = ", ".join(f"`{n}`" for n in (introduced + [c[0] for c in changed])[:5])
            findings.append(Finding(
                "BLOCKING", "TEST_FAILURES",
                f"{len(introduced) + len(changed)} failing test(s) on this "
                f"branch that could not be checked against the merge base: "
                f"{names}.",
                why="Without a base run there is no way to show these are not "
                    "the branch's own doing, so they are treated as blocking "
                    "rather than assumed harmless.",
                fix="Fix the failing tests, or run the suite on the base "
                    "branch yourself and explain why these are unrelated.",
            ))
        else:
            for node, before, after in changed[:5]:
                findings.append(Finding(
                    "BLOCKING", "TEST_FAILURES",
                    f"`{node}` fails differently here than on the merge base.",
                    why="The same test failing for a new reason is a new "
                        "failure, even though the node id matches.",
                    path=node.split("::")[0],
                    fix=f"On the base it failed with `{before or 'no detail'}`; "
                        f"here it fails with `{after or 'no detail'}`. Fix the "
                        "new cause.",
                ))
            if introduced:
                names = ", ".join(f"`{n}`" for n in introduced[:5])
                findings.append(Finding(
                    "BLOCKING", "TEST_FAILURES",
                    f"{len(introduced)} test failure(s) introduced by this "
                    f"branch: {names}.",
                    why="The same suite passes on the merge base, so these "
                        "failures belong to this pull request.",
                    fix="Fix the failing tests, or explain precisely why they "
                        "are not yours.",
                ))
    elif (head.get("failed") or head.get("errors")) and not base_ran:
        # Failures exist but the base run does not, so none of them can be
        # shown to be pre-existing. Blocking is the honest reading.
        names = ", ".join(f"`{n}`" for n in sorted(head_details)[:5])
        findings.append(Finding(
            "BLOCKING", "TEST_FAILURES",
            f"{len(head_details)} failing test(s) on this branch that could "
            f"not be checked against the merge base: {names or 'see output'}.",
            why="The base run did not happen, so nothing here has been "
                "demonstrated to be pre-existing.",
            fix="Fix the failing tests, or run the suite on the base branch "
                "yourself and explain why these are unrelated.",
        ))
    elif head.get("failed") or head.get("errors"):
        # The base fails identically -- same test, same reason. Not the
        # contributor's problem, so it must not become a request for changes;
        # reported anyway, because a maintainer should decide whether to fix
        # it rather than have it fade into the background.
        names = ", ".join(f"`{f}`" for f in sorted(head_details)[:5])
        findings.append(Finding(
            "MINOR", "PREEXISTING_FAILURES",
            f"{head.get('failed', 0)} failing test(s) also fail on the merge "
            f"base for the same reason, so they are not introduced here "
            f"({names or 'see output'}).",
            why="Confirmed by comparing the failure reasons at both commits, "
                "not just the test names.",
            fix="Nothing for the contributor; the maintainer decides whether "
                "to fix these separately.",
        ))
    return findings


# ---------------------------------------------------------------------------
# Assembling the review
# ---------------------------------------------------------------------------

def github_url(repo_info: Dict[str, Any]) -> str:
    return repo_info.get("url") or ""


def build_review(gh: GitHub, number: int, repo_info: Dict[str, Any],
                 run_tests: bool = True, test_timeout: int = 900,
                 work_dir: Optional[str] = None) -> ReviewResult:
    """Fetch everything, analyse it, return a result. Reads nothing but the
    API and the local repository."""
    pr = gh.pr(number)
    result = ReviewResult(pr=pr, repo=repo_info)
    default_branch = repo_info.get("default_branch", "main")

    result.findings += check_pr_state(pr, default_branch)

    try:
        diff = gh.pr_diff(number)
    except ReviewError as exc:
        result.findings.append(Finding(
            "BLOCKING", "UNREACHABLE",
            f"The diff could not be fetched: {exc}",
            why="Without a diff there is nothing to review.",
        ))
        diff = ""
    files = list(pr.get("files") or [])
    if diff:
        result.findings += analyse_diff(pr, diff, files)

    result.checks = normalize_checks(pr.get("statusCheckRollup") or [])
    result.findings += check_results(result.checks)

    reviews = gh.reviews(number)
    protection = gh.branch_protection(default_branch)
    result.protection = protection
    required = protection_requirements(protection)
    approvals, changes_requested = approval_state(
        reviews, pr.get("headRefOid") or "",
        bool(required.get("dismiss_stale")))

    if changes_requested:
        result.findings.append(Finding(
            "BLOCKING", "CHANGES_REQUESTED_EXISTING",
            f"{len(changes_requested)} reviewer(s) still have changes "
            f"requested open: {', '.join(sorted(changes_requested))}.",
            why="An unresolved request for changes means somebody already "
                "found a problem that has not been answered.",
            fix="Address the outstanding review, then re-run this one.",
        ))

    if run_tests:
        source = work_dir or os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))
        url = github_url(repo_info)
        head = pr.get("headRefOid") or ""
        result.test_head = run_suite(
            source, head, fetch_url=url,
            refs=[f"refs/pull/{number}/head", head],
            timeout=test_timeout,
        )
        base = _merge_base(source, pr)
        if base:
            result.test_base = run_suite(
                source, base, fetch_url=url, refs=[base], timeout=test_timeout
            )
        result.findings += compare_runs(result.test_head, result.test_base)
    else:
        result.notes.append(
            "Test suite not run (--skip-tests); nothing is claimed about it.")

    result.gates = build_gates(result, pr, repo_info, required, approvals)
    result.notes.append(_method_note(pr, repo_info))
    return result


def _merge_base(source_dir: str, pr: Dict[str, Any]) -> Optional[str]:
    """The fair thing to compare against: where this branch diverged."""
    head, base = pr.get("headRefOid"), pr.get("baseRefOid")
    if not head or not base:
        return base
    code, out, _ = _git(["merge-base", head, base], cwd=source_dir, timeout=60)
    if code == 0 and out.strip():
        return out.strip()
    return base


def build_gates(result: ReviewResult, pr: Dict[str, Any],
                repo_info: Dict[str, Any], required: Dict[str, Any],
                approvals: Sequence[str]) -> List[Gate]:
    """The conditions `--merge` demands. None of them bend for the flag."""
    gates: List[Gate] = []
    status = result.status

    gates.append(Gate(
        "Review status is READY",
        status == "READY",
        f"status is {status}"
        + (f" ({len(result.blocking)} blocking, {len(result.important)} "
           f"important)" if status != "READY" else "; nothing for the "
           "contributor to fix"),
    ))

    mergeable = (pr.get("mergeable") or "").upper()
    merge_state = (pr.get("mergeStateStatus") or "").upper()
    # BLOCKED means required checks or approvals are unmet, UNKNOWN means
    # GitHub has not finished deciding, and an empty value means we were never
    # told. None of those are an invitation to merge, so all three fail here.
    merge_ok = (mergeable == "MERGEABLE"
                and merge_state not in ("DIRTY", "BLOCKED", "UNKNOWN", ""))
    gates.append(Gate(
        "Pull request is mergeable",
        merge_ok,
        f"mergeable={mergeable or 'unknown'} "
        f"mergeState={merge_state or 'unknown'}",
    ))

    failing = [c for c in result.checks if c["status"] == "FAIL"]
    pending = [c for c in result.checks if c["status"] == "PENDING"]
    unknown = [c for c in result.checks if c["status"] == "OTHER"]
    if result.checks:
        # Every check has to say PASS. A state this tool does not understand
        # is not counted as a pass.
        all_passed = not (failing or pending or unknown)
        gates.append(Gate(
            "All checks passed",
            all_passed,
            "all passed" if all_passed
            else f"{len(failing)} failed, {len(pending)} still running, "
                 f"{len(unknown)} in an unreadable state",
        ))
    else:
        gates.append(Gate(
            "Continuous integration",
            False,
            "no CI checks are configured, so nothing has verified this branch",
            manual_fix="Add a workflow under .github/workflows that runs "
                       "`python -m pytest tests/ -q`, then require that "
                       "check on the default branch.",
        ))

    required_count = required.get("required_approvals", 0)
    decision = (pr.get("reviewDecision") or "").upper()
    approvals_ok = len(approvals) >= required_count
    detail = (f"{len(approvals)} present"
              + ("" if required_count else
                 (" -- requirements unknown"
                  if required.get("unreadable")
                  else " -- the repository requires none")))
    # GitHub computes reviewDecision itself; when it says a review is still
    # required or that changes were requested, its word fails this gate even
    # if our own count disagrees.
    if decision in ("CHANGES_REQUESTED", "REVIEW_REQUIRED"):
        approvals_ok = False
        detail += f"; GitHub reports reviewDecision={decision}"
    gates.append(Gate(
        f"Approvals ({required_count} required)",
        approvals_ok,
        detail,
    ))

    unreadable = required.get("unreadable")
    if unreadable:
        gates.append(Gate(
            "Branch protection on the default branch",
            False,
            "could not verify: the token cannot read branch protection "
            f"(HTTP {unreadable}); it needs admin or maintainer rights",
            manual_fix="Re-run with a token that can read repository "
                       "administration (admin or maintainer). Do not change "
                       "the repository's rules based on this result.",
        ))
    elif not required.get("configured"):
        gates.append(Gate(
            "Branch protection on the default branch",
            False,
            "branch protection is not enabled, so no review or check is "
            "actually required before merging",
            manual_fix="Settings -> Rules -> Add rule for the default branch: "
                       "require a pull request before merging and require 1 "
                       "approval; add the required status check once CI "
                       "exists.",
        ))
    else:
        missing = [
            c for c in required.get("required_checks", [])
            if not any(c in (check["name"] or "") for check in result.checks)
        ]
        gates.append(Gate(
            "Branch protection on the default branch",
            not missing,
            "configured"
            + (f" -- required check(s) not reported: {', '.join(missing)}"
               if missing else ""),
        ))
    return gates


def _method_allowed(repo_info: Dict[str, Any], method: str) -> bool:
    """Whether the repository still allows this merge method.

    Note the asymmetry: squash and rebase are `allow_<method>_merge`, but merge
    commits are `allow_merge_commit`. Building the key with an f-string was how
    this once ended up asking for `allow_merge_merge` and getting it wrong.
    """
    key = {"merge": "allow_merge_commit",
           "squash": "allow_squash_merge",
           "rebase": "allow_rebase_merge"}[method]
    return bool(repo_info.get(key, True))


def _method_note(pr: Dict[str, Any], repo_info: Dict[str, Any]) -> str:
    allowed = [m for m in ("merge", "squash", "rebase")
               if _method_allowed(repo_info, m)]
    viewer = repo_info.get("viewer_default_merge_method", "")
    return (f"Merge methods allowed: {', '.join(allowed) or 'none'}; the "
            f"repository default is {viewer.upper() or 'unset'}; this pull "
            f"request has {len(pr.get('commits') or [])} commit(s).")


def choose_method(repo_info: Dict[str, Any], requested: Optional[str]) -> Optional[str]:
    """Pick a merge method the repository actually allows.

    The repository's own configured default wins, because that is what the
    maintainer already uses; an explicit flag wins over that. Merge commits
    are the last resort only if nothing else is enabled.
    """
    viewer = (repo_info.get("viewer_default_merge_method") or "").lower()
    if requested:
        order = [requested]
    elif viewer in ("merge", "squash", "rebase"):
        order = [viewer]
    else:
        order = ["merge", "squash", "rebase"]
    for method in order:
        if _method_allowed(repo_info, method):
            return method
    for method in ("squash", "rebase", "merge"):
        if _method_allowed(repo_info, method):
            return method
    return None


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def render_report(result: ReviewResult, user: str = "") -> str:
    pr, repo = result.pr, result.repo
    author = (pr.get("author") or {}).get("login") or "(unknown)"
    bar = "=" * 78
    lines: List[str] = []

    lines.append(bar)
    lines.append(f'Review of #{pr.get("number")} "{pr.get("title")}"')
    lines.append(f"Repository : {repo.get('name')} "
                 f"(default branch {repo.get('default_branch')})")
    lines.append(f"Author     : {author}"
                 + ("  [you]" if user and author == user else ""))
    lines.append(f"Branch     : {pr.get('headRefName')} -> "
                 f"{pr.get('baseRefName')}")
    lines.append(f"State      : {pr.get('state')}"
                 + (" (draft)" if pr.get("isDraft") else "")
                 + f"  mergeable={pr.get('mergeable') or 'unknown'}"
                 + f" ({pr.get('mergeStateStatus') or 'unknown'})")
    lines.append(f"Size       : {len(pr.get('files') or [])} files, "
                 f"+{pr.get('additions')} -{pr.get('deletions')}, "
                 f"{len(pr.get('commits') or [])} commit(s)")
    lines.append(f"URL        : {pr.get('url')}")
    lines.append("")
    lines.append(f"STATUS: {result.status}")

    for title, items in (("BLOCKING", result.blocking),
                         ("IMPORTANT", result.important),
                         ("MINOR", result.minor)):
        lines.append("")
        lines.append(f"{title} ({len(items)})")
        if not items:
            lines.append("  (none)")
        for finding in items:
            where = finding.location()
            lines.append(f"  [{finding.code}] {finding.message}")
            if where:
                lines.append(f"        at {where}")
            if finding.why:
                lines.append(f"        why: {finding.why}")
            if finding.fix:
                lines.append(f"        fix: {finding.fix}")
            if finding.evidence:
                lines.append(f"        evidence: {finding.evidence}")

    lines.append("")
    lines.append("Continuous integration")
    if result.checks:
        for check in result.checks:
            detail = f" -- {check['detail']}" if check["detail"] else ""
            lines.append(f"  {check['status']:8} {check['name']}{detail}")
    else:
        lines.append("  (none configured on this pull request)")

    lines.append("")
    lines.append("Test suite (throwaway clone, stripped environment)")
    if result.test_head and result.test_head.get("ran"):
        head = result.test_head
        lines.append(f"  branch: {head['passed']} passed, {head['failed']} "
                     f"failed, {head['errors']} errors in {head['elapsed']}s")
        for name in head["failures"][:5]:
            lines.append(f"      failing: {name}")
        if result.test_base and result.test_base.get("ran"):
            base = result.test_base
            lines.append(f"  base  : {base['passed']} passed, "
                         f"{base['failed']} failed in {base['elapsed']}s")
            new = set(head["failures"]) - set(base["failures"])
            lines.append(f"  failures introduced by this branch: {len(new)}")
    elif result.test_head:
        lines.append(f"  not run: {result.test_head.get('reason')}")
    else:
        lines.append("  not run")

    lines.append("")
    lines.append("Merge gate")
    for gate in result.gates:
        lines.append(gate.line())

    manual = [g for g in result.gates if g.manual_fix and not g.ok]
    if manual:
        lines.append("")
        lines.append("Configuration to enable by hand (this repository has "
                     "none of it yet):")
        for gate in manual:
            lines.append(f"  - {gate.manual_fix}")

    lines.append("")
    for note in result.notes:
        lines.append(f"Note: {note}")
    lines.append(bar)
    return "\n".join(lines)


def request_changes_body(result: ReviewResult) -> str:
    parts = [
        REVIEW_MARKER,
        "Thanks for this pull request. An automated review found things that "
        "need attention before it can be merged.",
        "",
    ]
    for finding in result.blocking + result.important:
        where = finding.location()
        parts.append(f"**{finding.severity.title()} -- {finding.code}**"
                     + (f" (`{where}`)" if where else ""))
        parts.append(finding.message)
        if finding.why:
            parts.append(f"Why it matters: {finding.why}")
        if finding.fix:
            parts.append(f"Suggested fix: {finding.fix}")
        parts.append("")
    if result.test_head and result.test_head.get("ran"):
        head = result.test_head
        parts.append(
            f"I also ran the suite on your branch: {head['passed']} passed, "
            f"{head['failed']} failed."
        )
        parts.append("")
    parts.append("Push the fixes to this branch and the review can be re-run "
                 "against the new commits.")
    return "\n".join(parts)


def already_requested_changes(gh: GitHub, number: int, signature: str) -> bool:
    """Have we posted this exact review already?

    Matched on our marker plus the findings signature, so a genuinely new
    problem still earns a fresh request instead of being swallowed.
    """
    marker = f"findings:{signature}"
    mine = gh.user
    if not mine:
        return False
    for review in gh.reviews(number):
        # REST again: `user`, not `author` (see approval_state).
        if ((review.get("author") or review.get("user")
             or {}).get("login")) != mine:
            continue
        if (review.get("state") or "").upper() != "CHANGES_REQUESTED":
            continue
        body = review.get("body") or ""
        if REVIEW_MARKER in body and marker in body:
            return True
    for comment in gh.issue_comments(number):
        if (comment.get("user") or {}).get("login") != mine:
            continue
        body = comment.get("body") or ""
        if REVIEW_MARKER in body and marker in body:
            return True
    return False


def post_review(gh: GitHub, result: ReviewResult, number: int) -> Tuple[bool, str]:
    """Submit the request for changes, without repeating ourselves.

    Refuses when there is nothing blocking or important to ask for: asking a
    contributor to "change things" with no list attached is noise, not review.
    """
    if not (result.blocking or result.important):
        return False, "no blocking or important findings, so there is nothing to ask for"
    if not gh.user:
        # Without knowing our own login we cannot recognise an earlier review,
        # so posting could repeat ourselves. Refusing is the safer direction.
        return False, ("the authenticated GitHub login could not be determined, "
                       "so an existing request for changes cannot be ruled out")
    signature = result.signature()
    if already_requested_changes(gh, number, signature):
        return False, ("an identical request for changes is already posted; "
                       "nothing new to say")
    body = request_changes_body(result) + f"\n\nfindings:{signature}"
    if gh.submit_review(number, "REQUEST_CHANGES", body):
        return True, "review posted, requesting changes"
    if gh.comment(number, body):
        return True, ("the review API refused (often because the pull request "
                      "is your own); posted as a comment instead")
    return False, "could not post the review"


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def resolve_repo(explicit: Optional[str]) -> str:
    """owner/name, from the argument if given, else from the origin remote."""
    if explicit:
        return explicit
    proc = subprocess.run(
        ["git", "remote", "get-url", "origin"], capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60,
    )
    match = re.search(r"[:/]([^/]+/[^/]+?)(?:\.git)?$", (proc.stdout or "").strip())
    if not match:
        raise ReviewError("cannot determine the repository from the origin "
                          "remote; pass --repo OWNER/NAME")
    return match.group(1)


def main(argv: Optional[Sequence[str]] = None, gh: Optional[GitHub] = None) -> int:
    """Run the command. `gh` is injectable so the tests can drive the whole
    path -- including the merge gate -- without touching GitHub."""
    parser = argparse.ArgumentParser(
        prog="review_pr.py",
        description="Review a Critique pull request. Review only by default: "
                    "nothing is posted or merged unless you ask.",
    )
    parser.add_argument("number", type=int, help="pull request number")
    parser.add_argument("--merge", action="store_true",
                        help="merge if every gate passes; never overrides a "
                             "failed gate")
    parser.add_argument("--request-changes", action="store_true",
                        help="post a request for changes if blocking or "
                             "important findings exist")
    parser.add_argument("--merge-method", choices=["merge", "squash", "rebase"],
                        default=None,
                        help="merge style; defaults to the repository's own "
                             "configured default")
    parser.add_argument("--repo", default=None, help="OWNER/NAME")
    parser.add_argument("--skip-tests", action="store_true",
                        help="do not run the test suite")
    parser.add_argument("--test-timeout", type=int, default=900,
                        help="seconds allowed for each test run")
    args = parser.parse_args(argv)

    if args.merge and args.request_changes:
        print("choose one: --merge or --request-changes", file=sys.stderr)
        return 2
    if shutil.which("gh") is None:
        print("gh CLI not found. Install it: https://cli.github.com",
              file=sys.stderr)
        return 2

    gh = gh or GitHub()
    try:
        if not gh.repo:
            gh.repo = resolve_repo(args.repo)
        user = gh.verify_auth()
        repo_info = gh.repo_info()
    except ReviewError as exc:
        print(f"cannot start the review: {exc}", file=sys.stderr)
        return 2

    try:
        result = build_review(
            gh, args.number, repo_info, run_tests=not args.skip_tests,
            test_timeout=args.test_timeout,
        )
    except ReviewError as exc:
        print(f"cannot review #{args.number}: {exc}", file=sys.stderr)
        return 2

    print(render_report(result, user=user))
    exit_code = 0 if result.status == "READY" else 1

    if args.request_changes:
        print("")
        if result.blocking or result.important:
            ok, detail = post_review(gh, result, args.number)
            print(("Posted: " if ok else "Not posted: ") + detail)
            if not ok and result.status != "READY":
                exit_code = 1
        else:
            print("No blocking or important findings, so nothing was posted.")

    if args.merge:
        print("")
        failed = [g for g in result.gates if not g.ok]
        if failed:
            print("REFUSING TO MERGE: every gate must pass, and --merge does "
                  "not override a failure.")
            for gate in failed:
                print(f"  failed: {gate.name} -- {gate.detail}")
                if gate.manual_fix:
                    print(f"         fix: {gate.manual_fix}")
            exit_code = 1
        else:
            method = choose_method(repo_info, args.merge_method)
            if method is None:
                print("REFUSING TO MERGE: no merge method is enabled on this "
                      "repository.")
                exit_code = 1
            else:
                commits = len(result.pr.get("commits") or [])
                print(f"Merging #{args.number} with a {method} "
                      f"({commits} commit(s))...")
                ok, detail = gh.merge(args.number, method)
                print(detail or ("merged" if ok else "merge failed"))
                exit_code = 0 if ok else 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
