# Contributing to Critique

Thanks for your interest in contributing! Critique is meant to be simple and
maintainable.

> Translations: [简体中文](CONTRIBUTING.zh-CN.md) ·
> [日本語](CONTRIBUTING.ja.md) · [Español](CONTRIBUTING.es.md) —
> this English file is the canonical version.

## Getting Started

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
your change needs signed-in flows.

### Run the tests

```bash
cd backend
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

## Finding Something to Work On

Open issues labeled [`good first issue`](https://github.com/BistaDinesh03/critique/labels/good%20first%20issue)
are a good place to start. Got a question about the codebase or an approach?
Ask in [issue #1](https://github.com/BistaDinesh03/critique/issues/1) before
starting — no question is too small.

Issues are also labeled by area — `frontend`, `backend`, `tests`,
`accessibility`, `security`, `performance` — so you can filter to work that
matches what you know, or deliberately stretch into something new.

A curated, reviewed plan of 50 issues lives in
[docs/issue-roadmap.md](docs/issue-roadmap.md). Each entry states its
difficulty, the problem it solves, and which files it touches. If you are
looking for something concrete, start there.

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
the merge gate as a checklist. Two of those gates depend on repository
settings that cannot be checked by a script: continuous integration, and
branch protection on the default branch. Until both are configured in
Settings, `--merge` refuses — deliberately, because with nothing configured
no check and no approval is actually required before merging. The report
prints the exact steps each time.

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
