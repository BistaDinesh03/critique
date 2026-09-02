<p align="center">
  <img src="docs/logo-readme.svg" alt="Critique" width="48" />
</p>

<h1 align="center">Critique</h1>

<p align="center">
  <strong>Stop asking "What do you think?"</strong><br>
  Ask one question people can actually answer.
</p>

<p align="center">
  <a href="https://critique-qqz9.onrender.com"><strong>Try Critique</strong></a>
  &nbsp;·&nbsp;
  <a href="https://github.com/BistaDinesh03/critique">Source</a>
  &nbsp;·&nbsp;
  <a href="CONTRIBUTING.md">Contribute</a>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="MIT License"></a>
</p>

---

Generic feedback is useless.

> "What do you think of my project?"  
> "Looks good."

Critique forces a better question:

> "Would you understand what this does in 10 seconds?"

**One specific question → real human answers → clear signal to improve.**

No AI. No likes. No vanity metrics.

## How it works

1. **Share** — Add what you built  
2. **Ask** — One focused question  
3. **Get feedback** — Clarity, would-use, and written answers  
4. **Improve** — Act on real signal

## Live badge for your README

[![Critique](https://critique-qqz9.onrender.com/badge/11.svg)](https://critique-qqz9.onrender.com/project/11)

```markdown
[![Critique](https://critique-qqz9.onrender.com/badge/PROJECT_ID.svg)](https://critique-qqz9.onrender.com/project/PROJECT_ID)
```

Shows feedback count. Updates automatically. Links straight to your project.

## Run locally

```bash
git clone https://github.com/BistaDinesh03/critique.git
cd critique
pip install -r backend/requirements.txt
cp .env.example .env
cd backend && uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000  
GitHub OAuth setup → [docs/github-oauth-setup.md](docs/github-oauth-setup.md)

## Stack

FastAPI · SQLAlchemy · PostgreSQL / SQLite · Vanilla JS · GitHub OAuth · Render

## Contribute

Bug reports, ideas, and PRs welcome.  
See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## License

MIT
