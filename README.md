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
  <a href="CONTRIBUTING.md">Contributing</a> ·
  <a href="LICENSE">MIT License</a>
</p>

---

## Why Critique

Most feedback requests are too broad:

> "What do you think of my project?"
> → "Looks good!"

Critique asks for one focused question instead:

> "Would you understand what this does in 10 seconds?"

You submit a project, ask one specific question, and get structured human
feedback — a clarity score, a would-use score, and optional written
suggestions. No AI. No likes. No vanity metrics.

## How it works

1. **Share** — Add what you built and what it does.
2. **Ask** — Pose one focused question about it.
3. **Get feedback** — Clarity and would-use scores, plus written answers.
4. **Improve** — Act on real signal.

## Features

- **One focused question per project** — no generic "any thoughts?" posts
- **Structured feedback** — clarity (very clear / mostly clear / confusing) and would-use (yes / maybe / no)
- **Written suggestions** — optional free text, visible only to the project owner
- **Discover** — public feed of projects asking for feedback, ranked deterministically by need, freshness, and question quality
- **My Projects** — manage submissions, view results, share when you choose to
- **Dynamic badge** — embeddable SVG showing a project's live response count
- **Sign-in options** — GitHub OAuth or a passwordless email magic link
- **SEO basics** — `robots.txt`, a dynamic `sitemap.xml`, and homepage social-preview metadata

### Add the badge to your README

```markdown
[![Critique](https://critique.page/badge/PROJECT_ID.svg)](https://critique.page/project/PROJECT_ID)
```

Replace `PROJECT_ID` with your project's ID (from its Critique URL). The count
renders live from the database and the badge links to your project page.

## Stack

| | |
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
    main.py            App setup, page routes, /health, cache middleware
    auth.py            GitHub OAuth, email magic links, sessions
    csrf.py            Double-submit-cookie CSRF protection
    config.py          Environment-based settings
    database.py        Engine, table creation, lightweight migrations
    models.py          SQLAlchemy models
    schemas.py         Pydantic request/response validation
    ranking.py         Deterministic Discover ranking
    rate_limit.py      In-memory per-endpoint rate limiting
    analytics.py       Event-name allowlist enforcement
    email.py           Magic-link email delivery (Resend)
    routes_projects.py CRUD + Discover feed
    routes_responses.py Feedback submission and listing
    routes_results.py  Aggregated results for owners
    stats.py           Aggregate feedback statistics
    routes_badge.py    /badge/{id}.svg
    routes_stats.py    /api/stats
    routes_analytics.py      /api/analytics/track
    routes_analytics_dashboard.py  Owner-only dashboard
    routes_seo.py      robots.txt + sitemap.xml
  tests/               pytest suite (API, security, and frontend render harness)
frontend/              HTML pages (vanilla JS)
static/                CSS, JS, logos, favicon
docs/                  Setup guides
render.yaml            Deployment config
```

Pages are served directly by FastAPI from `frontend/`; the browser talks to a
JSON API under `/api/*`. There is no frontend build step and no ORM layer
beyond SQLAlchemy.

## Run locally

**Requirements:** Python 3.11+, Git. Node.js (any recent version) is needed to
run the frontend-render tests; they are skipped if `node` is not on your PATH.

```bash
git clone https://github.com/BistaDinesh03/critique.git
cd critique
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
cd backend
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. SQLite tables are created automatically on
startup; no separate migration step is needed for development.

Authentication is optional for local browsing — sign-in is only required to
submit or manage projects:

- **GitHub OAuth and email magic links:** see
  [docs/github-oauth-setup.md](docs/github-oauth-setup.md) for both, including
  the `RESEND_API_KEY` / `EMAIL_FROM` values email login needs (below)

## Environment variables

Copy `.env.example` to `.env` and fill in what you need. All values are
placeholders — never commit real credentials (`.env` is gitignored).

| Variable | Purpose | Notes |
|---|---|---|
| `APP_ENV` | `development` or `production` | defaults to `development` |
| `APP_URL` | Public base URL | defaults to `http://127.0.0.1:8000` |
| `SECRET_KEY` | Signs session cookies | Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | Database connection string | Defaults to local SQLite; use PostgreSQL in production |
| `GITHUB_CLIENT_ID` | GitHub OAuth app client ID | Optional — enables GitHub login |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth app secret | Optional |
| `GITHUB_REDIRECT_URI` | OAuth callback URL | Defaults to `http://127.0.0.1:8000/auth/callback` |
| `SESSION_COOKIE_SECURE` | Set `true` behind HTTPS | defaults to `false` |
| `SESSION_COOKIE_MAX_AGE` | Session lifetime in seconds | Optional; defaults to 604800 (7 days) |
| `RESEND_API_KEY` | Resend API key for magic-link emails | Optional — enables email login |
| `EMAIL_FROM` | From address for magic links | Optional; verified in Resend |

## Database

Development uses SQLite (`critique.db`, gitignored). On startup the app calls
`init_db()`, which creates tables and applies lightweight, additive migrations
for both SQLite and PostgreSQL. Production uses PostgreSQL with `DATABASE_URL`
set in the hosting environment.

## Tests

```bash
cd backend
python -m pytest tests/ -q
```

Expected: **290 passed**. The suite covers API behavior, CSRF, rate limiting,
IDOR/ownership checks, privacy rules, ranking, XSS, analytics validation,
authentication flows, SEO endpoints, and frontend rendering (via a Node-based
DOM harness — these tests are skipped when Node.js is unavailable).

## API

JSON API overview: [docs/api.md](docs/api.md). Interactive docs are served at
`/docs` (Swagger UI) and `/redoc` when the app is running. Health check:
`GET /health`.

## Security & privacy

- CSRF protection (double-submit cookie) on all state-changing requests;
  sessions live in `HttpOnly`, `SameSite=Lax` cookies (`Secure` in
  production)
- Ownership of projects is verified server-side from the session on every
  mutation — never from client-supplied headers
- Rate limiting on auth, project creation, deletion, feedback submission,
  and analytics
- Analytics events validated against a strict server-side allowlist; no
  third-party tracking scripts
- No IP addresses are stored (only SHA-256 hashes for duplicate detection),
  and written feedback is visible only to the project owner

[SECURITY.md](SECURITY.md) lists the full behavior and explains how to
report a vulnerability.

## Deploy

Deployment is configured in `render.yaml` (Render web service + PostgreSQL).
Secrets — `DATABASE_URL`, `SECRET_KEY`, OAuth credentials, and email keys —
are set manually in the Render dashboard and are never stored in the
repository. See `render.yaml` for the full list of expected variables.

## Contributing

Bug reports, ideas, and pull requests are welcome. Read
[CONTRIBUTING.md](CONTRIBUTING.md) for guidelines, and
[SECURITY.md](SECURITY.md) for reporting vulnerabilities.

## License

MIT — see [LICENSE](LICENSE).
