# First-contributor walkthrough

This guide takes one small documentation change from an open issue to a pull request. The example uses this repository's contribution workflow; use the same steps for another issue, adjusting the files and tests to match the change.

## 1. Choose and claim an issue

1. Read the issue description, scope, and acceptance criteria. Check that nobody else is already working on it.
2. Leave a comment on the upstream issue saying what you intend to change. Wait for any maintainer guidance if the issue asks for an approach before implementation.
3. Keep the change focused on that issue.

For this example, the work is documentation: add a guide under `docs/` and link to it from `README.md` and `CONTRIBUTING.md`.

## 2. Fork and clone

Use GitHub's **Fork** button on [the upstream repository](https://github.com/BistaDinesh03/critique), then clone your fork. Replace `YOUR_USERNAME` with your GitHub username:

```bash
git clone https://github.com/YOUR_USERNAME/critique.git
cd critique
git remote add upstream https://github.com/BistaDinesh03/critique.git
git remote -v
```

The `origin` remote should point to your fork; `upstream` should point to `BistaDinesh03/critique`. If you already added `upstream`, do not add it a second time.

## 3. Create a branch

Start from the latest upstream default branch:

```bash
git fetch upstream
git switch main
git pull --ff-only upstream main
git switch -c docs/short-description
```

Use a short branch name that describes the change. If your local `main` has local work you need to keep, do not overwrite it; create a clean working branch from the updated upstream branch instead.

## 4. Make one focused change

Edit only the files needed for the issue. Follow the existing Markdown style and links, and check the diff before committing:

```bash
git status --short
git diff --check
git diff
```

For a documentation-only change, confirm that relative links point to real repository paths and that commands match the project's current setup. Do not include unrelated formatting changes.

## 5. Run relevant checks

Use the check that matches your change. For backend behavior, install the project's requirements as described in [CONTRIBUTING.md](../CONTRIBUTING.md), then run the full suite or the narrowest relevant test:

```bash
cd backend
python -m pytest tests/ -q
```

For a focused test file or test, examples are:

```bash
python -m pytest tests/test_main.py -q
python -m pytest tests/test_main.py::test_health_check -q
```

Run these from the `backend/` directory. The frontend-render tests need Node.js on `PATH`; see [CONTRIBUTING.md](../CONTRIBUTING.md) for the marker and CI behavior. For a documentation-only change, also review the rendered Markdown and verify each new link and command against the repository. Report only checks you actually ran; do not claim a test passed just because it is documented here.

## 6. Commit and push

Review the final diff, then make one commit for this issue:

```bash
git diff --check
git status --short
git add docs/first-contributors.md README.md CONTRIBUTING.md
git commit -m "docs: add first-contributor walkthrough"
git push -u origin HEAD
```

If you changed different files, adjust the `git add` paths. Check that the commit contains only the intended change.

## 7. Open the pull request

Open a pull request from your fork's branch into `BistaDinesh03/critique:main`. You can use GitHub's **Compare & pull request** prompt after pushing, or open the [new pull request page](https://github.com/BistaDinesh03/critique/compare).

In the PR description:

- Explain the problem and the focused change.
- Link the issue with `Closes #ISSUE_NUMBER` when the change fully resolves it.
- List the checks you actually ran and their results.
- Keep the PR limited to this issue and respond constructively to review feedback.

The maintainers decide when to review and whether to merge; this guide does not promise a review timeline or acceptance.

## Before you submit

- [ ] I commented on the issue and checked for maintainer guidance.
- [ ] My branch is based on the latest upstream `main`.
- [ ] The diff contains only the intended changes.
- [ ] I checked the relevant links and ran the appropriate checks.
- [ ] The PR description accurately lists the checks I ran.
