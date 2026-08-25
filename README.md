<p align="center">
  <img src="static/logo.svg" alt="Critique" width="56" />
</p>

<h1 align="center">Critique</h1>

<p align="center">
  <strong>Ask one question. Get real answers.</strong>
</p>

<p align="center">
  An open-source platform where makers share what they've built,<br>
  ask one focused question, and get structured feedback from real people.
</p>

<p align="center">
  <strong><a href="https://critique-qqz9.onrender.com">Try Critique</a></strong>
  &nbsp;·&nbsp;
  <a href="https://github.com/BistaDinesh03/critique">View Source</a>
  &nbsp;·&nbsp;
  <a href="CONTRIBUTING.md">Contribute</a>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://github.com/BistaDinesh03/critique/tags"><img src="https://img.shields.io/badge/Release-v0.3.0-green.svg" alt="Release"></a>
</p>

---

## Why Critique?

Getting useful feedback on something you've built is hard. Most platforms reward engagement and reach, not honest answers.

Critique focuses on one thing: helping makers get useful answers to specific questions.

## How It Works

1. **Share** — Add something you've built.
2. **Ask** — Ask the one question you genuinely want answered.
3. **Learn** — Get structured feedback from real people.

## Why One Question?

Most feedback requests are too broad: *"What do you think of my project?"*

Critique intentionally focuses each project around one specific question, for example:

> "Is it immediately clear what this tool does?"

This makes feedback easier to give and more useful to receive.

## Who It's For

- Indie hackers validating a product idea
- Open-source maintainers improving their projects
- Developers looking for honest UX feedback
- Designers testing whether a concept is clear
- Students learning from real user responses
- Makers of any kind who want actionable input

## Features

### For Makers

- Submit a project with title, description, and link
- Ask one focused question
- View clarity and would-use results
- Read private written feedback (visible only to you)
- Manage and delete projects from My Projects

### For Reviewers

- Discover projects chronologically
- Rate clarity (Very clear / Mostly clear / Confusing)
- Say whether you'd use it (Yes / Maybe / No)
- Leave optional written suggestions
- Respond once per project

## Security

Critique includes:

- GitHub OAuth authentication
- CSRF protection
- Rate limiting
- Input validation
- XSS protection
- Ownership checks
- Privacy controls for written feedback
- Secure session handling

See [SECURITY.md](SECURITY.md).

## Tech Stack

| Layer          | Technology                                      |
|----------------|-------------------------------------------------|
| Backend        | FastAPI, SQLAlchemy                             |
| Database       | PostgreSQL (production), SQLite (development)   |
| Frontend       | HTML, CSS, Vanilla JavaScript                   |
| Authentication | GitHub OAuth                                    |
| Testing        | pytest (44 tests)                               |
| Deployment     | Render                                          |

## Quick Start

### Requirements

- Python 3
- Git

### Clone

```powershell
git clone https://github.com/BistaDinesh03/critique.git
cd critique
```

### Install

```powershell
python -m pip install -r backend/requirements.txt
```

### Configure

```powershell
Copy-Item .env.example .env
```

Edit `.env` with your GitHub OAuth credentials and a secret key.

Generate a secret key:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

### Run

```powershell
cd backend
python -m uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000)

### Test

```powershell
cd backend
python -m pytest tests/ -v
```

## Environment Variables

| Variable               | Required | Description                                      |
|------------------------|----------|--------------------------------------------------|
| `GITHUB_CLIENT_ID`     | Yes      | GitHub OAuth App Client ID                       |
| `GITHUB_CLIENT_SECRET` | Yes      | GitHub OAuth App Client Secret                   |
| `GITHUB_REDIRECT_URI`  | Yes      | OAuth callback URL                               |
| `SECRET_KEY`           | Yes      | Random string for session signing                |
| `DATABASE_URL`         | Yes      | SQLite (dev) or PostgreSQL (production)          |
| `APP_ENV`              | No       | `development` or `production`                    |
| `APP_URL`              | No       | Base URL of the application                      |
| `SESSION_COOKIE_SECURE`| No       | `true` in production (HTTPS)                     |

Never commit `.env` to the repository.

## GitHub OAuth Setup

1. Go to [GitHub Settings → Developer settings → OAuth Apps](https://github.com/settings/developers)
2. Click **New OAuth App**
3. Set:
   - **Homepage URL**: `http://127.0.0.1:8000` (local) or your production URL
   - **Callback URL**: `http://127.0.0.1:8000/auth/callback` (local) or your production callback
4. Register and copy the Client ID and Client Secret

Full instructions: [docs/github-oauth-setup.md](docs/github-oauth-setup.md)

## Project Structure

```
backend/          # FastAPI application
  app/            # Python source code
  tests/          # pytest tests
frontend/         # HTML pages (vanilla JS)
static/           # CSS, logo, favicon
docs/             # Setup guides
render.yaml       # Render deployment config
```

## Contributing

Found a bug? Have a UX idea? Want to improve the code or documentation?

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).

---

<p align="center">
  <sub>If Critique is useful to you, consider giving the repository a star.</sub>
</p>
