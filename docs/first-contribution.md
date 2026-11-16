# Your First Contribution to Critique

Welcome! This guide walks you through making your first contribution to Critique, from finding an issue to opening a pull request.

## What is Critique?

Critique is an open-source platform where builders share their projects and receive honest, structured feedback from real people. Instead of vague "looks good" comments, Critique lets you ask one specific question about your project and collect real answers.

- **Website:** https://critique.page
- **Repository:** https://github.com/BistaDinesh03/critique
- **License:** MIT

## Finding an Issue

1. Browse [open issues](https://github.com/BistaDinesh03/critique/issues) labeled [`good first issue`](https://github.com/BistaDinesh03/critique/labels/good%20first%20issue).
2. Read the issue carefully. Make sure you understand the problem and the acceptance criteria.
3. Comment on the issue saying you'd like to work on it. A maintainer will confirm availability.
4. If you have questions, ask in the issue or in [Discussion #741](https://github.com/BistaDinesh03/critique/discussions/741).

### Recommended Starting Issues

- [#77](https://github.com/BistaDinesh03/critique/issues/77) — Add `<noscript>` notices (HTML, beginner)
- [#683](https://github.com/BistaDinesh03/critique/issues/683) — Feedback quality guide (docs, beginner)
- [#688](https://github.com/BistaDinesh03/critique/issues/688) — RSS/Atom feed (backend, beginner)
- [#685](https://github.com/BistaDinesh03/critique/issues/685) — Clarity distribution visualization (frontend, beginner)
- [#720](https://github.com/BistaDinesh03/critique/issues/720) — Save draft capability (frontend, beginner)

## Setting Up

### Prerequisites

- Python 3.11+
- Git

### Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/critique.git
cd critique
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
```

### Run the backend

```bash
cd backend
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. Authentication providers are optional for local browsing.

### Run tests

```bash
cd backend
GITHUB_CLIENT_ID=ci-test-client-id python -m pytest tests/ -q
```

On Windows PowerShell:

```powershell
cd backend
$env:GITHUB_CLIENT_ID='ci-test-client-id'
python -m pytest tests/ -q
```

## Making Changes

1. Create a branch from `main`:
   ```bash
   git checkout -b fix/your-change-name
   ```
2. Make your changes.
3. Add or update tests.
4. Run the test suite.
5. Check for trailing whitespace:
   ```bash
   git diff --check
   ```

## Submitting a Pull Request

1. Push your branch to your fork:
   ```bash
   git push origin fix/your-change-name
   ```
2. Open a pull request against `main`.
3. Fill out the PR template.
4. Wait for review. Maintainers will provide feedback.

### What to include in your PR

- A clear description of what changed and why.
- Tests for new functionality.
- Updated documentation if needed.
- No secrets, credentials, or debug artifacts.

## Getting Help

- Comment on the issue you're working on.
- Ask in [Discussion #741](https://github.com/BistaDinesh03/critique/discussions/741).
- Read [CONTRIBUTING.md](../CONTRIBUTING.md) for full guidelines.
- Read [SECURITY.md](../SECURITY.md) for vulnerability reporting.