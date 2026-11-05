# Local Development Troubleshooting Guide

This guide covers common issues encountered when setting up, developing, or running tests for Critique locally.

---

## 1. Python Environment & Dependencies

### `ModuleNotFoundError: No module named 'fastapi'` (or other dependencies)

**Cause**: Python is running outside the virtual environment.

**Solution**:
1. Ensure your virtual environment is created and activated:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Verify the active Python interpreter points inside `.venv`:
   ```bash
   which python3
   ```

---

## 2. Environment Variables & Configuration

### `RuntimeError: CRITIQUE_SECRET_KEY is required`

**Cause**: Critique requires a secret key for session signing and CSRF tokens.

**Solution**:
Copy `.env.example` to `.env` in the repository root:
```bash
cp .env.example .env
```
Ensure `CRITIQUE_SECRET_KEY` is set to a secure string (minimum 32 characters for production, any test string for local dev):
```env
CRITIQUE_SECRET_KEY=local-dev-secret-key-must-be-long-enough
```

### GitHub OAuth Sign-In Fails Locally (`400 Bad Request` or redirect mismatch)

**Cause**: GitHub OAuth callback URL is not registered or credentials are missing.

**Solution**:
1. When developing locally without OAuth, use email magic link authentication.
2. If testing GitHub OAuth, set up a GitHub OAuth App with:
   - Homepage URL: `http://localhost:8000`
   - Authorization callback URL: `http://localhost:8000/auth/github/callback`
3. Update `.env` with:
   ```env
   GITHUB_CLIENT_ID=your_client_id
   GITHUB_CLIENT_SECRET=your_client_secret
   ```
See [docs/github-oauth-setup.md](github-oauth-setup.md) for full instructions.

---

## 3. SQLite Database Issues

### `sqlite3.OperationalError: database is locked`

**Cause**: An active process, background worker, or unclosed connection has locked the SQLite file.

**Solution**:
1. Stop any running local server processes (`uvicorn`).
2. Remove the temporary test database if it was left in an inconsistent state:
   ```bash
   rm -f test.db critique_test.db
   ```
3. For local development, Critique uses an SQLite file configured via `CRITIQUE_DB_PATH` (defaults to `./critique.db`).

### Schema Out of Sync or Missing Tables

**Cause**: The database schema was updated in a recent pull request.

**Solution**:
Critique creates tables on startup in `backend/app/database.py`. If schema changes cause issues with your existing local database:
```bash
rm -f critique.db
# Restart the server to re-initialize clean tables
uvicorn backend.app.main:app --reload
```

---

## 4. Frontend & Render Testing

### `Node.js missing` or `frontend_render_harness.js` errors in tests

**Cause**: Certain UI render tests invoke `node backend/tests/frontend_render_harness.js` to simulate DOM rendering.

**Solution**:
1. Ensure Node.js (v18+) is installed on your system:
   ```bash
   node --version
   ```
2. If you are only modifying backend routes or docs, you can run isolated backend tests:
   ```bash
   pytest backend/tests/test_api.py
   ```

---

## 5. Port Conflicts

### `OSError: [Errno 48] Address already in use: 8000`

**Cause**: Another application or an existing uvicorn instance is already using port 8000.

**Solution**:
Find and terminate the process using port 8000:
```bash
lsof -ti :8000 | xargs kill -9
```
Or start uvicorn on an alternative port:
```bash
uvicorn backend.app.main:app --port 8080 --reload
```

---

## 6. Running the Test Suite

### Tests Fail Due to Stale State

**Solution**:
Run pytest cleanly with clean cache:
```bash
pytest backend/tests/ -o cache_dir=/tmp/.pytest_cache
```
To run link validation specifically:
```bash
pytest backend/tests/test_markdown_links.py
```

---

## Still having trouble?

If you encounter an issue not covered here:
- Search existing [closed issues and pull requests](https://github.com/BistaDinesh03/critique/issues?q=is%3Aissue)
- Ask in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)
- Report a bug using our issue templates.
