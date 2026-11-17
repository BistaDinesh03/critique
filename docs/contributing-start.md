# Contributor Onboarding Guide

Welcome to Critique! This guide walks you through everything you need to find an issue, set up your local environment, run the test suite, and submit your first pull request.

---

## 1. Finding Your First Issue

Critique tags issues designed for newcomers:

- Look for issues with the [`good first issue`](https://github.com/BistaDinesh03/critique/labels/good%20first%20issue) and [`beginner`](https://github.com/BistaDinesh03/critique/labels/beginner) labels.
- Before starting work, leave a comment on the issue indicating you would like to tackle it.
- Maintainers use an automated assignment tool (`scripts/contributor.py assign`) to assign issues only after you comment, preventing multiple contributors from working on the same task simultaneously.

---

## 2. Local Setup

### Prerequisites
- Python 3.10+ (or 3.11+)
- Node.js 18+ (needed for frontend render testing)
- Git and GitHub CLI (`gh`)

### Fork & Clone
1. Fork [BistaDinesh03/critique](https://github.com/BistaDinesh03/critique) on GitHub.
2. Clone your fork locally:
   ```bash
   git clone https://github.com/<YOUR_USERNAME>/critique.git
   cd critique
   git remote add upstream https://github.com/BistaDinesh03/critique.git
   git fetch upstream
   ```

3. Set up a Python virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r backend/requirements.txt
   ```

---

## 3. Running the Test Suite

Before making any code modifications, verify your baseline environment:

```bash
cd backend
GITHUB_CLIENT_ID=ci-test-client-id python -m pytest tests/ -q
```

To run only frontend rendering tests:
```bash
python -m pytest tests/ -m frontend_render -q
```

To run a single test file:
```bash
python -m pytest tests/test_loading_ux.py -q
```

---

## 4. Making Changes & Committing

1. Create a descriptive feature branch:
   ```bash
   git checkout -b feat/my-new-feature
   ```
2. Keep changes focused and minimal. Follow the code formatting conventions in the repository.
3. Commit your changes with signed-off commits (`-s`):
   ```bash
   git commit -s -m "feat(module): brief description of change (closes #123)"
   ```

---

## 5. Submitting Your Pull Request

1. Push your branch to your fork:
   ```bash
   git push -u origin feat/my-new-feature
   ```
2. Open a Pull Request against `main` on `BistaDinesh03/critique`.
3. In the PR description, mention the issue it closes (`Closes #123`) and outline what you changed and how you verified it.
4. Ensure all CI checks pass. If maintainers request adjustments, update your branch and push!
