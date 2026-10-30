# Contributor management tool

`scripts/contributor.py` is the maintainer's workflow from first contact to
thank-you: triage unclaimed work, assign it to somebody who actually asked for
it, review the resulting pull request, and merge, close, and thank only when
the work is genuinely done.

It contains **no review logic of its own**. Every finding, every gate and every
merge decision comes from [`review_pr.py`](pull-request-review.md), which has
its own tests and its own document. This tool adds the issue-side work that the
review engine has no opinion about, and it refuses to do anything the review
engine would refuse to do.

## Requirements

- Python 3.11, no extra packages.
- The [`gh` CLI](https://cli.github.com), authenticated with a token that can
  read the repository. Merging, closing issues and commenting need a token with
  write access.
- A working directory where `gh` resolves the repository (run from inside the
  clone), or pass `--repo OWNER/NAME`.
- To merge: the manual configuration described at the end of
  [`pull-request-review.md`](pull-request-review.md#configuration-that-has-to-be-enabled-by-hand).
  That is a repository setting, not a flag. Without it, `finalize --merge`
  refuses and prints the steps.

## The four commands

```
python scripts/contributor.py triage                        # what can somebody work on?
python scripts/contributor.py assign 30 --user Venius24     # only if they asked
python scripts/contributor.py review 57                     # read-only, adds issue context
python scripts/contributor.py finalize 57 --merge           # merge, close, thank
```

### triage

Lists open issues that are unclaimed and offered as suitable work, best first.

For each one it prints the labels, the files the issue says it touches, how
many acceptance criteria it records, and the command to run its tests, so a
newcomer can decide before commenting. Issues somebody has already commented
on but which nobody is assigned to are listed separately as "already spoken
for" — the tool will not offer work that two people might both start.

Filters: `--label NAME` (repeatable), `--limit N`, `--json`.

Read-only. It writes nothing to GitHub.

### assign ISSUE --user USERNAME

Assigns an issue, but only when it is safe to do so. It refuses, without
writing anything, when:

- the issue is missing, closed, or locked;
- somebody else is already the assignee (it does not take work away);
- the same person is already assigned (it reports "nothing to do" so re-running
  is a no-op rather than a second notification);
- **the person being assigned has not asked for the issue in a comment.**

That last rule is the important one. Assignment requires evidence: a comment
from that user on that issue containing a request to work on it ("I'd like to
work on this", "Could you please assign it to me", "I plan to…", and similar).
The tool checks the actual comments, matched to that user's login, case
insensitively. It never assigns work to somebody who has not volunteered, and
`--comment` — which posts a short reply — is refused for the same reason. By
default no comment is posted at all: GitHub's own assignment notification
reaches them.

### review PULL_REQUEST

Runs the review engine and prints its report unchanged, then adds two sections
the engine does not produce:

- **Linked issues** — which issues the description refers to, whether each is
  opened by a closing keyword (`Fixes #N`) or only mentioned, whether it is
  still open, what files it says it touches, and how many of its acceptance
  criteria are still unticked.
- **Confirmed / suggested / uncertain** — the engine's findings split three
  ways: confirmed defects (observed in the diff, the checks, or the suite),
  suggestions (minor, never blockers), and uncertainty (the two heuristic
  checks, which are pattern matching and say so).

`--request-changes` posts the review, reusing `review_pr.post_review`, so it is
idempotent: a second run against the same commits posts nothing. Without that
flag the command is read-only. It never merges.

### finalize PULL_REQUEST --merge

The whole end of the workflow. Without `--merge` it only *reports* what a
merge would need — what would close, what would stay open, which gates pass.

With `--merge` it:

1. runs the review engine, including the test suite on the head commit;
2. re-checks that the repository still has CI and branch protection configured
   (a re-run must not assume yesterday's settings);
3. inspects every linked issue and classifies it:
   - **closing** — linked with `Fixes`/`Closes`/`Resolves`, still open, and the
     change touches at least one file the issue itself names. These are the
     only issues it will close.
   - **held open** — linked with a closing keyword, but the change touches
     none of the files the issue names. This adds a *failing* gate: it will not
     merge until the description is corrected or the reference removed.
   - **mentioned only** — referenced without a closing keyword. Never closed.
   - **already closed / unreadable** — reported, left alone.
4. merges only if **every** gate passes, then **re-reads the pull request** to
   confirm GitHub actually reports it as merged;
5. closes only the issues classified as closing, and only if the re-read
   confirmed the merge;
6. posts the thank-you, only if the merge is confirmed and no thank-you has
   already been posted.

Options: `--merge-method merge|squash|rebase` (refused, not silently swapped,
if the repository disallows it), `--no-close` (merge but leave every issue
open), `--no-thanks` (skip the thank-you), `--skip-tests`,
`--test-timeout SECONDS`.

### What finalize will not do

It will not close an issue that is merely mentioned, take a gate's word for
something it did not verify, thank a contributor before the merge is confirmed,
thank one twice, push to a fork, or touch a contributor's branch. An explicit
`--merge-method` that the repository disallows is refused rather than quietly
replaced by another method.

## Acceptance criteria, honestly

Issues in this repository carry their acceptance criteria as checkboxes, and
`finalize` shows every unticked one so you can confirm them by eye. It does not
tick them and it does not claim they passed: criteria like "the language is
welcoming" are judgement, and a tool that said otherwise would be lying.

What it *can* verify objectively, and does, is that the issue is linked with a
closing keyword, that it is still open, and that the pull request touches at
least one of the files the issue names. If an issue names files and the change
touches none of them, the merge is blocked.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Done, or reported without incident (including `--merge` on an already merged pull request). |
| 1 | Refused or needs work: a gate failed, the issue was not assignable, the review found blockers. |
| 2 | Could not run: no `gh`, no authentication, the repository could not be resolved, the issue list could not be read. |

## Permissions

| Command | Reads | Writes |
|---|---|---|
| `triage` | issues | none |
| `assign` | one issue, its comments | the issue's assignees; optionally one comment |
| `review` | pull request, diff, checks, reviews, linked issues | a review, only with `--request-changes` |
| `finalize` | everything `review` reads, plus the linked issues | one merge, the closing of linked issues, one thank-you comment |

## Testing

The tests in `backend/tests/test_contributor.py` all use a fake client. No test
assigns a real issue, closes a real issue, merges a real pull request, or posts
a real comment. The fake records writes so the tests assert both what must
happen and what must never happen: without a volunteer's comment, with someone
else holding the issue, before a merge is confirmed, for a merely mentioned
issue, on a second thank-you.

```
cd backend && python -m pytest tests/test_contributor.py -q
```

## Troubleshooting

**"issue #N was not found"** — the number is an issue, not a pull request, and
the tool only reports what the API said. Check the number.

**"X has not asked for issue #N"** — this is the tool working. Ask the person
to comment on the issue first; it is what CONTRIBUTING tells contributors to
do, and it means they have read the issue.

**`finalize --merge` refuses citing CI or branch protection** — see the manual
setup in [`pull-request-review.md`](pull-request-review.md#configuration-that-has-to-be-enabled-by-hand).
Both have to be enabled in the repository by hand; no flag here can substitute,
and none will.

**"an identical request for changes is already posted"** — you already ran
`review --request-changes` for these findings. Re-running would be a duplicate.

**"already merged; nothing to do"** — the pull request is merged. This run
performed no merge, so it closes nothing and thanks nobody: it will not take
credit for, or comment on, a merge it did not make.
