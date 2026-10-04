<p align="center">
  <img src="docs/logo-readme.svg" alt="Critique" width="56" />
</p>

<h1 align="center">Critique</h1>

<p align="center">
  <strong>Ask one question. Get real answers.</strong><br>
  An open-source feedback platform for people who build things.
</p>

<p align="center">
  <a href="https://critique.page">Live demo</a> ·
  <a href="docs/api.md">API</a> ·
  <a href="CONTRIBUTING.md">Contributing</a> ·
  <a href="LICENSE">MIT License</a>
</p>

---

## Overview

Most feedback requests are too broad to act on:

> "What do you think of my project?"
> → "Looks good!"

Critique swaps the vague ask for one focused question — for example:

> "Would you understand what this does in 10 seconds?"

You submit a project, ask that single question, and get structured feedback
from real people: a clarity rating, a would-use rating, and optional written
suggestions that only you, the project owner, can read. No AI, no likes, no
popularity ranking — just answers you can act on.

## How it works

1. **Share** — Add what you built and what it does.
2. **Ask** — Pose one focused question about it.
3. **Get feedback** — Clarity and would-use ratings, plus written answers.
4. **Improve** — Act on real signal.

## Features

- **One focused question per project** — every project asks a single, specific question, so answers stay comparable and actionable
- **Structured ratings** — clarity (very clear / mostly clear / confusing) and would-use (yes / maybe / no) for every response
- **Private written suggestions** — optional free text, visible only to the project owner
- **Discover** — a public feed ranked deterministically by need, freshness, question quality, and more
- **My Projects** — manage your submissions and revisit results whenever you like
- **Results dashboard** — response totals, distribution bars, and written feedback for each project
- **Sharing** — post to X or Reddit, or copy the link, right after submitting or from My Projects
- **Dynamic badge** — a live SVG response count for your README (below)
- **Sign-in options** — GitHub OAuth or a passwordless email magic link
- **SEO support** — `robots.txt`, a dynamic `sitemap.xml`, and homepage social-preview metadata

## Feedback badge

Every project has an embeddable SVG badge with its live response count:

- **Badge endpoint:** `GET /badge/{project_id}.svg` — `https://critique.page/badge/PROJECT_ID.svg`
- **Links to:** the project page — `https://critique.page/project/PROJECT_ID`

```markdown
[![Critique](https://critique.page/badge/PROJECT_ID.svg)](https://critique.page/project/PROJECT_ID)
```

Replace `PROJECT_ID` with your project's ID — the number in its Critique URL.
The count is rendered from the database on each request, and 1000+ displays
as `1k+`.

## Stack

| Layer | Choice |
|---|---|
| Backend | FastAPI + SQLAlchemy 2.x (Python 3.11+) |
| Database | PostgreSQL in production, SQLite for development |
| Frontend | Vanilla HTML/CSS/JS — no build step |
| Auth | GitHub OAuth and email magic links (via Resend) |
| Tests | pytest (290 tests; frontend-render tests use Node.js) |
| Hosting | Render (`render.yaml`) |
| License | MIT |

## Architecture

```text
backend/
  app/
    main.py                   App setup, page routes, /health, cache headers
    auth.py                   GitHub OAuth, email magic links, sessions
    csrf.py                   Double-submit-cookie CSRF protection
    config.py                 Environment-based settings
    database.py               Engine, table creation, additive migrations
    models.py                 SQLAlchemy models
    schemas.py                Pydantic request/response validation
    ranking.py                Deterministic Discover ranking
    rate_limit.py             In-memory per-endpoint rate limiting
    analytics.py              Event storage and visitor cookie
    email.py                  Magic-link email delivery (Resend)
    routes_projects.py        Project CRUD and Discover feed
    routes_responses.py       Feedback submission and listing
    routes_results.py         Aggregated results for owners
    stats.py                  Aggregate feedback statistics
    routes_badge.py           GET /badge/{id}.svg
    routes_stats.py           GET /api/stats
    routes_analytics.py       Event allowlist, /api/analytics/track
    routes_analytics_dashboard.py  Owner analytics endpoint
    routes_seo.py             robots.txt and sitemap.xml
  tests/                      pytest suite (API, security, frontend render)
frontend/                     HTML pages (vanilla JS, no build step)
static/                       CSS, JS, logos, favicon
docs/                         Setup guides and API reference
render.yaml                   Deployment config
```

Pages are served directly by FastAPI from `frontend/`; the browser talks to a
JSON API under `/api/*`. There is no frontend build step and no ORM layer
beyond SQLAlchemy.

