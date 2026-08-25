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
  <strong><a href="https://critique-qqz9.onrender.com">Try Critique →</a></strong>
  &nbsp;·&nbsp;
  <a href="https://github.com/BistaDinesh03/critique">View Source</a>
  &nbsp;·&nbsp;
  <a href="CONTRIBUTING.md">Contribute</a>
</p>

<p align="center">
  <a href="https://github.com/BistaDinesh03/critique/blob/main/LICENSE"><img src="https://img.shields.io/github/license/BistaDinesh03/critique" alt="License: MIT"></a>
</p>

---

## How It Works

1. **Share** — Add your project.
2. **Ask** — Ask one focused question.
3. **Learn** — Get structured feedback from real people.

## Features

### For Makers

- Submit a project
- Ask one focused question
- View clarity and would-use results
- Read private written feedback
- Manage and delete projects

### For Reviewers

- Discover projects
- Rate clarity
- Say whether you'd use the project
- Leave optional suggestions
- Respond once per project

## Built With Care

- GitHub OAuth
- CSRF protection
- Rate limiting
- Input validation
- XSS protection
- Ownership checks
- Privacy controls

See [SECURITY.md](SECURITY.md).

## Tech Stack

| Layer          | Technology                    |
|----------------|-------------------------------|
| Backend        | FastAPI, SQLAlchemy           |
| Database       | SQLite                        |
| Frontend       | HTML, CSS, Vanilla JavaScript |
| Authentication | GitHub OAuth                  |
| Testing        | pytest                        |
| Deployment     | Render                        |

## Getting Started

### Requirements

- Python 3
- Git

### Clone

```bash
git clone https://github.com/BistaDinesh03/critique.git
cd critique
```

### Install

```bash
python -m pip install -r backend/requirements.txt
```

### Configure

```bash
cp .env.example .env
```

Edit `.env` with your GitHub OAuth credentials and a secret key.

Generate a secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Run

```bash
cd backend
python -m uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

### Test

```bash
cd backend
python -m pytest tests/ -v
```

## Environment Variables

| Variable                | Required | Description                        |
|-------------------------|----------|------------------------------------|
| `GITHUB_CLIENT_ID`      | Yes      | GitHub OAuth App Client ID         |
| `GITHUB_CLIENT_SECRET`  | Yes      | GitHub OAuth App Client Secret     |
| `GITHUB_REDIRECT_URI`   | Yes      | OAuth callback URL                 |
| `SECRET_KEY`            | Yes      | Random string for session signing  |
| `DATABASE_URL`          | No       | Default: `sqlite:///./critique.db` |
| `APP_ENV`               | No       | `development` or `production`      |
| `APP_URL`               | No       | Base URL of the application        |
| `SESSION_COOKIE_SECURE` | No       | `true` in production (HTTPS)       |

## GitHub OAuth Setup

1. Go to [GitHub Settings → Developer settings → OAuth Apps](https://github.com/settings/developers).
2. Click **New OAuth App**.
3. Set:
   - **Homepage URL**: `http://127.0.0.1:8000` (local) or your production URL
   - **Callback URL**: `http://127.0.0.1:8000/auth/callback` (local) or your production callback
4. Register and copy the Client ID and Client Secret.

Full instructions: [docs/github-oauth-setup.md](docs/github-oauth-setup.md).

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

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
