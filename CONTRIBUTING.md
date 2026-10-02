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

Expected: **290 passed**. Install [Node.js](https://nodejs.org) first — the
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

## Communication

- Be kind and constructive
- Assume good intentions
- Focus on the work, not the person

## License

By contributing, you agree your work will be licensed under the MIT License.
