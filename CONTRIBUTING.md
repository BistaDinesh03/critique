# Contributing to Critique

Thanks for your interest in contributing! Critique is meant to be simple and
maintainable.

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

Expected: **346 passed**. Install [Node.js](https://nodejs.org) first — the
frontend-render tests need `node` on PATH and are skipped without it.

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
- Link any related issues
- Be respectful and patient

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

## Communication

- Be kind and constructive
- Assume good intentions
- Focus on the work, not the person

## First-Time Contributor Guide

Thanks for volunteering to contribute to Critique! You do not need to be
an experienced developer to help. Many contributions are documentation,
accessibility, or "good first issue" tasks that only require careful
reading and writing.

### Choosing an issue

- Start by looking for issues labeled [`good first issue`](
  https://github.com/BistaDinesh03/critique/labels/good%20first%20issue)
  — these are specifically scoped for newcomers.
- You can also filter issues by area (`frontend`, `backend`, `tests`,
  `accessibility`, `security`, `performance`) to match your skills or
  interests.
- If you are unsure whether an issue is the right scope, ask in [issue
  #1](https://github.com/BistaDinesh03/critique/issues/1) — no question
  is too small, and the maintainer can steer you.
- Read the full issue description, acceptance criteria, and testing
  instructions before commenting that you intend to work on it.

### Understanding the expected scope

- Each issue in the roadmap (`docs/issue-roadmap.md`) and on GitHub has
  acceptance criteria and a defined scope. Read these carefully before
  starting.
- If an issue seems too large or vague, comment asking for it to be
  broken down — maintainers will help refine it.
- Remember: small, focused pull requests are much easier to review and
  more likely to be merged quickly.

### Setting up the project

1. Fork the repository and clone your fork.
2. Create a virtual environment: `python -m venv .venv` and activate it.
3. Install dependencies: `pip install -r requirements.txt`.
4. Copy `.env.example` to `.env` (or `copy .env.example .env` on Windows)
   and set any needed environment variables.
5. Start the server: `cd backend && uvicorn app.main:app --reload`.
6. Open http://127.0.0.1:8000 in your browser.

Run `python -m pytest tests/ -q` to verify the test suite (expected:
**346 passed**). Note: frontend-render tests require Node.js on PATH and
are skipped without it.

### Following code conventions

- Follow existing patterns in the codebase — look at similar functions
  or components for style reference.
- Use meaningful names; keep functions small.
- Comment only where useful; avoid dead code.
- Follow the existing line ending and whitespace conventions (the
  repository uses LF line endings, UTF-8 without BOM).

### Writing a useful pull request description

Describe what you changed and why, using this structure:

- **Summary:** One sentence on what the PR changes.
- **Problem/issue:** Link to the issue you are solving (e.g., `Fixes #853`).
- **What changed:** Bullet list of the specific files modified and why.
- **How tested:** The exact test command you ran and the result (e.g.,
  `python -m pytest tests/ -q — passed all 346 tests`).
- **Self-review:** Note any known limitations or areas where you welcome
  feedback.

### Responding to review feedback

- Read each piece of feedback carefully; the maintainer's goal is to help
  your contribution land, not to critique you personally.
- Make changes in small, discrete commits on your branch — do not squash
  or rebase unless the maintainer requests it.
- If you disagree with a comment, start a constructive discussion in the
  PR — assume good intentions.
- After making changes, request a re-review by commenting `Review please`
  or `python scripts/review_pr.py PR_NUMBER --request-changes`.

You are always welcome to ask questions in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)
or on the PR discussion. The maintainer is happy to help you through the
process.

## Reporting a security issue

Please do not open a public issue for a vulnerability. Follow the private
process described in [SECURITY.md](SECURITY.md), which also documents the
project's security-relevant behavior. For anything that is not a
vulnerability, [issue #1](https://github.com/BistaDinesh03/critique/issues/1)
is a good place to ask.

## License

By contributing, you agree your work will be licensed under the MIT License.
