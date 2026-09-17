<p align="center">
  <img src="docs/logo-readme.svg" alt="Critique" width="56" />
</p>

<h1 align="center">Critique</h1>

<p align="center">
  <strong>Ask one question. Get real answers.</strong><br>
  A focused feedback platform for builders.
</p>

<p align="center">
  <a href="https://critique.page">Live demo</a> ·
  <a href="https://github.com/BistaDinesh03/critique">GitHub</a> ·
  <a href="LICENSE">MIT License</a>
</p>

---

## At a glance

| | |
|---|---|
| Backend | FastAPI + SQLAlchemy 2.x |
| Database | PostgreSQL (production) / SQLite (development) |
| Frontend | Vanilla HTML/CSS/JS — no build step |
| Auth | GitHub OAuth |
| Tests | 78 (pytest) |
| License | MIT |

---

## What is Critique?

Most feedback requests are too broad:

> "What do you think of my project?"
> → "Looks good!"

Critique fixes this by asking for one focused question instead:

> "Would you understand what this does in 10 seconds?"

You submit a project, ask one specific question, and receive structured human feedback — clarity, would-use, and optional written suggestions.

No AI. No likes. No vanity metrics.

---

## How it works

1. **Share** — Add what you built.
2. **Ask** — One focused question.
3. **Get feedback** — Clarity and would-use scores, plus written answers.
4. **Improve** — Act on real signal.

---

## README feedback badge

Show your project's live response count in any README:

```markdown
[![Critique](https://critique.page/badge/PROJECT_ID.svg)](https://critique.page/project/PROJECT_ID)
```

Replace `PROJECT_ID` with your project ID. The badge renders live from the database and links to your project page.

---

## Key features

- **One focused question per project** — no generic "any thoughts?" posts
- **Structured feedback** — clarity (very clear / mostly clear / confusing) and would-use (yes / maybe / no)
- **Written suggestions** — optional free-text feedback
- **Privacy controls** — written feedback visible only to the project owner
- **GitHub OAuth** — sign in with an existing GitHub account
- **Dynamic badges** — embeddable SVG with live response count
- **Discover** — public feed of projects asking for feedback
- **My Projects** — manage submissions and view results
- **Deterministic ranking** — projects surfaced by need, freshness, and question quality

---

## Engineering

Critique is a small, focused FastAPI application built for clarity and low operational overhead.

**Stack**

- FastAPI + SQLAlchemy 2.x
- PostgreSQL (production) / SQLite (development)
- Vanilla HTML/CSS/JS on the frontend
- GitHub OAuth for authentication
- Render for deployment

**What is built in**

- CSRF protection on all state-changing requests (double-submit cookie)
- Session cookies with `HttpOnly`, `SameSite=Lax`, and `Secure` in production
- Input validation with Pydantic (length limits, URL scheme checks, enum patterns)
- HTML escaping of all user content in the frontend (XSS protection)
- Ownership checks on every mutation — determined server-side from the authenticated session
- Rate limiting on auth, project creation, feedback submission, deletion, and analytics
- Analytics events validated against a strict allowlist
- No third-party tracking scripts; no IP addresses stored (only SHA-256 hashes for duplicate detection)

**Tests**

```bash
cd backend && python -m pytest tests/ -v
```

78 tests covering API behavior, CSRF, rate limiting, IDOR/ownership, privacy, ranking, XSS, analytics validation, and SEO endpoints.

---

## Run locally

**Requirements:** Python 3.11+, Git

```bash
git clone https://github.com/BistaDinesh03/critique.git
cd critique
pip install -r backend/requirements.txt
cp .env.example .env
cd backend && uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000

GitHub OAuth setup: [docs/github-oauth-setup.md](docs/github-oauth-setup.md)

---

## Project structure

```text
backend/
  app/
    auth.py            GitHub OAuth + sessions
    csrf.py            CSRF protection
    database.py        Engine + migrations
    models.py          SQLAlchemy models
    ranking.py         Discover ranking
    rate_limit.py      In-memory rate limiting
    routes_*.py        API routes
    schemas.py         Pydantic validation
    routes_seo.py      sitemap.xml + robots.txt
  tests/               78 pytest tests
frontend/              HTML pages (vanilla JS)
static/                CSS, JS, logo, favicon
docs/                  Setup guides
render.yaml            Deployment config
```

---

## Contributing

Bug reports, ideas, and pull requests are welcome.

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines, and [SECURITY.md](SECURITY.md) for reporting vulnerabilities.

---

## License

MIT — see [LICENSE](LICENSE).
