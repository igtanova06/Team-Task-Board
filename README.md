# Team Task Board (Kanban)

![Team Task Board](Logo/screen.png)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Framework](https://img.shields.io/badge/Framework-Flask%203.0+-green.svg)](#)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](#)
[![Database](https://img.shields.io/badge/Database-SQL%20Server%20%7C%20SQLite-red.svg)](#)
[![Tests](https://img.shields.io/badge/Tests-107%20passed-brightgreen.svg)](#)
[![Security](https://img.shields.io/badge/Security-Bleach%20XSS%20%7C%20OCC%20%7C%20CSRF-blueviolet.svg)](#)

A modern, full-stack collaborative Kanban web application built with **Flask**, **SQLAlchemy ORM**, **Bootstrap 5**, and **Vanilla JavaScript (Fetch API / AJAX)**. 

Designed for high-productivity agile teams, Team Task Board combines intuitive visual workflow tracking with enterprise-grade engineering: **Role-Based Access Control (RBAC)**, **Optimistic Concurrency Control (OCC)**, **Dual Authentication (Session Cookies + Stateless JWT)**, and multi-layered **Application Security**.

---

## Table of Contents

- [Key Features](#key-features)
- [Architecture Overview](#architecture-overview)
- [Role-Based Access Control (RBAC)](#role-based-access-control-rbac)
- [Pre-configured Demo Accounts](#pre-configured-demo-accounts)
- [Engineering & Security Highlights](#engineering--security-highlights)
  - [Optimistic Concurrency Control (OCC)](#optimistic-concurrency-control-occ)
  - [XSS Defense with Bleach Sanitizer](#xss-defense-with-bleach-sanitizer)
  - [Dual Authentication Strategy](#dual-authentication-strategy)
  - [Reusable Jinja2 Form Macros](#reusable-jinja2-form-macros)
- [Database Schema & Persistence](#database-schema--persistence)
- [RESTful API Reference](#restful-api-reference)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation & Setup](#installation--setup)
  - [Environment Configuration (.env)](#environment-configuration-env)
  - [Running the Application](#running-the-application)
  - [Running the Test Suite](#running-the-test-suite)
- [Project Directory Structure](#project-directory-structure)
- [License](#license)

---

## Key Features

- **Visual Kanban Board**: Organize tasks across 4 intuitive workflow stages: `To Do` → `In Progress` → `Review` → `Done`.
- **Fluid Drag-and-Drop**: Interactive card movement powered by HTML5 Drag & Drop and SortableJS with optimistic UI updates.
- **Dynamic Workspaces**: Create, manage, and configure multiple boards with custom members, avatars, and descriptions.
- **Task Management**: Title, rich-text instructions, priority indicators (`Low`, `Medium`, `High`), deadline picker with past-date prevention, and assignee allocation.
- **Interactive Discussions**: Real-time task comment threads supporting safe rich-text formatting (`<b>`, `<i>`, `<code>`, `<a>` with `rel="nofollow noopener"`).
- **Fast Search & Client-side Filters**: Real-time filtering by task title keyword, assignee member, and priority level without server re-renders.
- **Zero-Config Bootstrap**: Automatically verifies database health, executes migrations, and seeds initial demo data on startup.

---

## Architecture Overview

Team Task Board is built following the **Application Factory Pattern** with clear separation between representation, business logic, and persistence:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Client Layer                                   │
│  Browser Web UI (HTML5 / Bootstrap 5 / AJAX)  │  REST API Clients / Postman │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                        HTTP Requests  │  (Session Cookie / Bearer JWT)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Middleware Layer                                 │
│    CSRF Validation   │   Authentication Loader   │   Custom Error Handler   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Application Blueprints                            │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌───────────────────┐  │
│  │     `main` (Web)     │  │     `auth` (Auth)    │  │   `api` (REST)    │  │
│  │ HTML Pages, Modals,  │  │ Session & JWT Login, │  │ Task & Board CRUD,│  │
│  │ Kanban Board Views   │  │ Register, RBAC Guards│  │ Status, Comments  │  │
│  └──────────────────────┘  └──────────────────────┘  └───────────────────┘  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Data & Validation Layer                            │
│  WTForms / JsonForms │ Bleach Sanitizer │ OCC Guard │ SQLAlchemy 2.0 ORM     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Persistence Storage                                │
│      Microsoft SQL Server (Primary via PyODBC)  │  SQLite (Fallback / Test) │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Role-Based Access Control (RBAC)

Access permissions are enforced dynamically per board via `BoardMembership`:

| Action | Owner | Member | Viewer | Security Constraint |
|---|:---:|:---:|:---:|---|
| **View Board & Tasks** | ✅ Yes | ✅ Yes | ✅ Yes | Concealed (`404`) for non-members |
| **Create Task** | ✅ Yes | ✅ Yes | ❌ No | Viewers cannot create tasks (`403`) |
| **Edit Task Content** | ✅ Yes | 🟡 Conditional | ❌ No | Member: only if task creator or assignee |
| **Change Task Status** | ✅ Yes | 🟡 Conditional | ❌ No | Member: only if task creator or assignee |
| **Reassign Task** | ✅ Yes | 🟡 Conditional | ❌ No | Member: only if original task creator |
| **Delete Task** | ✅ Yes | ❌ No | ❌ No | Only Board Owner can delete tasks |
| **Post Comments** | ✅ Yes | ✅ Yes | ✅ Yes | Available to all active board members |
| **Manage Board Members** | ✅ Yes | ❌ No | ❌ No | Only Owner can invite, modify roles, or remove |
| **Demote / Remove Sole Owner** | ❌ Blocked | ❌ Blocked | ❌ Blocked | Invariant: Board must have at least one Owner |
| **Edit / Delete Board** | ✅ Yes | ❌ No | ❌ No | Cascades deletion to memberships, tasks & comments |

---

## Pre-configured Demo Accounts

The database comes pre-seeded with 4 accounts representing each RBAC tier:

**Default Password for all demo accounts:** `Password123`

| Username | Email | Initial Board Role | Permissions Summary |
| :--- | :--- | :---: | :--- |
| **`alex`** | `alex@example.com` | **Owner** | Full administrative rights: board settings, invite/remove members, role management, task deletion, and board deletion. *(Protected as sole owner)*. |
| **`ben`** | `ben@example.com` | **Member** | Creates tasks, edits and moves tasks created by or assigned to Ben, posts task comments. |
| **`chris`** | `chris@example.com` | **Member** | Creates tasks, edits and moves tasks created by or assigned to Chris, posts task comments. |
| **`david`** | `david@example.com` | **Viewer** | Read-only board access: views board and task details, posts comments. Cannot modify or move tasks. |

---

## Engineering & Security Highlights

### Optimistic Concurrency Control (OCC)
In high-concurrency environments where multiple teammates interact with the same board:
1. Every task entity maintains an `updated_at` timestamp with millisecond precision.
2. When a client reads a task, it receives the ISO 8601 timestamp (e.g., `2026-11-06T14:30:00.123Z`).
3. When saving modifications (`PUT /api/tasks/<id>/status` or `PATCH /api/tasks/<id>`), the client sends back its last-read timestamp.
4. The server compares the client token against the current database timestamp:
   - **Match**: Update is committed; new timestamp returned.
   - **Mismatch (Stale)**: The server aborts with **`409 Conflict`** and message: `"Task was modified by another user. Reload latest data."`
   - **UI Behavior**: The Kanban card automatically snaps back to its original column and displays an error toast notification without disrupting other cards.

### XSS Defense with Bleach Sanitizer
User input is sanitized through a defense-in-depth model before database persistence:
- **Task Titles**: Plain text sanitized via `clean_text()` — dangerous script/style tags, event handlers (`onerror`, `onload`), and HTML tags are stripped.
- **Task Descriptions & Comments**: Rich text sanitized via `clean_html()`:
  - Strict allowlist: `<b>`, `<i>`, `<u>`, `<em>`, `<strong>`, `<code>`, `<pre>`, `<p>`, `<br>`, `<ul>`, `<ol>`, `<li>`, `<blockquote>`, `<a>`.
  - Dangerous protocols (`javascript:`) are removed; external links (`<a>`) are verified and automatically injected with `rel="nofollow noopener"`.
- **Templates**: Jinja2 auto-escapes all context variables by default.

### Dual Authentication Strategy
- **Web UI**: Session cookie authentication powered by `Flask-Login` with hardened cookie attributes (`HttpOnly=True`, `SameSite="Lax"`).
- **RESTful API**: Stateless Bearer JWT tokens powered by `Flask-JWT-Extended` (`Authorization: Bearer <token>`).
- **CSRF Protection**: Handled via `Flask-WTF` CSRFProtect. Browser sessions require CSRF tokens (`X-CSRFToken` header or form input); Bearer token API requests bypass cookie CSRF checks cleanly.

### Reusable Jinja2 Form Macros
Web forms (`/login`, `/register`, `/change-password`) are rendered through reusable Jinja2 macros defined in [`app/templates/kanban/_form_helpers.html`](file:///app/templates/kanban/_form_helpers.html):
- `render_field(field)`: Renders input with label, placeholder, and server-side validation error feedback (`is-invalid` / `invalid-feedback`).
- `render_password_field(field)`: Renders password field with appropriate security attributes.
- `render_submit(text)`: Renders consistent action buttons with loading states.
- `render_flashes()`: Renders dismissible Bootstrap alert boxes for flash messages.

---

## Database Schema & Persistence

The relational database architecture is built on **5 models** with full Unicode (`NVARCHAR`) support for international text and diacritics:

```sql
users (id, username, email, password_hash, created_at)
boards (id, name, description, created_at, updated_at)
board_memberships (id, user_id, board_id, role, joined_at)
  └── Foreign Keys: user_id -> users.id (CASCADE), board_id -> boards.id (CASCADE)
  └── Check Constraint: role IN ('owner', 'member', 'viewer')
  └── Unique Constraint: (user_id, board_id)
tasks (id, title, description, status, priority, deadline, board_id, assigned_to, created_by, created_at, updated_at)
  └── Foreign Keys: board_id -> boards.id (CASCADE), assigned_to -> users.id, created_by -> users.id
  └── Check Constraints: status IN ('todo', 'in_progress', 'review', 'done'), priority IN ('low', 'medium', 'high')
comments (id, task_id, user_id, content, created_at, updated_at)
  └── Foreign Keys: task_id -> tasks.id (CASCADE), user_id -> users.id (CASCADE)
```

Database migrations are tracked and executed via **Flask-Migrate / Alembic** in `migrations/versions/`.

---

## RESTful API Reference

| Category | Method | Endpoint | Auth | Description | Status Codes |
|---|:---:|---|:---:|---|:---:|
| **Auth** | `POST` | `/auth/login` | None | Authenticate credentials; returns JWT access token | `200`, `400`, `401` |
| **Auth** | `POST` | `/auth/register` | None | Register new user account | `201`, `400`, `409` |
| **Boards** | `GET` | `/api/boards` | Bearer | List all boards current user belongs to | `200`, `401` |
| **Boards** | `POST` | `/api/boards` | Bearer | Create a new board (creator becomes Owner) | `201`, `400`, `401` |
| **Boards** | `GET` | `/api/boards/<id>` | Bearer | Get board details, role, and member list | `200`, `401`, `404` |
| **Boards** | `PATCH` | `/api/boards/<id>` | Bearer | Update board name / description (Owner only) | `200`, `400`, `403`, `404` |
| **Boards** | `DELETE`| `/api/boards/<id>` | Bearer | Delete board and cascade all tasks (Owner only)| `204`, `403`, `404` |
| **Members**| `POST` | `/api/boards/<id>/members` | Bearer | Add member to board (Owner only) | `201`, `400`, `403`, `404`, `409` |
| **Members**| `PATCH`| `/api/boards/<id>/members/<uid>` | Bearer | Change member role (Sole owner protected) | `200`, `400`, `403`, `404` |
| **Members**| `DELETE`| `/api/boards/<id>/members/<uid>` | Bearer | Remove member or leave board | `200`, `400`, `403`, `404` |
| **Tasks** | `GET` | `/api/boards/<id>/tasks` | Bearer | Get all Kanban tasks on a board | `200`, `401`, `404` |
| **Tasks** | `POST` | `/api/boards/<id>/tasks` | Bearer | Create task (Member / Owner; past deadline blocked) | `201`, `400`, `403`, `404` |
| **Tasks** | `GET` | `/api/tasks/<id>` | Bearer | Get task detail and comments | `200`, `401`, `404` |
| **Tasks** | `PUT` | `/api/tasks/<id>/status` | Bearer | Change status with OCC `updated_at` check | `200`, `400`, `403`, `404`, `409` |
| **Tasks** | `PATCH` | `/api/tasks/<id>` | Bearer | Partial edit task with OCC `updated_at` check | `200`, `400`, `403`, `404`, `409` |
| **Tasks** | `DELETE`| `/api/tasks/<id>` | Bearer | Delete task (Owner only) | `204`, `403`, `404` |
| **Comments**| `POST`| `/api/tasks/<id>/comments` | Bearer | Add sanitized comment to task | `201`, `400`, `401`, `404` |
| **RBAC** | `GET` | `/api/rbac/boards/<id>/summary` | Bearer | View board summary (`@viewer_required`) | `200`, `401`, `404` |
| **RBAC** | `POST` | `/api/rbac/boards/<id>/pin` | Bearer | Pin board to quick access (`@member_required`)| `200`, `401`, `403`, `404` |

---

## Getting Started

### Prerequisites
- **Python 3.11+**
- **Git**
- *(Optional)* Microsoft SQL Server 2019+ and ODBC Driver 18 for SQL Server (automatic SQLite fallback is used if SQL Server is not configured)

### Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd Team-Task-Board
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Windows PowerShell:
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # Linux / macOS:
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Environment Configuration (.env)

Create a `.env` file in the root directory:

```env
# Application Secrets
SECRET_KEY=dev-team-task-board-secret-key-32bytes-secure!
JWT_SECRET_KEY=dev-jwt-task-board-secret-key-32bytes-min!

# Option A: Connect to Microsoft SQL Server (Production)
# DATABASE_URL=mssql+pyodbc://sa:YourPassword@localhost,1433/TeamTaskBoard?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes

# Option B: Leave DATABASE_URL empty to use automatic SQLite fallback (instance/dev.db)
```

### Running the Application

Start the application runner:
```bash
python run.py
```

`run.py` automatically:
1. Verifies the database connection.
2. Applies pending database migrations (`flask db upgrade`).
3. Auto-seeds the 4 demo accounts, board, and tasks if the database is empty.
4. Starts the local server at `http://127.0.0.1:5000`.

**Helpful CLI commands:**
- Re-seed demo data: `python run.py --reseed --yes`
- Apply migrations manually: `flask db upgrade`
- Run standalone database seed: `python seed.py`

### Running the Test Suite

Execute the automated test suite with pytest:
```bash
pytest
```
*Output: **107 passed in ~78s** across all test suites:*
- `test_models.py`: Model relationships, password hashing, cascade deletes.
- `test_auth.py`: Authentication, form validation, password changes.
- `test_board_api.py` & `test_board_pages.py`: Board CRUD, membership, page controllers.
- `test_task_api.py`: Task CRUD, deadline validation, permission boundaries.
- `test_api_routes.py`: Contract API endpoints, comments, OCC conflict detection.
- `test_jwt_rbac_isolated.py` & `test_rubric.py`: Custom decorators and Bleach sanitizer tests.
- `test_demo_bootstrap.py`: Zero-config database bootstrap verification.

---

## Project Directory Structure

```text
Team-Task-Board/
├── app/
│   ├── __init__.py           # Application Factory (create_app) & Blueprint registration
│   ├── extensions.py         # SQLAlchemy & Flask-Migrate instances
│   ├── api/                  # RESTful API Endpoints & Business Logic
│   │   ├── forms.py          # Unified WTForms/JsonForms for API payloads
│   │   ├── guards.py         # Permission helpers, board/task context & OCC checks
│   │   ├── routes.py         # Core API routes (tasks list, status update, comments)
│   │   ├── boards.py         # Board CRUD & membership endpoints
│   │   ├── tasks.py          # Detailed task operations (create, patch, delete)
│   │   └── serializers.py   # JSON dict serializers (task_dict, comment_dict)
│   ├── auth/                 # Authentication, JWT & Security
│   │   ├── forms.py          # Web forms (LoginForm, RegisterForm, ChangePasswordForm)
│   │   ├── jwt_helpers.py    # Stateless JWT authentication & jwt_api_required
│   │   ├── rbac.py           # Custom decorators (@role_required, @owner_required, ...)
│   │   ├── rbac_routes.py    # Decorator demonstration endpoints (/api/rbac)
│   │   ├── routes.py         # Web auth routes (login, register, logout, change password)
│   │   └── sanitizer.py      # Bleach HTML sanitizer (clean_text, clean_html)
│   ├── main/                 # Web UI Page Controllers
│   │   ├── demo.py           # Database pre-flight verification & auto-seeding
│   │   ├── routes.py         # HTML page routes (/, /boards, /boards/<id>)
│   │   └── setup.py          # CSRF protection, LoginManager & custom error handlers
│   ├── models/               # SQLAlchemy ORM Models
│   │   ├── board.py          # Board & BoardMembership models
│   │   ├── comment.py        # Comment model
│   │   ├── task.py           # Task model (TaskStatus, TaskPriority, constraints)
│   │   └── user.py           # User model (password hashing & verification)
│   ├── static/kanban/        # Frontend Static Assets
│   │   ├── css/kanban.css    # Custom responsive Kanban styling
│   │   └── js/
│   │       ├── boards.js     # Board management, search, modals & member administration
│   │       └── kanban.js     # Kanban board UI, Drag & Drop, task detail, OCC alerts
│   └── templates/kanban/     # Jinja2 Templates
│       ├── base.html         # Base template with Bootstrap 5, navbar & CSRF token
│       ├── boards.html       # Board listing page
│       ├── board.html        # Interactive Kanban workspace (4 columns & modals)
│       ├── login.html        # User sign-in page
│       ├── register.html     # User registration page
│       ├── change_password.html # Password update page
│       ├── error.html        # Friendly error page (400, 403, 404, 405, 500)
│       ├── _form_helpers.html   # Reusable Jinja2 form macros
│       ├── _board_form_modal.html # Create / edit board modal
│       └── _members_modal.html    # Member management modal
├── docs/                     # Technical Documentation & Specifications
│   ├── api_contract.md       # RESTful API payload & response contracts
│   └── business_rules.md     # RBAC and concurrency business rules
├── migrations/               # Alembic Migration Versions
├── tests/                    # Automated Test Suite (107 tests)
├── config.py                 # Multi-environment configuration classes
├── requirements.txt          # Python package dependencies
├── run.py                    # Application entry point with bootstrap checks
└── seed.py                   # Demo database seeding script
```

---

## License

Distributed under the [MIT License](LICENSE).
