# Critique

**Ask one question. Get real answers.**

A lightweight, open-source platform for getting honest human feedback on your work. Built with simplicity in mind — no algorithms, no AI, no noise.

## Why it exists

Getting honest feedback on side projects is hard. Social media rewards engagement, not honesty. Critique gives you a clean space to ask ONE specific question about your project and receive structured, human responses.

## Features

- **One question per project** — Focus on what matters
- **Structured feedback** — Clarity rating, would-you-use-it, and written suggestions
- **Simple discovery** — Browse projects asking for feedback
- **Results dashboard** — Clean percentage breakdowns
- **GitHub OAuth** — Sign in with your existing account
- **No algorithms** — Projects are listed chronologically
- **No AI** — Every response is from a real person

## Tech Stack

- **Frontend**: HTML, CSS, Vanilla JavaScript
- **Backend**: Python 3.11+, FastAPI
- **Database**: SQLite
- **Authentication**: GitHub OAuth
- **Testing**: pytest

## Local Development

### Prerequisites

- Python 3.11+
- Git
- A GitHub account

### Setup

`powershell
# Clone the repository
git clone https://github.com/yourusername/critique.git
cd critique

# Install dependencies
python -m pip install -r requirements.txt

# Create environment file
Copy-Item .env.example .env

# Edit .env with your values
# See "GitHub OAuth Setup" below
Environment Variables
VariableDescriptionRequired
GITHUB_CLIENT_IDGitHub OAuth App Client IDYes
GITHUB_CLIENT_SECRETGitHub OAuth App Client SecretYes
GITHUB_REDIRECT_URIOAuth callback URLYes
SECRET_KEYRandom string for session signingYes
DATABASE_URLSQLite database URLNo (default: sqlite:///./critique.db)
APP_ENVEnvironment nameNo (default: development)
APP_URLBase URLNo (default: http://127.0.0.1:8000)
Running the Application
powershell
cd backend
python -m uvicorn app.main:app --reload
Open http://127.0.0.1:8000 in your browser.

Running Tests
powershell
cd backend
python -m pytest tests/ -v
GitHub OAuth Setup
Go to GitHub Settings → Developer settings → OAuth Apps

Click New OAuth App

Fill in:

Application name: Critique

Homepage URL: http://127.0.0.1:8000

Authorization callback URL: http://127.0.0.1:8000/auth/callback

Click Register application

Copy the Client ID and generate a Client Secret

Put both values in your .env file

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
│   │   ├── database.py   # SQLite connection
│   │   ├── main.py       # App entry point
│   │   ├── models.py     # SQLAlchemy models
│   │   ├── routes_*.py   # API endpoints
│   │   ├── schemas.py    # Pydantic validation
│   │   └── stats.py      # Feedback calculations
│   └── tests/        # pytest test suite
├── frontend/         # HTML pages (vanilla JS)
├── docs/             # Documentation
├── static/           # Static files
├── .env.example      # Environment template
└── README.md
Contributing
See CONTRIBUTING.md for how to contribute.

License
MIT — see LICENSE for details.
