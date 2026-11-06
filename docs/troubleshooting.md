# Local Development Troubleshooting

Common issues and solutions when setting up and developing Critique locally.

---

## 1. Virtual Environment & Dependencies

### `No module named 'fastapi'` or `pytest: command not found`
**Cause:** Your active shell does not have the project virtual environment enabled.

**Solution:**
Ensure you have created and activated the virtualenv:

```bash
# macOS / Linux:
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Windows (PowerShell):
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

---

## 2. Running Tests

### Frontend render tests skipped
**Symptom:** pytest reports multiple skipped tests in `test_frontend_render.py` or `test_auth_choice_ui.py`.

**Cause:** The frontend rendering harness uses Node.js to evaluate DOM and JavaScript execution, and Node.js is not installed or not on your `PATH`.

**Solution:**
Install [Node.js](https://nodejs.org/) (v18+ recommended) and verify with `node --version`. Once available, re-run pytest.

### `KeyError: 'client_id'` in `test_login_sends_state_to_github`
**Cause:** Without a `.env` file or environment variable, `settings.GITHUB_CLIENT_ID` defaults to an empty string, which `parse_qs` drops from query parameters.

**Solution:**
Run pytest with `GITHUB_CLIENT_ID` set:

```bash
# Bash:
GITHUB_CLIENT_ID=ci-test-client-id python -m pytest tests/ -q

# PowerShell:
$env:GITHUB_CLIENT_ID = "ci-test-client-id"
python -m pytest tests/ -q
```

---

## 3. Server Startup & Ports

### `ERROR: [Errno 48] Address already in use`
**Cause:** Another process (e.g. an existing uvicorn instance) is already listening on port 8000.

**Solution:**
Find and terminate the process using port 8000:

```bash
# macOS / Linux:
lsof -i :8000
kill -9 <PID>

# Windows (PowerShell):
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process
```

Alternatively, start uvicorn on an alternate port:

```bash
uvicorn app.main:app --reload --port 8080
```

---

## 4. GitHub OAuth Authentication

### `redirect_uri_mismatch` from GitHub
**Cause:** GitHub OAuth requires an exact match between the callback URL configured in the GitHub OAuth App and `GITHUB_REDIRECT_URI`.

**Solution:**
In your GitHub OAuth App settings, make sure:
- **Authorization callback URL** is set to `http://127.0.0.1:8000/auth/callback`
- Note that `http://localhost:8000` is treated by GitHub as a different domain than `http://127.0.0.1:8000`. Use `127.0.0.1` consistently.

Refer to [docs/github-oauth-setup.md](github-oauth-setup.md) for step-by-step OAuth configuration.

---

## 5. Database Issues

### Database schema out of sync
**Cause:** Schema migrations are additive and automatic on app startup, but local SQLite files can become dirty during development.

**Solution:**
Critique creates SQLite files in `backend/critique.db` (app) and `backend/critique_test.db` (tests). If you need a clean slate:

```bash
cd backend
rm -f critique.db critique_test.db
# Restart the server or re-run pytest to re-initialize tables cleanly
```
