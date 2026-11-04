# Architecture Overview

This document provides a high-level overview of Critique's system architecture, design principles, and technical foundations.

---

## 1. System Philosophy

Critique is designed around three core principles:
1. **Minimal Dependencies:** Built with modern Python (FastAPI, SQLAlchemy, Pydantic) on the backend and lightweight, standard-compliant vanilla JavaScript and CSS on the frontend. No build step or heavy client-side framework is required.
2. **Speed & Reliability:** Fast page loads via server-served HTML shell templates with progressive client-side hydration for dynamic data.
3. **Security by Default:** Cookie-based session tokens, CSRF protection on every state-changing route, IP rate limiting, strict input validation, and defensive XSS escaping.

---

## 2. Component Diagram

```
+-----------------------------------------------------------+
|                        Browser                            |
|  - HTML Shells (frontend/*.html)                          |
|  - Shared CSS & Design Tokens (static/shared.css)         |
|  - Client Components & Auth Choice (static/ui.js)         |
|  - Lightweight First-Party Telemetry (static/analytics.js)|
+-----------------------------+-----------------------------+
                              | HTTPS / JSON / Cookies
                              v
+-----------------------------------------------------------+
|                     FastAPI Backend                       |
|  - main.py (Lifespan, CacheControl, Security Headers)     |
|  - app/auth.py (GitHub OAuth + Passwordless Email Auth)   |
|  - app/routes_projects.py (Discover Feed, CRUD, Ranking)  |
|  - app/routes_responses.py & routes_results.py (Feedback) |
|  - app/routes_stats.py (Social Proof & In-Memory Caching) |
|  - app/routes_seo.py (robots.txt, sitemap.xml, feed.xml)  |
|  - app/csrf.py (Double-submit Cookie Protection)          |
|  - app/rate_limit.py (In-memory IP Bucket Limiter)        |
+-----------------------------+-----------------------------+
                              | SQLAlchemy ORM
                              v
+-----------------------------------------------------------+
|                     Database Layer                        |
|  - SQLite (Local development: critique.db)                |
|  - PostgreSQL (Production via DATABASE_URL)               |
|  - Additive migrations via init_db()                      |
+-----------------------------------------------------------+
```

---

## 3. Frontend Architecture

The frontend lives in `frontend/` and `static/`:
- **HTML Templates (`frontend/`):**
  - `index.html`: Landing page, project submission form, and community stats.
  - `discover.html`: Paginated project feed with ranking, search, and responsive cards.
  - `project_detail.html`: Individual project view and structured 3-part feedback form.
  - `my_projects.html`: Authenticated creator dashboard to manage and share projects.
- **Design System (`static/shared.css`):**
  - Semantic CSS variables for colors, typography, spacing, shadows, and transitions.
  - Built-in dark color scheme support under `@media (prefers-color-scheme: dark)`.
  - Accessible focus outlines and reduced motion media queries.
- **Client Helpers (`static/ui.js` & `static/analytics.js`):**
  - `CritiqueUI`: Auth modal/drawer, toasts with accessible live regions, confirmation dialogs.
  - `CritiqueShare`: Clipboard copy affordance and native Web Share API bridge.
  - `CritiqueAnalytics`: Privacy-first, first-party event tracker with no third-party scripts.

---

## 4. Backend & API Layer

The backend is built with FastAPI and organized into modular routers under `backend/app/`:
- **`app/main.py`:** Application entry point, router mounts, static files mounting, lifespan shutdown cleanup, and `CacheControlMiddleware` providing baseline security headers (`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, and HSTS in production).
- **`app/auth.py`:** Two passwordless sign-in methods:
  - **GitHub OAuth:** State CSRF cookie validation, token exchange, and user provisioning.
  - **Magic-link Email:** Resend API integration with signed, short-lived tokens.
- **`app/routes_projects.py`:** Project creation, paginated feeds, and ranking algorithms balancing freshness and engagement.
- **`app/routes_responses.py` & `app/routes_results.py`:** Submitting and reviewing feedback. Written suggestions remain strictly private to the project owner.
- **`app/routes_stats.py`:** Public aggregate builder metrics with in-memory TTL caching to minimize database query overhead.
- **`app/csrf.py`:** Generates and validates CSRF tokens matching the `critique_csrf` cookie against the `X-CSRF-Token` request header.

---

## 5. Data Model & Persistence

The database layer uses SQLAlchemy models in `backend/app/models.py`:
- `User`: GitHub or email account with unique identifier, username, and optional avatar URL.
- `Project`: Submitted project containing title, description, link, screenshot URL, owner ID, and creation timestamp.
- `Question`: Core question asked by the builder for their project.
- `Response`: Feedback response storing clarity, would-use ratings, and optional written suggestion.
- `EmailLoginToken`: Hashed verification tokens for magic-link authentication with 15-minute expiry.
- `AnalyticsEvent`: Privacy-respecting audit trail for pageviews, shares, and funnel stages.

---

## 6. Testing Strategy

The test suite in `backend/tests/` provides comprehensive coverage:
- **API & Unit Tests:** FastAPI `TestClient` exercising routes, schemas, rate limits, and edge cases.
- **Security & Contract Tests:** Verifying cookie attributes (`HttpOnly`, `SameSite`, `Secure`), CSRF defenses, and authentication boundaries.
- **DOM Rendering Harness (`frontend_render_harness.js`):** Node.js-based virtual DOM harness that executes the real client-side JavaScript on raw HTML templates to assert DOM manipulation, event dispatch, and accessibility attributes.
