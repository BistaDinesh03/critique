# Contributing to Critique

Thanks for your interest in contributing! Critique is meant to be simple and
maintainable.

> Translations: [简体中文](CONTRIBUTING.zh-CN.md) ·
> [日本語](CONTRIBUTING.ja.md) · [Español](CONTRIBUTING.es.md) —
> this English file is the canonical version.

## Getting Started

If you are contributing for the first time, check out our step-by-step [Contributor Onboarding Guide](docs/contributing-start.md).

1. Fork the repository
2. Clone your fork
3. Create a branch for your change
4. Make your changes
5. Run the tests
6. Submit a pull request

### Set up a development environment

```bash
git clone https://github.com/YOUR_USERNAME/critique.git
cd critique
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
cd backend
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. Authentication providers are optional for local
browsing — see [docs/github-oauth-setup.md](docs/github-oauth-setup.md) if
your change needs signed-in flows. For common local setup issues and solutions,
see [docs/troubleshooting.md](docs/troubleshooting.md).

### Run the tests

```bash
cd backend
GITHUB_CLIENT_ID=ci-test-client-id python -m pytest tests/ -q
```

On Windows (PowerShell):

```powershell
cd backend
$env:GITHUB_CLIENT_ID = "ci-test-client-id"
python -m pytest tests/ -q
```

Expected: a clean run. The suite grows with almost every PR, so trust
pytest's own summary (and the CI `test` check) rather than a hardcoded
count in this file. Install [Node.js](https://nodejs.org) first — the
frontend-render tests need `node` on PATH and are skipped without it.

For a faster feedback loop while working on a focused change, run a single
test file, a specific test function, or tests matching a keyword:

```bash
python -m pytest tests/test_main.py -q
python -m pytest tests/test_main.py::test_health_check -q
python -m pytest tests/ -q -k health_check
```

The frontend-render test modules are skipped when `node` is not on PATH.
This is expected when you run the suite locally; install Node.js if your
change affects frontend rendering. In CI the behavior is deliberately the
opposite: the collection guard in `backend/tests/conftest.py` fails the run
when `node` is missing, so render tests can never skip silently there.

When adding a frontend-render test module, copy this module-level `pytestmark` block:

```python
pytestmark = [
    pytest.mark.frontend_render,
    pytest.mark.skipif(
        shutil.which("node") is None,
        reason="node is required to run the frontend rendering harness",
    ),
]
```

The `frontend_render` marker is what lets the CI collection guard identify render tests. CI fails if `node` is missing and marked render tests would otherwise be skipped; a module missing the marker is not yet caught automatically (see [#154](https://github.com/BistaDinesh03/critique/issues/154)).

To run only the frontend-render tests locally:

```bash
python -m pytest tests/ -m frontend_render -q
```

For full details on scenario construction and DOM stub capabilities, see the [Frontend Render Test Harness guide](docs/frontend-render-harness.md).

## Development Guidelines

### Keep it simple

Critique intentionally avoids complexity. Before adding anything, ask:

- Does this solve a real problem?
- Can it be done with fewer dependencies?
- Does it need to be in V1?

### Code style

- Follow existing patterns
- Use meaningful names
- Keep functions small
- Comment only where useful
- No dead code

### Database changes

Critique has no migration framework. Schema changes to existing tables are
applied at startup by `backend/app/database.py`, and they must follow a strict
contract: guarded on `inspect()`, idempotent, additive, applied on both SQLite
and PostgreSQL, and loud on failure. Read
[docs/database-migrations.md](docs/database-migrations.md) before changing a
model.

### Testing

- Run all tests before submitting
- Add tests for new functionality
- Tests must pass with 0 failures

### Pull requests

- Keep PRs focused and small
- Describe what you changed and why
- No secrets, unrelated changes, or test results you did not actually run
- Link any related issues
- Be respectful and patient

For a step-by-step example of claiming an issue, working in a fork, running relevant checks, and opening a pull request, see the [first-contributor walkthrough](docs/first-contributors.md).

Changes that affect layout should also run the visual regression suite.
[docs/visual-regression.md](docs/visual-regression.md) explains what the
baselines cover and how to update them when a visual change is intentional.

## Welcome to new contributors

Thanks for your interest in contributing to Critique!

Before starting, please comment on the issue so we can confirm it is still
available. We'll help you understand the implementation and review your
contribution.

We appreciate every meaningful contribution, whether it's code, tests,
documentation, or feedback.

### First-contribution checklist

1. Read [README.md](README.md), skim [docs/architecture.md](docs/architecture.md), and [docs/first-contributors.md](docs/first-contributors.md).
2. Pick an issue from the [Good issues to contribute](README.md#good-issues-to-contribute) list.
3. Comment on the issue to claim it (maintainers confirm availability).
4. Fork, branch, implement, and add tests.
5. Run the relevant test suite and `git diff --check`.
6. Open a pull request linking the issue, describing what changed and why.

### Maintainer welcome template

When a new contributor opens their first issue or PR, reply with:

> Thanks for your interest in contributing to Critique!
>
> Before starting, please comment on the issue so we can confirm it is still
> available. We'll help you understand the implementation and review your
> contribution.
>
> We appreciate every meaningful contribution, whether it's code, tests,
> documentation, or feedback.

Do not promise instant reviews or unrealistic response times.

## Finding Something to Work On

Open issues labeled [`good first issue`](https://github.com/BistaDinesh03/critique/labels/good%20first%20issue)
are a good place to start. Got a question about the codebase or an approach?
Ask in [issue #1](https://github.com/BistaDinesh03/critique/issues/1) before
starting — no question is too small.

Issues are also labeled by **area** and by **difficulty**, so you can filter for
work that matches what you know — or deliberately stretch into something new.
Both are documented in [The label taxonomy](#the-label-taxonomy) below.

For a verified list of work that is actually available, use
[docs/contributor-opportunities.md](docs/contributor-opportunities.md). Every issue
on that page is open, unassigned, not claimed in a comment, and not attached to an
open pull request, and the page states the date it was last checked against the
tracker. It is the only list you should act on.

[docs/issue-roadmap.md](docs/issue-roadmap.md) also exists, but it is a **dated
historical record** from 2026-10-17 — many of its rows have since shipped. Read it
for context, not for a task.

### Triage, labels and issue lifecycle

So that this page stays trustworthy, issues follow a simple lifecycle:

- **Open and unclaimed** — the issue is real, nobody is on it. Comment to claim it.
- **Assigned** — someone is working on it. The assignee is shown on the issue.
- **Blocked** — an open pull request or an unresolved design question stands in the
  way. Comment and ask before starting; the blocker may be resolvable.
- **Closed as resolved** — the behaviour shipped. The closing comment names the file
  and test that prove it.
- **Closed as duplicate** — an earlier issue covers the same work. The closing
  comment links the canonical issue, which stays open.
- **Closed as not planned** — the idea is out of scope or has no scoped path right
  now. This is not a judgement on the idea; it can be reopened with a concrete use
  case.

Two conventions matter when you pick up work:

1. **The tracker is a queue, not a wishlist.** An issue is only created when someone
   intends to work on it. Broad ideas belong in
   [issue #1](https://github.com/BistaDinesh03/critique/issues/1) or Discussions first.
2. **`good first issue` means small, unblocked, and unclaimed.** If an issue carrying
   that label is assigned or has an open pull request, the label is wrong — say so and
   it will be removed.

#### The label taxonomy

Labels answer two questions: *what is this about*, and *how hard is it*.

**Area labels** say which part of the codebase an issue touches.

| Label | Meaning |
|-------|---------|
| `frontend` | UI, styling and browser-side behaviour |
| `backend` | Server-side, API and database work |
| `tests` | Test coverage, harnesses and CI checks |
| `security` | Hardening, vulnerabilities and privacy |
| `performance` | Speed, caching and resource use |
| `accessibility` | Barrier affecting people with disabilities |
| `documentation` | Improvements or additions to documentation |

Some issues also carry an `area:*` label — for example `area: growth` or
`area: feedback` — recording which part of the product plan the issue came from.
Area labels describe *place*. They say nothing about difficulty.

**Difficulty labels** say how much context a change needs.

| Label | Meaning | Roughly |
|-------|---------|---------|
| `beginner` | Small, well-scoped first contribution | one file and one test |
| `intermediate` | Requires cross-component work or design judgment | a few files, an existing pattern to follow |
| `advanced` | Deep work: concurrency, migrations, performance, observability | a design decision plus new tests |

An issue should carry exactly one difficulty label. If one is missing or looks
wrong, say so in the issue and it will be corrected — the label is a promise
about scope, and a broken promise costs a contributor a weekend.

Other labels you will see: `good first issue` (small, unblocked, unclaimed),
`help wanted` (a contribution would be welcome), `bug`, `enhancement`,
`duplicate`, and the automation labels (`dependencies`, `python`,
`github_actions`).

#### Choosing work that fits

1. Decide how much time you have. A `beginner` issue is an evening; an
   `advanced` one is a project.
2. Filter by the area you know, or by the area you want to learn.
3. Check nothing blocks it: no assignee, no open pull request, and no
   claim comment.
   [docs/contributor-opportunities.md](docs/contributor-opportunities.md) has
   already done this check for you.
4. Comment on the issue with your plan before writing code. For anything past
   `beginner`, the maintainer would rather agree on the approach first than
   review a large PR in the wrong direction.

## How we work together on Critique

Critique is a site where builders ask one focused question and other people
answer it. Contributors are asked to use the product the same way they would
ask others to use theirs — it is the fastest way to understand what the
project is for.

For a typical code contribution:

1. **Claim the issue.** Comment on the issue to say you intend to work on
   it. This avoids two people doing the same work, and it lets the maintainer
   steer you early if the approach needs a rethink.
2. **Use Critique once.** Submit a project with one focused question, or give
   useful feedback on someone else's project. You are not being audited — this
   is so your first pull request is informed by the product rather than only
   the code.
3. **Fork and branch.** Fork the repository, create a branch, and implement
   the issue.
4. **Test, and dogfood if it applies.** Run the relevant tests. If your change
   alters something a visitor would see, try it on Critique itself and ask
   other builders whether it works.
5. **Open the pull request.** Describe what you changed, why, and the exact
   tests you ran.

### Exceptions, stated plainly

This guideline is deliberately light, and it is **not** a gate. It does not
apply to:

- **Documentation, accessibility, and security fixes** — these help people
  who cannot necessarily use the site as others do, and requiring product
  participation first would be a barrier in exactly the wrong place.
- **Your first contribution** — one contribution is enough. Nobody is asked
  to participate repeatedly to stay welcome.
- **Bug reports and issue triage** — these are contributions on their own.

There is no cost to participate, no payment is ever requested, and no
personal information beyond a GitHub account is needed. Nothing on GitHub can
verify that you used the site, and we will not ask you to prove it — the
step exists to help you, not to police you.

## For maintainers: reviewing a pull request

Reviews are run with one command, from a clone of this repository:

```bash
python scripts/review_pr.py 123                      # review and report only
python scripts/review_pr.py 123 --request-changes    # also post the review
python scripts/review_pr.py 123 --merge              # merge only if every gate passes
```

The default is non-destructive: it reads the pull request, analyses the diff,
runs the test suite in a throwaway clone with a stripped environment, and
prints a report. It never pushes to a contributor's branch, never modifies a
fork, and never merges without `--merge`. The flag does not override a failed
gate — a pull request with a failing check, an unresolved blocker, or a
missing approval is refused, and the report says which gate and why.

Each report ends with `READY`, `CHANGES_REQUESTED`, or `BLOCKED`, followed by
the merge gate as a checklist. Continuous integration and branch protection
on the default branch (`main`) are actively configured: every pull request runs
the required `test` check via GitHub Actions, and `main` requires passing status
checks, strict up-to-date branch alignment, 1 approval, and conversation
resolution with administrator enforcement. `--merge` enforces these gates and
refuses if any check, approval, or gate remains unsatisfied.

Full usage, what each check means, and the limitations:
[docs/pull-request-review.md](docs/pull-request-review.md).

The surrounding workflow — finding unclaimed work, assigning an issue to
somebody who has asked for it, checking a pull request's linked issues, and
closing and thanking only once a merge is confirmed — is
`scripts/contributor.py`. It reuses the review tool above for every judgement
about the code, and adds the issue-side work:

```
python scripts/contributor.py triage                    # what can somebody work on?
python scripts/contributor.py assign 30 --user USERNAME # only if they asked for it
python scripts/contributor.py review 57                 # read-only, adds issue context
python scripts/contributor.py finalize 57 --merge       # merge, close, thank
```

It will not assign an issue to somebody who has not commented asking for it,
close an issue that is merely mentioned in a description, thank a contributor
before the merge is confirmed, or send a second message. Full usage:
[docs/contributor-workflow.md](docs/contributor-workflow.md).

For the project-specific review checklist, see the [Maintainer Pull Request Review Checklist](docs/maintainer-guide.md).

## Communication

- Be kind and constructive
- Assume good intentions
- Focus on the work, not the person

All participation in this project is covered by the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Reporting a security issue

Please do not open a public issue for a vulnerability. Follow the private
process described in [SECURITY.md](SECURITY.md), which also documents the
project's security-relevant behavior. For anything that is not a
vulnerability, [issue #1](https://github.com/BistaDinesh03/critique/issues/1)
is a good place to ask.

If you find Critique useful or appreciate the project, consider starring the
repository. It helps others discover the project. Starring is entirely
optional and has no effect on issue assignment, reviews, or merging.

## License

By contributing, you agree your work will be licensed under the MIT License.
