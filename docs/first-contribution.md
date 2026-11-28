# Your First Contribution to Critique

Welcome! This guide walks you through making your first contribution to Critique, from finding an issue to opening a pull request.

## What is Critique?

Critique is an open-source platform where builders share their projects and receive honest, structured feedback from real people. Instead of vague "looks good" comments, Critique lets you ask one specific question about your project and collect real answers.

- **Website:** https://critique.page
- **Repository:** https://github.com/BistaDinesh03/critique
- **License:** MIT

## Finding an Issue

1. Browse the [`good first issue` label](https://github.com/BistaDinesh03/critique/labels/good%20first%20issue) or the [contributor opportunities page](contributor-opportunities.md).
2. Read the problem, acceptance criteria, and comments. Skip anything assigned, claimed in a comment, or attached to an open pull request.
3. Comment on the issue saying you would like to work on it. A maintainer will confirm availability.
4. Ask questions in the issue or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1). No question is too small.

### Good first issues to start with

These were open, unassigned, and unclaimed when last checked on 2026-11-28. Verify the live state before you start.

- [#901 — correct the feedback progress count](https://github.com/BistaDinesh03/critique/issues/901)
- [#903 — explain who sees written feedback](https://github.com/BistaDinesh03/critique/issues/903)

More beginner work is listed under the [`good first issue` label](https://github.com/BistaDinesh03/critique/labels/good%20first%20issue).

## Setting Up

### Prerequisites

- Python 3.11+
- Git
- Node.js (optional; frontend-render tests are skipped without it)

The canonical setup and fork workflow is in [contributing-start.md](contributing-start.md). For a quick local run, use `python scripts/quickstart.py` (`py scripts/quickstart.py` on Windows).

### Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/critique.git
cd critique
python -m venv .venv
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

# Windows cmd.exe
.venv\Scripts\activate.bat

pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
```

If PowerShell blocks `Activate.ps1`, run
`Set-ExecutionPolicy -Scope Process Bypass` for the current session and try again.

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
- Ask in [GitHub Discussions](https://github.com/BistaDinesh03/critique/discussions) or [issue #1](https://github.com/BistaDinesh03/critique/issues/1).
- Read [CONTRIBUTING.md](../CONTRIBUTING.md) for full guidelines.
- Read [SECURITY.md](../SECURITY.md) for vulnerability reporting.