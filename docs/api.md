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
- **CSRF:** every state-changing request (`POST`, `DELETE`) must include the
  header `X-CSRF-Token` whose value matches the `critique_csrf` cookie (set
  with `httponly=False` so JavaScript can read it). Missing or mismatched
  tokens return `403 {"detail": "Invalid or missing CSRF token"}`.
- **Rate limiting** is per client IP and endpoint; exceeding a limit returns
  `429 {"detail": "Too many requests. Please slow down."}`.
- **Validation errors** return `422` (FastAPI/Pydantic) or `400` with a
  `detail` field. Unknown server errors return
  `500 {"detail": "Internal server error"}` without stack traces.

### Rate limits

| Key | Limit |
|---|---|
| `auth` (OAuth login/callback) | 10 requests / 60 s |
| `email_login_start` | 3 requests / 15 min |
| `email_login_verify` | 10 requests / 60 s |
| `project_create` | 5 requests / 5 min |
| `project_delete` | 20 requests / 5 min |
| `response_submit` | 10 requests / 5 min |
| `analytics` (track) | 60 requests / 60 s |

## Authentication — `/auth`

| Method | Path | Auth | CSRF | Notes |
|---|---|---|---|---|
| GET | `/auth/login` | — | — | Starts GitHub OAuth; rate-limited (`auth`). Redirects to GitHub. |
| GET | `/auth/callback` | — | — | OAuth callback; validates state; rate-limited. Redirects on success/failure. |
| GET | `/auth/logout` | — | — | Clears session and CSRF cookies; redirects to `/`. |
| GET | `/auth/check` | Required | — | `{"authenticated": true, "username": "..."}` or `401`. |
| GET | `/auth/csrf-token` | — | — | `{"csrf_token": "..."}`; also sets the `critique_csrf` cookie if absent. |
| POST | `/auth/email/start` | — | Required | Body `{"email": "...", "return_to"?: "/path"}`. Requests a magic link (15-minute, single-use). Always `{"ok": true}` regardless of whether the address exists or sending succeeded. Rate-limited (`email_login_start`). |
| GET | `/auth/email/verify?token=...` | — | — | Consumes the token atomically, sets the session, redirects. Invalid/expired/used tokens redirect to `/?error=email_link`. Rate-limited (`email_login_verify`). |

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

## Feedback — `/api/projects/{project_id}/responses`

| Method | Path | Auth | CSRF | Rate limit | Notes |
|---|---|---|---|---|---|
| POST | `.../responses` | Required | Required | `response_submit` | Body: `clarity` (enum), `would_use` (enum), optional `suggestion` text. Returns `201`. One response per user per question — a second submission returns `409`. The client IP is stored only as a SHA-256 hash. |
| GET | `.../responses` | Optional | — | — | Owner receives written `suggestion` text; everyone else receives scores only (`id`, `clarity`, `would_use`, `question_id`, `created_at`). `404` if the project does not exist. |

## Results — `/api/projects/{project_id}/results`

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `.../results` | Optional | `{project_id, project_title, question_text, stats, responses, is_owner}`. `stats` (clarity/would-use aggregates) is public; `responses` (including written suggestions) is populated only for the owner — determined server-side from the session. `404` for unknown projects. |

## Badge — `/badge`

| Method | Path | Notes |
|---|---|---|
| GET | `/badge/{project_id}.svg` | SVG image showing the live response count (`1k+` formatting at 1000+). `Cache-Control: no-cache`. `404` for unknown projects. |

## Stats — `/api`

| Method | Path | Notes |
|---|---|---|
| GET | `/api/stats` | Public aggregate site statistics. |

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

## Pages and misc

| Method | Path | Notes |
|---|---|---|
| GET | `/` `/discover` `/my-projects` `/project/{id}` `/project/{id}/results` | HTML pages. A CSRF cookie is issued with each page response. |
| GET | `/health` | `{"status": "ok"}` — uptime probe. |
| GET | `/docs`, `/redoc` | FastAPI-generated API documentation. |
| GET | `/static/*` | CSS/JS/images; served with `Cache-Control: public, max-age=86400`. |

## Error responses

| Status | Shape | When |
|---|---|---|
| 400 | `{"detail": "Invalid event name"}` | Analytics allowlist rejection. |
| 401 | `{"detail": "Not authenticated"}` | Auth required, no session. |
| 403 | `{"detail": "Invalid or missing CSRF token"}` | Missing/mismatched `X-CSRF-Token`. |
| 403 | `{"detail": "Not authorized"}` | Signed in but not allowed (e.g., dashboard). |
| 403 | `{"detail": "You cannot delete this project"}` | Delete attempted by a non-owner. |
| 404 | `{"detail": "Not Found"}` | Unknown route or resource. |
| 409 | `{"detail": "You have already responded to this question"}` | Second response to the same question. |
| 422 | `{"detail": [...]}` | Pydantic validation failure. |
| 429 | `{"detail": "Too many requests. Please slow down."}` | Rate limit exceeded. |
| 500 | `{"detail": "Internal server error"}` | Unhandled error; never leaks stack traces. |
