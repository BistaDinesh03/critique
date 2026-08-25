# Critique

**Ask one question. Get real answers.**

A lightweight, open-source platform for getting honest human feedback on your work. Built with simplicity in mind — no algorithms, no AI, no noise.

## Live Demo

**https://critique-qqz9.onrender.com**

## Why it exists

Getting honest feedback on side projects is hard. Social media rewards engagement, not honesty. Critique gives you a clean space to ask ONE specific question about your project and receive structured, human responses.

## Features

- **One question per project** — Focus on what matters
- **Structured feedback** — Clarity rating, would-you-use-it, and written suggestions
- **Simple discovery** — Browse projects asking for feedback
- **Results dashboard** — Clean percentage breakdowns
- **GitHub OAuth** — Sign in with your existing account
- **Privacy controls** — Written feedback visible only to project owner
- **Security** — CSRF protection, rate limiting, input validation
- **No algorithms** — Projects are listed chronologically
- **No AI** — Every response is from a real person

## Tech Stack

- **Frontend**: HTML, CSS, Vanilla JavaScript
- **Backend**: Python 3.11+, FastAPI
- **Database**: SQLite
- **Authentication**: GitHub OAuth
- **Testing**: pytest (44 tests)
- **Deployment**: Render

## Local Development

### Prerequisites

- Python 3.11+
- Git
- A GitHub account

### Setup

`powershell
# Clone the repository
git clone https://github.com/BistaDinesh03/critique.git
cd critique

# Install dependencies
python -m pip install -r backend/requirements.txt

# Create environment file
Copy-Item .env.example .env

# Edit .env with your values (see Environment Variables below)
Running the Application
powershell
cd backend
python -m uvicorn app.main:app --reload
Open http://127.0.0.1:8000 in your browser.

Running Tests
powershell
cd backend
python -m pytest tests/ -v
Production Deployment
The application is deployed on Render.

Render Configuration
Build Command: pip install -r backend/requirements.txt

Start Command: cd backend && uvicorn app.main:app --host 0.0.0.0 --port 

Environment: Python 3

Required Environment Variables
VariableRequiredDescription
GITHUB_CLIENT_IDYesGitHub OAuth App Client ID
GITHUB_CLIENT_SECRETYesGitHub OAuth App Client Secret
GITHUB_REDIRECT_URIYesOAuth callback URL (e.g., https://your-app.onrender.com/auth/callback)
SECRET_KEYYesRandom string for session signing
DATABASE_URLNoDefault: sqlite:///./critique.db
APP_ENVNoSet to production in production
APP_URLNoBase URL of the application
SESSION_COOKIE_SECURENoSet to true in production (HTTPS)
GitHub OAuth Setup
Go to GitHub Settings → Developer settings → OAuth Apps

Click New OAuth App

Fill in:

Application name: Critique

Homepage URL: Your application URL

Authorization callback URL: https://your-app.onrender.com/auth/callback

Click Register application

Copy the Client ID and generate a Client Secret

Put both values in your environment variables

Generate a secret key:

powershell
python -c "import secrets; print(secrets.token_hex(32))"
See docs/github-oauth-setup.md for detailed instructions.

Project Structure
text
critique/
├── backend/          # FastAPI application
│   ├── app/          # Python source code
│   │   ├── auth.py       # GitHub OAuth and sessions
│   │   ├── csrf.py       # CSRF protection
│   │   ├── database.py   # SQLite connection
│   │   ├── main.py       # App entry point
│   │   ├── models.py     # SQLAlchemy models
│   │   ├── rate_limit.py # In-memory rate limiting
│   │   ├── routes_*.py   # API endpoints
│   │   ├── schemas.py    # Pydantic validation
│   │   └── stats.py      # Feedback calculations
│   └── tests/        # 44 pytest tests
├── frontend/         # HTML pages (vanilla JS)
├── docs/             # Documentation
├── static/           # Static files
├── .env.example      # Environment template
├── render.yaml       # Render deployment config
└── README.md
Contributing
See CONTRIBUTING.md for how to contribute.

Security
See SECURITY.md for reporting vulnerabilities.

License
MIT — see LICENSE for details.
