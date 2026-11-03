# Pull request review tool

`scripts/review_pr.py` is the maintainer's one command for reviewing a
contributor's pull request: it finds problems, says what to change, and merges
only when nothing stands in the way.

```bash
python scripts/review_pr.py 123                      # review and report only
python scripts/review_pr.py 123 --request-changes    # also post the review
python scripts/review_pr.py 123 --merge              # merge if every gate passes
```

The default is non-destructive. Without an explicit flag it reads the pull
request and prints a report; it does not post, comment, merge, push, or touch
the contributor's fork.

## Requirements

| Requirement | Why |
|---|---|
| [`gh` CLI](https://cli.github.com) installed | every GitHub call goes through it |
| `gh auth login` completed | read the pull request, post reviews, merge |
| `git`, and a clone of this repository | the tool reads `origin` to learn which repository it is in |
| Python 3.11+ | the tool itself |
| Node.js on `PATH` | only for the frontend-render tests inside the suite |

Run it from anywhere inside a clone. Pass `--repo OWNER/NAME` if `origin` does
not point at the repository you mean.

## What it checks

Findings are split by how much they matter, and every one carries the reason
it was raised plus a suggested fix.

**Blocking** — a pull request that should not be merged as it stands:

| Code | What it means |
|---|---|
| `SECRET` | An added line looks like a private key, token, or hard-coded credential |
| `FORBIDDEN_PATH` | A committed `.env`, database file, cache, or `node_modules` |
| `CONFLICT_MARKERS` | `<<<<<<<` or `>>>>>>>` committed into a file |
| `CONFLICT`, `WRONG_BASE`, `DRAFT`, `UNREACHABLE` | The pull request cannot be judged or merged in its current state |
| `CHECKS_FAILED`, `CHECKS_RUNNING`, `CHECKS_UNKNOWN` | A required check failed, has not finished, or reported a state this tool cannot read |
| `CHANGES_REQUESTED_EXISTING` | A reviewer has changes outstanding that were never addressed |
| `TEST_FAILURES` | The suite fails on this branch but passes on the merge base — a regression, or the same test failing here for a different reason than on the base |

**Important** — legitimate to merge in principle, but nobody should merge it
without a second look:

| Code | What it means |
|---|---|
| `UNSAFE_CODE` | `shell=True`, `eval`, `pickle.loads`, disabled TLS, skipped hooks, newly skipped tests, and similar |
| `TESTS_MISSING` | Source changed with no test change |
| `TESTS_DELETED` | Test files removed or renamed |
| `SENSITIVE_PATH` | `SECURITY.md`, `render.yaml`, `.env.example`, `.github/`, the analytics route, or the analytics snapshot |
| `SCOPE` | More files or lines than the guideline allows for this kind of change |
| `NO_DESCRIPTION`, `NO_TEST_EVIDENCE` | The pull request body does not say what changed, or which tests ran |
| `BODY_REPORTS_FAILURES` | The description itself reports failing tests (minor if it calls them pre-existing, which the automated run then confirms) |
| `BEHIND` | The branch is behind the default branch, so tests would run against the wrong tree |
| `TESTS_NOT_RUN` | The suite could not be run here, so nothing at all is claimed about it |

**Minor** — worth a sentence, never a blocker: a title that does not follow
the `type: summary` form, no linked issue, trailing whitespace, one very large
file, and two heuristic checks.

Both heuristic checks say so in their output, because they are inference
rather than observation: `UNRELATED` looks for changed files whose names share
no words with the title or description, and `TITLE_FORMAT` compares against
this repository's commit history.

## How the test suite is run

The suite is run twice — once on the pull request's head commit and once on
the merge base — so that this branch is blamed only for failures it actually
introduced:

- **New failure** (present on the branch, absent on the base) → `TEST_FAILURES`,
  blocking.
- **Same test, different failure** (the node id matches but the failure reason
  changed) → `TEST_FAILURES`, blocking: matching names alone do not make a
  failure harmless.
- **Failure on both, for the same reason** → `PREEXISTING_FAILURES`, minor, and
  explicitly not the contributor's fault. The *reasons* are compared, after
  normalising only values that differ between any two runs (temporary paths,
  mock object ids, generated ids), so a changed cause cannot hide behind a
  matching test name.
- **Base could not be run** → the failures are reported as blocking, because
  nothing has been shown to be pre-existing.
- **Cannot be run at all** → `TESTS_NOT_RUN`, with the reason. A review that
  says "looks fine" without running anything is guessing, so this is reported
  rather than assumed.

Both runs happen in a throwaway clone under the system temporary directory:

- The clone has no `.env`, no database files, and no local git configuration,
  because those are untracked and never copied.
- The test process receives a stripped environment containing only what Python
  and Git need to start. No `GITHUB_TOKEN`, no `GH_TOKEN`, no cloud keys.
- A fork's commits are fetched anonymously into that clone (`refs/pull/N/head`
  is public on a public repository). The maintainer's own repository is never
  fetched into or modified.