## Getting started

**Requirements:** Python 3.11+, Git. Node.js (any recent version) is only
needed for the frontend-render tests — they are skipped when `node` is not on
your PATH.

```bash
git clone https://github.com/BistaDinesh03/critique.git
cd critique
python -m venv .venv
```

Activate the virtual environment:

```bash
# macOS / Linux
source .venv/bin/activate
```

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install dependencies, create your environment file, and start the server:

```bash
pip install -r requirements.txt
cp .env.example .env    # Windows: copy .env.example .env
cd backend
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. SQLite tables are created automatically on
startup — no separate migration step.

Authentication is optional for local browsing; sign-in is only required to
submit or manage projects. Setup for GitHub OAuth and email magic links
(including the `RESEND_API_KEY` and `EMAIL_FROM` values email login needs) is
in [docs/github-oauth-setup.md](docs/github-oauth-setup.md).

## Environment variables

Copy `.env.example` to `.env` and set what you need. `.env` is gitignored —
never commit real credentials.

| Variable | Purpose | Default / notes |
|---|---|---|
| `APP_ENV` | `development` or `production` | `development` |
| `APP_URL` | Public base URL | `http://127.0.0.1:8000` |
| `SECRET_KEY` | Signs session tokens and OAuth state | No default — generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | Database connection string | `sqlite:///./critique.db`; use PostgreSQL in production |
| `GITHUB_CLIENT_ID` | GitHub OAuth app client ID | Optional — enables GitHub login |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth app secret | Optional |
| `GITHUB_REDIRECT_URI` | OAuth callback URL | `http://127.0.0.1:8000/auth/callback` |
| `SESSION_COOKIE_SECURE` | Set `true` behind HTTPS | `false` |
| `SESSION_COOKIE_MAX_AGE` | Session lifetime in seconds | Optional; `604800` (7 days) |
| `RESEND_API_KEY` | Resend API key for magic-link emails | Optional — enables email login |
| `EMAIL_FROM` | From address for magic links | Optional; verified in Resend |

## Database

Development uses SQLite (`critique.db`, gitignored) — the default when
`DATABASE_URL` is unset. On startup the app runs `init_db()`, which creates
tables and applies lightweight, additive migrations for both SQLite and
PostgreSQL, so there is no separate migration step. Production uses
PostgreSQL, with `DATABASE_URL` provided by the hosting environment and kept
out of the repository.

## Testing

```bash
cd backend
python -m pytest tests/ -q
```

Expected: **290 passed, 2 warnings** (both warnings come from third-party
packages). The suite covers API behavior, CSRF, rate limiting, ownership
checks, privacy rules, ranking, XSS, analytics validation, authentication
flows, SEO endpoints, and frontend rendering through a Node-based DOM
harness (skipped when Node.js is unavailable).

## API

JSON API reference: [docs/api.md](docs/api.md). While the app is running,
interactive docs are served at `/docs` (Swagger UI) and `/redoc`, and a
health check is available at `GET /health`.

## Security & privacy

- CSRF protection (double-submit cookie with an `X-CSRF-Token` header) on all
  state-changing requests; sessions live in an `HttpOnly`, `SameSite=Lax`
  cookie, with `Secure` when `SESSION_COOKIE_SECURE=true` (Render sets this)
- Project ownership is verified server-side from the session on every
  mutation — never from client-supplied headers
- Rate limiting on auth and email login, project creation and deletion,
  feedback submission, and analytics
- Pydantic validation on every request body; frontend output is escaped and
  covered by XSS regression tests
- Analytics events validated against a strict server-side allowlist; no
  third-party tracking scripts
- No IP addresses are stored (only SHA-256 hashes for duplicate detection),
  and written feedback is visible only to the project owner

[SECURITY.md](SECURITY.md) lists the full behavior and explains how to
report a vulnerability.

## Deployment

Deployment is configured in `render.yaml`: a Render web service with a
PostgreSQL database. `APP_ENV=production` and `SESSION_COOKIE_SECURE=true`
are set there; secrets — `DATABASE_URL`, `SECRET_KEY`, OAuth credentials, and
email keys — are marked `sync: false` and entered manually in the Render
dashboard, never stored in the repository. See `render.yaml` for the full
list of expected variables.

## Contributing

Bug reports, ideas, and pull requests are welcome — thank you! Read
[CONTRIBUTING.md](CONTRIBUTING.md) for guidelines, and
[SECURITY.md](SECURITY.md) for reporting vulnerabilities.

## License

MIT — see [LICENSE](LICENSE).
