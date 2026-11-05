# Critique API Reference

All endpoints served by the Critique application. The HTML pages are rendered
by FastAPI from `frontend/`; everything below returns JSON unless noted.

- **Base URL (production):** `https://critique.page`
- **Local development:** `http://127.0.0.1:8000`
- **Interactive docs:** `/docs` (Swagger UI) and `/redoc` while the app runs

## Conventions

- **Authentication** is cookie-based: a session cookie is set when you sign
  in. Endpoints marked *Optional* work signed-out with reduced data; endpoints
  marked *Required* return `401` without a session.
- **CSRF:** state-changing mutation requests (`POST /api/projects/`, `DELETE /api/projects/{id}`, `POST .../responses`, `POST /auth/email/start`) must include the header `X-CSRF-Token` whose value matches the `critique_csrf` cookie (set with `httponly=False` so JavaScript can read it). Missing or mismatched tokens return `403 {"detail": "Invalid or missing CSRF token"}`. Lightweight analytics telemetry (`POST /api/analytics/track`) is exempt from CSRF tokens to support browser beacons and unauthenticated event tracking; it is guarded by IP rate limiting (`analytics`) and an allowlist of valid event names.
- **Rate limiting** is per client IP and endpoint; exceeding a limit returns
  `429 {"detail": "Too many requests. Please slow down."}`.
- **Validation errors** return `422` (FastAPI/Pydantic) or `400` with a
  `detail` field. Unknown server errors return
  `500 {"detail": "Internal server error"}` without stack traces.
- **404 responses** depend on the request path and `Accept` header. For
  non-`/api/` paths, an `Accept` header containing `text/html` receives the
  branded HTML page with status `404`. JSON clients and the default `*/*`
  receive JSON instead. Every `/api/*` path returns its JSON `{"detail": ...}`
  error even with `Accept: text/html`, including missing API resources.
  Other error statuses (`400`, `401`, `403`, `409`, `422`, `429`, `500`)
  retain their JSON responses for all clients.

### Rate limits

The limits below are per client IP. Magic-link requests also have a separate
per-email cooldown described after the table.

| Key | Limit |
|---|---|
| `auth` (OAuth login/callback) | 10 requests / 60 s |
| `email_login_start` | 3 requests / 15 min |
| `email_login_verify` | 10 requests / 60 s |
| `project_create` | 5 requests / 5 min |
| `project_delete` | 20 requests / 5 min |
| `response_submit` | 10 requests / 5 min |
| `analytics` (track) | 60 requests / 60 s |