- The clone is deleted afterwards, with retries, because Windows hands back
  locked files for a moment.

Use `--skip-tests` to leave the suite out; the report then says plainly that
nothing is claimed about it. `--test-timeout` (default 900 seconds) caps each
run.

## The merge gate

`--merge` runs the same review first, then requires every gate:

1. Review status is `READY` — no blocking or important findings.
2. The pull request is mergeable: no conflict, and GitHub reports a state that
   means "can be merged". `BLOCKED`, `UNKNOWN`, or no answer at all fails here.
3. Every configured check passed. A check in a state this tool cannot read
   counts as a failure, never as a pass.
4. The required number of approvals is present, and GitHub agrees: its own
   `reviewDecision` of `REVIEW_REQUIRED` or `CHANGES_REQUESTED` fails this
   gate even when the count looks satisfied, and an approval the repository
   would dismiss as stale does not count.
5. Branch protection is configured on the default branch.
6. Continuous integration is configured.

`--merge` never overrides a failed gate, never force-pushes, and never deletes
a branch. When it refuses, it prints each failing gate and what to do about
it. The merge method defaults to the repository's own configured default
(merge commits here), and `--merge-method {merge,squash,rebase}` overrides it
— but only with a method the repository still allows.

### Configuration that has to be enabled by hand

Two gates depend on settings that a script cannot change, and this repository
currently has neither. Until both exist, `--merge` refuses by design: with
nothing configured, no approval and no check is actually required before
merging, so the gate would be a rubber stamp.

In this order:

1. **Add CI.** Create `.github/workflows/tests.yml`:

   ```yaml
   name: tests
   on:
     pull_request:
     push:
       branches: [main]
   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-python@v5
           with:
             python-version: "3.11"
         - run: pip install -r backend/requirements.txt
         - uses: actions/setup-node@v4
           with:
             node-version: "20"
         - run: python -m pytest tests/ -q
           working-directory: backend
           env:
             # See the note below: without this the OAuth state test fails
             # on any machine that has no .env -- including this runner.
             GITHUB_CLIENT_ID: ${{ vars.OAUTH_CLIENT_ID || 'ci-test-client-id' }}
   ```

   > **Why there is a fallback literal.**
   > GitHub does not pass repository variables (or secrets) to workflows
   > triggered by pull requests **from forks** — only pushes inside the
   > repository receive them. A fork run therefore sees an empty
   > `vars.OAUTH_CLIENT_ID` and the OAuth test would fail on every external
   > pull request. The `||` fallback gives those runs a literal that keeps the
   > test's contract intact (the authorize URL must carry exactly what is
   > configured), while push runs to `main` still use the real variable.

   > **Why the variable is `OAUTH_CLIENT_ID` and not `GITHUB_CLIENT_ID`.**
   > GitHub rejects any Actions *variable* or *secret* whose name starts with
   > `GITHUB_` (HTTP 422: "Variable names must not start with GITHUB_"), so
   > the command `gh variable set GITHUB_CLIENT_ID` cannot run at all. The
   > variable is therefore named `OAUTH_CLIENT_ID`, and the workflow maps it
   > onto the process variable the application itself reads,
   > `GITHUB_CLIENT_ID`.
   >
   > **Why `GITHUB_CLIENT_ID` is in that workflow.**
   > `backend/app/config.py` defaults it to an empty string, and
   > `tests/test_oauth_state.py` asserts against the `client_id` in the
   > authorize URL. `urllib.parse.parse_qs` drops blank values, so on a
   > machine with no `.env` — a clean clone, a fresh CI runner — that one
   > test fails with `KeyError: 'client_id'`. It fails the same way on every
   > branch, so the tool reports it as pre-existing instead of blaming the
   > pull request, but it will still turn a required check red. Set the
   > `OAUTH_CLIENT_ID` repository variable (a GitHub OAuth client id is not
   > secret; a repository *variable*, or a default in `config.py`, both work)
   > **before** making the check required. Repairing that test is a separate
   > change and is deliberately not done by this tool.

