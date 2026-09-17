<p align="center">
  <img src="docs/logo-readme.svg" alt="Critique" width="56" />
</p>

<h1 align="center">Critique</h1>

<p align="center">
  <strong>Ask one question. Get real answers.</strong><br>
  A focused feedback platform for builders.
</p>

<p align="center">
  <a href="https://critique.page"><strong>Live demo</strong></a> ·
  <a href="https://github.com/BistaDinesh03/critique">GitHub</a> ·
  <a href="LICENSE">MIT License</a>
</p>

---

## What is Critique?

Most feedback requests are too broad:

> "What do you think of my project?"
> → "Looks good!"

Critique fixes this by forcing one focused question:

> "Would you understand what this does in 10 seconds?"

You submit a project, ask one specific question, and receive structured human feedback — clarity, would-use, and optional written suggestions. No AI, no likes, no vanity metrics.

---

## How it works

1. **Share** — Add what you built
2. **Ask** — One focused question
3. **Get feedback** — Clarity and would-use scores, plus written answers
4. **Improve** — Act on real signal

---

## Preview

<p align="center">
  <img src="static/og-image.png" alt="Critique — Ask one question. Get real answers." width="640" />
</p>

*(The image above is Critique's social preview card, not a UI screenshot.)*

---

## README feedback badge

Drop this into any project README to show how many responses your project has received:

```markdown
[![Critique](https://critique.page/badge/PROJECT_ID.svg)](https://critique.page/project/PROJECT_ID)
```

Replace `PROJECT_ID` with your project ID. The badge renders live from the database and links directly to your project page.

---

## Key features

- **One focused question** per project — no generic "any thoughts?" posts
- **Structured feedback** — clarity (very clear / mostly clear / confusing) and would-use (yes / maybe / no)
- **Written suggestions** — optional free-text feedback from reviewers
- **Privacy controls** — written feedback is visible only to the project owner
- **GitHub OAuth** — sign in with an existing GitHub account
- **Dynamic badges** — embeddable SVG that shows the live response count
- **Discover** — public feed of projects looking for feedback
- **My Projects** — manage your submissions and view results
- **Deterministic ranking** — projects are surfaced based on need, freshness, and question quality (no ML, no ads)

---

## Engineering

Critique is built as a small, focused FastAPI application.

| Area | Implementation |
|------|----------------|
| Backend | FastAPI + SQLAlchemy 2.x |
| Database | PostgreSQL (production) / SQLite (development) |
| Frontend | Vanilla HTML/CSS/JS — no build step |
| Auth | GitHub OAuth with signed session cookies |
| Deployment | Render |

**Security protections:**

- CSRF protection via double-submit cookie on all state-changing requests
- Session cookies are `HttpOnly`, `SameSite=Lax`, and `Secure` in production
- Input validation with Pydantic (`pattern`, `max_length`, URL scheme checks)
- HTML escaping of all user content in the frontend (XSS protection)
- Ownership checks on every mutation — server-side session, never client headers
- Rate limiting on auth, project creation, feedback submission, deletion, and analytics
- Analytics events validated against a strict allowlist (`page_view`, `discover_view`, `project_view`, `feedback_start`, `feedback_submit`, `project_submit`)
- No third-party tracking scripts, no IP addresses stored (only SHA-256 hashes for duplicate detection)

**Testing:**

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
static/                CSS, JS, logo, favicon, OG image
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
