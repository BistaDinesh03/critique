<p align="center">
  <div align="center">
  <img src="docs/logo-readme.svg" alt="Critique" width="56" />
</div>
</p>

<h1 align="center">Critique</h1>

<p align="center">
  <strong>Ask one question. Get real answers.</strong>
</p>

<p align="center">
  Critique is an open-source feedback platform for makers. Share what you've built, ask one focused question, and get structured feedback from real people.
</p>

<p align="center">
  <a href="https://critique-qqz9.onrender.com"><strong>Try Critique</strong></a>
  &nbsp;·&nbsp;
  <a href="https://critique-qqz9.onrender.com/discover">Discover Projects</a>
  &nbsp;·&nbsp;
  <a href="https://github.com/BistaDinesh03/critique">View Source</a>
  &nbsp;·&nbsp;
  <a href="CONTRIBUTING.md">Contribute</a>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
</p>

---

## Feedback

Built something similar? I'd love your honest opinion.

[![Critique feedback](https://critique-qqz9.onrender.com/badge/5.svg)](https://critique-qqz9.onrender.com/project/5)

---

## Early access — looking for 20 makers

Critique is currently in its early stage. We're looking for 20 makers and developers to try it with something they've built.

Have a side project, SaaS, open-source project, website, VS Code extension, mobile app, design, or student project? Submit it, ask one question you genuinely want answered, and get feedback from other people.

Then help another maker by reviewing a project in Discover.

> **Build something? Get a second opinion.**
>
> Submit your project → ask one focused question → get real feedback.

[Try Critique →](https://critique-qqz9.onrender.com/) · [Discover Projects →](https://critique-qqz9.onrender.com/discover)

---

## What is Critique?

Critique is built around a simple idea:

Instead of asking people:

> "What do you think of my project?"

ask:

> "Is it immediately clear what this tool does?"

Each project has one focused question so reviewers know exactly what to evaluate. This turns project feedback into something structured and actionable — useful for product feedback, developer feedback, and maker feedback alike.

## Why this exists

Generic feedback is often vague:

- "Looks great."
- "Cool project."
- "I like it."

These comments are nice, but they rarely help a maker decide what to change next. Critique is designed to turn feedback into clearer signals — clarity, intent to use, and written suggestions tied to one specific question.

## How it works

### 1. Share

Add something you've built.

### 2. Ask

Ask one specific question.

### 3. Learn

Get structured feedback from other people.

## Who is it for?

- Indie hackers validating a product
- Open-source maintainers improving a project
- Developers testing a new tool
- Designers testing an idea
- Students looking for outside feedback
- Makers preparing for a launch

## Features

### For makers

- Submit a project
- Ask one focused question
- Collect clarity feedback
- Collect would-use feedback
- Read written responses privately
- Manage your projects

### For reviewers

- Discover projects
- Answer focused questions
- Rate clarity
- Share whether you'd use the project
- Leave optional suggestions
- Respond once per project

## Why open source?

Critique is open source so developers can inspect how it works, report problems, improve the product, and help shape the platform.

[View Source](https://github.com/BistaDinesh03/critique) · [Contribute](CONTRIBUTING.md) · [Security](SECURITY.md)

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

## Tech stack

| Layer          | Technology                    |
| -------------- | ----------------------------- |
| Backend        | FastAPI, SQLAlchemy           |
| Database       | PostgreSQL (production), SQLite (development) |
| Frontend       | HTML, CSS, Vanilla JavaScript |
| Authentication | GitHub OAuth                  |
| Testing        | pytest                        |
| Deployment     | Render                        |

## Uptime Monitoring

The production instance exposes a lightweight health check:
GET https://critique-qqz9.onrender.com/health

text

Returns {"status":"ok"} with no database or authentication overhead.

To monitor uptime:

1. Create a free [UptimeRobot](https://uptimerobot.com) account.
2. Add a new monitor with type **HTTP(S)**.
3. Set the URL to https://critique-qqz9.onrender.com/health.
4. Set the monitoring interval to 5 minutes.

UptimeRobot will alert you if the service becomes unreachable.

## Quick start

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

## Environment variables

| Variable                | Required | Description                                      |
| ----------------------- | -------- | ------------------------------------------------ |
| `GITHUB_CLIENT_ID`      | Yes      | GitHub OAuth App Client ID                       |
| `GITHUB_CLIENT_SECRET`  | Yes      | GitHub OAuth App Client Secret                   |
| `GITHUB_REDIRECT_URI`   | Yes      | OAuth callback URL                               |
| `SECRET_KEY`            | Yes      | Random string for session signing                |
| `DATABASE_URL`          | No       | Default: `sqlite:///./critique.db`               |
| `APP_ENV`               | No       | `development` or `production`                    |
| `APP_URL`               | No       | Base URL of the application                      |
| `SESSION_COOKIE_SECURE` | No       | Set to `true` in production (HTTPS)              |

Never commit `.env` to the repository.

## GitHub OAuth setup

1. Go to [GitHub Settings → Developer settings → OAuth Apps](https://github.com/settings/developers)
2. Click **New OAuth App**
3. Set:
   - **Homepage URL**: `http://127.0.0.1:8000` (local) or `https://critique-qqz9.onrender.com` (production)
   - **Callback URL**: `http://127.0.0.1:8000/auth/callback` (local) or `https://critique-qqz9.onrender.com/auth/callback` (production)
4. Register and copy the Client ID and Client Secret

Full instructions: [docs/github-oauth-setup.md](docs/github-oauth-setup.md)

## Project structure

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

Contributions are welcome. You can help with:

- Bug reports
- Feature ideas
- UX improvements
- Documentation
- Security reports
- Pull requests

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## License

MIT — see [LICENSE](LICENSE).

---

## Try Critique

Have something you've built?

Ask one question.  
Get real answers.

[Try Critique →](https://critique-qqz9.onrender.com/) · [Discover Projects →](https://critique-qqz9.onrender.com/discover) · [View Source →](https://github.com/BistaDinesh03/critique)

If Critique is useful to you, consider giving the repository a star.


