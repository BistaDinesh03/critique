<p align="center">
  <img src="static/logo.svg" alt="Critique" width="48" />
</p>

# Critique

**Ask one question. Get real answers.**

Critique is an open-source platform where makers share what they've built, ask one focused question, and receive structured feedback from real people.

---

**[Live Demo](https://critique-qqz9.onrender.com)** &nbsp;|&nbsp; **[GitHub](https://github.com/BistaDinesh03/critique)** &nbsp;|&nbsp; **[Contributing](CONTRIBUTING.md)**

---

## How It Works

1. **Share** — Add your project with a title, description, and link.
2. **Ask** — Ask the one specific question you genuinely want answered.
3. **Learn** — Get structured feedback from real people.

## Features

### For Makers
- Submit a project
- Ask one focused question
- View aggregate results (clarity and would-use percentages)
- Read private written feedback (visible only to you)
- Manage and delete projects from My Projects

### For Reviewers
- Discover projects chronologically
- Rate clarity (Very clear / Mostly clear / Confusing)
- Share whether you'd use it (Yes / Maybe / No)
- Leave optional written suggestions
- One response per user per project

## Built With Care

- GitHub OAuth authentication
- CSRF protection
- Rate limiting
- Input validation
- XSS protection
- Ownership checks
- Privacy controls for written feedback

See [SECURITY.md](SECURITY.md).

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, SQLAlchemy |
| Database | SQLite |
| Frontend | HTML, CSS, Vanilla JavaScript |
| Authentication | GitHub OAuth |
| Testing | pytest (44 tests) |
| Deployment | Render |

## Getting Started

### Requirements

- Python 3
- Git

### Clone

\\\ash
git clone https://github.com/BistaDinesh03/critique.git
cd critique
\\\

### Install

\\\ash
python -m pip install -r backend/requirements.txt
\\\

### Configure

\\\ash
Copy-Item .env.example .env
\\\

Edit .env with your GitHub OAuth credentials and a secret key.

### Run

\\\ash
cd backend
python -m uvicorn app.main:app --reload
\\\

Open http://127.0.0.1:8000

### Test

\\\ash
cd backend
python -m pytest tests/ -v
\\\

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| GITHUB_CLIENT_ID | Yes | GitHub OAuth App Client ID |
| GITHUB_CLIENT_SECRET | Yes | GitHub OAuth App Client Secret |
| GITHUB_REDIRECT_URI | Yes | OAuth callback URL |
| SECRET_KEY | Yes | Random string for session signing |
| DATABASE_URL | No | Default: sqlite:///./critique.db |
| APP_ENV | No | development or production |
| APP_URL | No | Base URL of the application |
| SESSION_COOKIE_SECURE | No | 	rue in production (HTTPS) |

## GitHub OAuth Setup

1. Go to [GitHub Settings > Developer settings > OAuth Apps](https://github.com/settings/developers)
2. Click **New OAuth App**
3. Set:
   - **Homepage URL**: http://127.0.0.1:8000 (local) or your production URL
   - **Callback URL**: http://127.0.0.1:8000/auth/callback (local) or your production callback
4. Register and copy the Client ID and Client Secret

Full instructions: [docs/github-oauth-setup.md](docs/github-oauth-setup.md)

Generate a secret key:

\\\ash
python -c "import secrets; print(secrets.token_hex(32))"
\\\

## Project Structure

\\\
backend/          # FastAPI application
  app/            # Python source code
  tests/          # 44 pytest tests
frontend/         # HTML pages (vanilla JS)
static/           # CSS, logo, favicon
docs/             # Setup guides
render.yaml       # Render deployment config
\\\

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