**Per-email cooldown:** a repeat `/auth/email/start` request for the same
normalized email address within 60 seconds intentionally returns `{"ok": true}`
without sending another email. This is separate from the IP-based
`email_login_start` limit; that limit still applies and can return `429`.
The cooldown is tracked in process memory, not as a durable delivery limit.
Reporting send failures is separately tracked in [#81](https://github.com/BistaDinesh03/critique/issues/81).

## Authentication — `/auth`

| Method | Path | Auth | CSRF | Notes |
|---|---|---|---|---|
| GET | `/auth/login` | — | — | Starts GitHub OAuth; rate-limited (`auth`). Redirects to GitHub. |
| GET | `/auth/callback` | — | — | OAuth callback; validates single-use state; rate-limited (`auth`). With a valid state and `code`, sets the session and redirects to `return_to` or `/`. When GitHub reports cancellation via `error` (such as `error=access_denied`) or when `code` is omitted, consumes the state, clears `critique_return_to`, and redirects to `/?auth=cancelled` (where the homepage displays a neutral banner). A missing, expired, forged, or replayed state returns `400 {"detail": "Invalid or missing OAuth state"}`. |
| GET | `/auth/logout` | — | — | Clears session and CSRF cookies; redirects to `/`. |
| GET | `/auth/check` | Required | — | `{"authenticated": true, "username": "...", "id": <int>}` or `401`. |
| GET | `/auth/csrf-token` | — | — | `{"csrf_token": "..."}`; also sets the `critique_csrf` cookie if absent. |
| POST | `/auth/email/start` | — | Required | Body `{"email": "...", "return_to"?: "/path"}`. Requests a magic link (15-minute, single-use). Always `{"ok": true}` regardless of whether the address exists or sending succeeded. Within the intentional 60-second per-email cooldown, repeat requests return that same success without sending another email. Separately rate-limited per IP (`email_login_start`). |
| GET | `/auth/email/verify?token=...` | — | — | Consumes the token atomically, sets the session, redirects. Missing, empty, invalid, expired, or used tokens redirect to `/?error=email_link`. Rate-limited (`email_login_verify`). |

`return_to` is validated against an allowlist of safe local paths; anything
else is ignored.

## Projects — `/api/projects`

| Method | Path | Auth | CSRF | Rate limit | Notes |
|---|---|---|---|---|---|
| POST | `/api/projects/` | Required | Required | `project_create` | Creates a project and its first question. Returns `201` with `{project, question}`. |
| GET | `/api/projects/` | — | — | — | Discover feed. Query: `page` (≥1, default 1), `page_size` (1–50, default 10). Deterministically ranked. |
| GET | `/api/projects/my/list` | Required | — | — | All projects owned by the session user. |
| GET | `/api/projects/{project_id}` | — | — | — | One project with its active question; `404` if not found. |
| DELETE | `/api/projects/{project_id}` | Required | Required | `project_delete` | Owner-only. `204` on success; `404` if the project does not exist; `403` if you are signed in but not the owner. |

#### Paginated Project Feed Response

`GET /api/projects/` returns a JSON envelope:

```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "page_size": 10,
  "total_pages": 5
}
```

| Field | Type | Description |
|---|---|---|
| `items` | array | List of project objects for the current page, deterministically ranked. |
| `total` | integer | Global count: total number of matching visible projects across all pages. |
| `page` | integer | Current 1-based page number. |
| `page_size` | integer | Maximum number of items per page. |
| `total_pages` | integer | Total available pages (`ceil(total / page_size)`). |

## Feedback — `/api/projects/{project_id}/responses`

| Method | Path | Auth | CSRF | Rate limit | Notes |
|---|---|---|---|---|---|
| POST | `.../responses` | Required | Required | `response_submit` | Body: `clarity` (enum), `would_use` (enum), optional `suggestion` text. Returns `201`. One response per user per question — a second submission returns `409`. The client IP is stored only as a keyed HMAC-SHA-256 digest, stable while `SECRET_KEY` remains unchanged; raw IP addresses are not stored. |
| GET | `.../responses` | Optional | — | — | Owner receives written `suggestion` text; everyone else receives scores only (`id`, `clarity`, `would_use`, `question_id`, `created_at`). `404` if the project does not exist. |

## Results — `/api/projects/{project_id}/results`

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `.../results` | Optional | `{project_id, project_title, question_text, stats, responses, is_owner}`. `stats` (clarity/would-use aggregates) is public; `responses` (including written suggestions) is populated only for the owner — determined server-side from the session. `404` for unknown projects. |
| GET | `.../results.csv` | Required (Owner) | Returns feedback as `text/csv; charset=utf-8` attachment (`Content-Disposition: attachment; filename="project-{id}-feedback.csv"`). Columns: `created_at,clarity,would_use,suggestion`. Cells starting with formula triggers (`=`, `+`, `-`, `@`, `\t`, `\r`) are escaped with a leading single quote to neutralize spreadsheet injection. `401` for anonymous, `403` for non-owners, `404` for unknown projects. |

## Badge — `/badge`

| Method | Path | Notes |
|---|---|---|
| GET | `/badge/{project_id}.svg` | SVG image showing the live response count (exact below 1,000, then `1.2k` / `12k` / `1.2m` style abbreviations). `Cache-Control: no-cache`. `404` for unknown projects. |

## Stats — `/api`

| Method | Path | Notes |
|---|---|---|
| GET | `/api/stats` | Public aggregate site statistics (`total_builders`, `total_projects`, `total_questions`, `total_responses`, and recent builders). |

## Analytics — `/api/analytics`

| Method | Path | Auth | Rate limit | Notes |
|---|---|---|---|---|
| POST | `/api/analytics/track?event_name=...&project_id=...` | Optional | `analytics` | Parameters are passed in the query string (no request body). `event_name` must be on the server-side allowlist or the request is rejected with `400 {"detail": "Invalid event name"}`. Returns `{"ok": bool}` and sets/refreshes the visitor cookie. Stores only the
  event name, an anonymous visitor ID, optional user/project IDs, and a
  timestamp — no IP addresses, free-form text, or third-party scripts. |
| GET | `/api/analytics/dashboard` | Required (owner allowlist) | — | Aggregated totals for the site owner; `403` for other signed-in users. |

## SEO — `/`

| Method | Path | Notes |
|---|---|---|
| GET | `/robots.txt` | Allows public crawling; disallows `/my-projects`, `/api/`, `/auth/`, `/health`. |
| GET | `/sitemap.xml` | Homepage, `/discover`, and every project page (dynamic). |

Every absolute URL in both endpoints (the `Sitemap:` line in `/robots.txt`
and each `<loc>` in `/sitemap.xml`) is built from `settings.APP_URL`, read per
request. Surrounding whitespace and any trailing slash are stripped
(`https://critique.page/` becomes `https://critique.page`); if `APP_URL` is
unset or blank, the origin falls back to `http://127.0.0.1:8000`. An absolute
origin is required because crawlers cannot resolve a root-relative `<loc>`,
and the `Sitemap:` line is specified as an absolute URL. Self-hosted
deployments should set `APP_URL` to their public origin so crawlers are
pointed at the right site.

## Pages and misc

| Method | Path | Notes |
|---|---|---|
| GET | `/` `/discover` `/my-projects` `/project/{id}` `/project/{id}/results` | HTML pages. A CSRF cookie is issued with each page response. `/?auth=cancelled` renders a neutral notice banner and cleans up the URL query flag. |
| GET | `/google8ffd0ae5f931d1e6.html` | Google Search Console site-verification file. |
| GET | `/health` | `{"status": "ok"}` — uptime probe. |
| GET | `/docs`, `/redoc` | FastAPI-generated API documentation. |
| GET | `/static/*` | CSS/JS use `Cache-Control: no-cache` (revalidation); images use `Cache-Control: public, max-age=86400`. |

## Error responses

| Status | Shape | When |
|---|---|---|
| 400 | `{"detail": "Invalid event name"}` | Analytics allowlist rejection. |
| 400 | `{"detail": "Invalid or missing OAuth state"}` | Missing, expired, forged, or replayed state in `GET /auth/callback`. |
| 401 | `{"detail": "Not authenticated"}` | Auth required, no session. |
| 403 | `{"detail": "Invalid or missing CSRF token"}` | Missing/mismatched `X-CSRF-Token`. |
| 403 | `{"detail": "Not authorized"}` | Signed in but not allowed (e.g., dashboard). |
| 403 | `{"detail": "You cannot delete this project"}` | Delete attempted by a non-owner. |
| 404 | HTML page or `{"detail": "Not Found"}` (resource-specific `detail` where applicable) | Non-`/api/` paths return branded HTML when `Accept` contains `text/html`; JSON clients and default `*/*` get JSON. `/api/*` always gets JSON, including missing resources (for example `{"detail": "Project not found"}`). |
| 409 | `{"detail": "You have already responded to this question"}` | Second response to the same question. |
| 422 | `{"detail": [...]}` | Pydantic validation failure. |
| 429 | `{"detail": "Too many requests. Please slow down."}` | Rate limit exceeded. |
| 500 | `{"detail": "Internal server error"}` | Unhandled error; never leaks stack traces. |

## Usage Examples

### 1. cURL Examples

#### Browse the Discover Feed (Public)
```bash
# Fetch the first page of ranked projects (JSON)
curl -s -H "Accept: application/json" "http://127.0.0.1:8000/api/projects/?page=1&page_size=10"
```

#### Fetch Project Details
```bash
# Retrieve a project and its active question
curl -s -H "Accept: application/json" "http://127.0.0.1:8000/api/projects/1"
```

#### Fetch Project Results & Feedback Stats
```bash
# Public aggregate feedback statistics
curl -s -H "Accept: application/json" "http://127.0.0.1:8000/api/projects/1/results"
```

#### Check Global Application Stats
```bash
# Site-wide project and response counters
curl -s -H "Accept: application/json" "http://127.0.0.1:8000/api/stats"
```

#### Authenticated Feedback Submission
State-changing endpoints (`POST`, `DELETE`) require an active session cookie and matching `X-CSRF-Token` header:
```bash
# 1. Fetch CSRF token and store session cookies
curl -s -c cookies.txt "http://127.0.0.1:8000/auth/csrf-token"

# 2. Extract CSRF token value from cookies
CSRF_TOKEN=$(grep critique_csrf cookies.txt | awk '{print $7}')

# 3. Submit feedback with session cookies and CSRF header
curl -s -b cookies.txt -X POST "http://127.0.0.1:8000/api/projects/1/responses" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -d '{
    "clarity": "very_clear",
    "would_use": "yes",
    "suggestion": "Great landing page! Would love to see an interactive demo video."
  }'
```

---

### 2. Python Examples

#### Public Client with `urllib` / Standard Library
```python
import json
import urllib.request

BASE_URL = "http://127.0.0.1:8000"

def get_discover_feed(page=1, page_size=10):
    url = f"{BASE_URL}/api/projects/?page={page}&page_size={page_size}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

def get_project_stats(project_id):
    url = f"{BASE_URL}/api/projects/{project_id}/results"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

if __name__ == "__main__":
    feed = get_discover_feed()
    print(f"Discovered {len(feed)} projects.")
    if feed:
        first_id = feed[0]["id"]
        stats = get_project_stats(first_id)
        print(f"Stats for project {first_id}:", stats.get("stats"))
```

#### Client using `requests` (with Session & CSRF)
```python
import requests

BASE_URL = "http://127.0.0.1:8000"
session = requests.Session()

# 1. Initialize session and obtain CSRF cookie
csrf_resp = session.get(f"{BASE_URL}/auth/csrf-token")
csrf_token = csrf_resp.json().get("csrf_token")
session.headers.update({
    "X-CSRF-Token": csrf_token,
    "Accept": "application/json",
})

# 2. Query discover feed
projects = session.get(f"{BASE_URL}/api/projects/").json()
print("First project:", projects[0]["title"] if projects else "No projects")

# 3. Submit feedback (when authenticated)
def submit_feedback(project_id, clarity, would_use, suggestion=""):
    payload = {
        "clarity": clarity,
        "would_use": would_use,
        "suggestion": suggestion,
    }
    response = session.post(
        f"{BASE_URL}/api/projects/{project_id}/responses",
        json=payload,
    )
    return response.status_code, response.json()
```
