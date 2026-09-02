<p align="center">
  <img src="docs/logo-readme.svg" alt="Critique" width="56" />
</p>

<h1 align="center">Critique</h1>

<p align="center">
  <strong>Get feedback that actually helps you improve your project.</strong><br>
  One focused question. Real human answers. No fluff.
</p>

<p align="center">
  <a href="https://critique-qqz9.onrender.com">
    <img src="https://img.shields.io/badge/Try%20Critique-Free-brightgreen?style=for-the-badge" alt="Try Critique">
  </a>
  &nbsp;
  <a href="https://github.com/BistaDinesh03/critique">
    <img src="https://img.shields.io/badge/GitHub-Source-black?style=for-the-badge" alt="Source">
  </a>
  &nbsp;
  <a href="CONTRIBUTING.md">
    <img src="https://img.shields.io/badge/Contribute-Welcome-blue?style=for-the-badge" alt="Contribute">
  </a>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="MIT License"></a>
</p>

---

### The problem with most feedback

> "What do you think of my project?"  
> → "Looks good!" or silence.

That’s useless.

**Critique forces a better question:**

> "Would you understand what this does in 10 seconds?"  
> "Would you actually use this?"  
> "What’s the most confusing part?"

You get clear, actionable signal instead of polite noise.

**One specific question → real human answers → clear signal to improve.**

No AI. No likes. No vanity metrics.

---

### How it works

1. **Share** — Add what you built  
2. **Ask** — One focused question  
3. **Get feedback** — Clarity score, would-use score, and written answers  
4. **Improve** — Act on real signal

---

### Live badge for your README

Drop this into any project README and start collecting feedback automatically:

[![Critique](https://critique-qqz9.onrender.com/badge/11.svg)](https://critique-qqz9.onrender.com/project/11)

```markdown
[![Critique](https://critique-qqz9.onrender.com/badge/PROJECT_ID.svg)](https://critique-qqz9.onrender.com/project/PROJECT_ID)
```

The badge shows the number of responses, updates automatically, and links straight to your project page.  
This is the easiest way to get continuous feedback from people who already care about your work.

---

### Who is this for?

- Indie hackers & solo founders shipping side projects  
- Open-source maintainers who want real signal  
- Students and builders tired of “looks good” comments  
- Anyone who wants feedback that actually helps them improve

---

### Try it in 30 seconds

1. Go to **[critique-qqz9.onrender.com](https://critique-qqz9.onrender.com)**  
2. Sign in with GitHub  
3. Post your project + one specific question  
4. Share the link (or add the badge to your README)

That’s it. Real people start answering.

---

### Run locally

```bash
git clone https://github.com/BistaDinesh03/critique.git
cd critique
pip install -r backend/requirements.txt
cp .env.example .env
cd backend && uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000  

GitHub OAuth setup → [docs/github-oauth-setup.md](docs/github-oauth-setup.md)

---

### Stack

FastAPI · SQLAlchemy · PostgreSQL / SQLite · Vanilla JS · GitHub OAuth · Render

---

### Contribute

Bug reports, ideas, and PRs are very welcome.  
See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

---

### License

MIT