2. **Protect the default branch.** Settings → Rules → Add branch rule for
   `main`, then enable:
   - Require a pull request before merging
   - Require 1 approval
   - Require status checks to pass before merging — add `test` once the
     workflow above has run at least once (GitHub only offers checks that
     have reported before)

Reviewing works before either is enabled; only `--merge` waits for them.

## Requesting changes

`--request-changes` posts a GitHub review with the blocking and important
findings. It is not posted at all when there is nothing at that level to ask
for — asking a contributor to "change things" with no list attached is noise,
not review.

It will not repeat itself. Every review carries a marker and a hash of the
findings, and before posting the tool re-reads the pull request's reviews and
comments looking for the same pair. An identical request is skipped; a
genuinely new finding is posted, because the hash differs. Posting a request
for changes changes the pull request's review state, and that change is
deliberately excluded from the hash — otherwise every re-run would post again.

If GitHub refuses the review API (the usual reason being that you are
reviewing your own pull request), the same text is posted as an ordinary
comment instead, and the report says so.

Re-running after new commits is the intended workflow: the review is computed
from the current head, so fixes clear their findings and new problems appear.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | The review completed and the pull request is `READY`, or the merge succeeded |
| `1` | The review completed but the pull request is `CHANGES_REQUESTED` or `BLOCKED`, or the merge was refused |
| `2` | The review could not run: bad usage, no `gh`, no authentication, or the pull request does not exist |

## Limitations

Stated plainly, because a review tool that overstates itself is worse than
none:

- **It is not a substitute for reading the diff.** It finds patterns; it does
  not judge whether a change is a good idea, whether it matches the project's
  intentions, or whether a test actually tests anything.
- **Unresolved review *threads* are not checked.** GitHub exposes them only
  through GraphQL; the tool reads the review decisions instead.
- **No browser or device is exercised.** A change to the frontend is checked
  by the render tests and by static analysis, never by looking at a page.
- **Static analysis misses things.** It is tuned for precision over recall: a
  missed exotic secret is accepted as a cost to avoid false accusations of
  leaking one. Read the diff for the security-relevant files.
- **Test blame is only as good as the suite.** A branch can pass the suite and
  still be wrong.
- **It never merges on its own.** It does not auto-merge from its own
  analysis, and nothing in it can bypass branch protection.
- **Duplicate suppression has not been exercised against a review posted by this tool.** Pull requests in this repository have received human and bot reviews, but none of the reviews checked contains the tool's `<!-- critique-review-pr -->` marker. The re-read-before-posting check has therefore been tested against empty review state and review objects in GitHub's documented shape, but not against a review previously posted by this tool. The first real `--request-changes` is worth watching, and it is a comment rather than anything destructive if the de-duplication misreads the situation.

## Troubleshooting

| Symptom | Cause |
|---|---|
| `gh CLI not found` | Install it, or fix `PATH` |
| `gh is not authenticated` | Run `gh auth login` |
| `cannot determine the repository` | Run from inside a clone whose `origin` is this repository, or pass `--repo` |
| `pull request #N was not found` | A typo, or a pull request in another repository |
| `TESTS_NOT_RUN` with "not available locally and could not be fetched" | No network, or a commit that is not reachable from `refs/pull/N/head` — run the suite yourself and paste the result |
| `Test run exceeded 900s` | Raise `--test-timeout`, or use `--skip-tests` and run it by hand |
