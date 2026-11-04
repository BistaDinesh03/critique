# System Architecture Overview

This document provides a high-level overview of Critique's system architecture, technical design principles, and component interactions.

---

## 1. High-Level Architecture

Critique is built as a lightweight, zero-build web application designed to be simple to deploy, audit, and contribute to.

```
+--------------------------------------------------------------+
|                        Client Browser                        |
|   (Vanilla HTML5, CSS custom properties, vanilla JS modules)  |
+------------------------------+-------------------------------+
                               |  HTTP / REST JSON
                               v
+--------------------------------------------------------------+
|                      FastAPI Web Server                      |
|                                                              |
|  +------------------------+      +------------------------+  |
|  |     Static & HTML      |      |        API Tier        |  |
|  |      Route Shells      |      |   /api/projects, auth  |  |
|  +------------------------+      +------------------------+  |
|               |                              |               |
|               +--------------+---------------+               |
|                              v                               |
|                  +-----------------------+                   |
|                  |   Security & Auth     |                   |
|                  | - CSRF Double-Submit  |                   |
|                  | - GitHub OAuth 2.0    |                   |
|                  | - Magic Links (Resend)|                   |
|                  +-----------------------+                   |
|                              |                               |
|                              v                               |
|                  +-----------------------+                   |
|                  |  SQLAlchemy ORM Tier  |                   |
|                  +-----------------------+                   |
+------------------------------+-------------------------------+
                               |
                               v
               +-------------------------------+
               |      SQLite Database File     |
               |         (critique.db)         |
               +-------------------------------+
```

---

## 2. Component Breakdown

### Frontend (`frontend/` & `static/`)
- **Zero-Build Architecture:** All frontend pages (`index.html`, `discover.html`, `project_detail.html`, `my_projects.html`) are plain HTML files styled with vanilla CSS variables (`static/shared.css`).
- **No Node Toolchain Required for Runtime:** The application runs without Webpack, Vite, or npm build steps in production.
- **Client Scripting:** Standard JavaScript handles DOM rendering, asynchronous JSON calls to `/api/`, toast notifications, and event tracking (`static/ui.js`, `static/analytics.js`).

### Backend (`backend/app/`)
- **FastAPI Framework:** Implements ASGI endpoints, dependency injection, and automatic JSON validation.
- **Pydantic Validation (`schemas.py`):** Enforces strict validation on project creation, questions, and feedback responses.
- **Database & ORM (`database.py`, `models.py`):** Uses SQLAlchemy to map relational entities (`User`, `Project`, `Question`, `Response`, `EmailLoginToken`, `AnalyticsEvent`) to SQLite.

### Authentication & Security (`auth.py`, `csrf.py`, `email.py`)
- **GitHub OAuth:** Users can authenticate via standard OAuth authorization code flow.
- **Passwordless Magic Links:** Users can sign in with an email address. Tokens are hashed with SHA-256 before storage in SQLite and expire after 15 minutes.
- **CSRF Defense:** Double-submit cookie verification (`critique_csrf` cookie matched with `X-CSRF-Token` header) protects all mutating endpoints (`POST`, `DELETE`, `PUT`).

---

## 3. Data Model

| Model | Purpose |
|---|---|
| **User** | Represents registered makers and contributors (GitHub ID or verified email). |
| **Project** | Projects submitted for community feedback (title, description, URL, screenshot). |
| **Question** | The specific question the project author wants answered. |
| **Response** | Structured feedback entries answering the active question. |
| **EmailLoginToken** | Single-use cryptographically secure tokens for passwordless authentication. |
| **AnalyticsEvent** | Privacy-conscious, internal instrumentation events for funnel metrics. |

---

## 4. Testing Strategy (`backend/tests/`)
- **Pytest Suite:** All routes, models, authentication flows, and security constraints are verified with pytest.
- **In-Memory Fixtures:** Tests spin up ephemeral database sessions, ensuring isolation and fast execution.
- **Harness Integration:** Node-based headless DOM harness (`frontend_render_harness.js`) validates key frontend interactions where necessary.
