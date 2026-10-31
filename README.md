# Team Task Board (Kanban)

![Team Task Board](Logo/screen.png)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Framework](https://img.shields.io/badge/Framework-Flask-green.svg)](#)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](#)
[![Tests](https://img.shields.io/badge/Tests-107%20passed-brightgreen.svg)](#)

A modern web-based Kanban task management application built with **Flask** for team collaboration, offering visual workflow tracking, role-based access control (RBAC), optimistic concurrency control (OCC), and real-time interactive task updates via AJAX/Fetch API.

---

## Key Features & Workflow

- **Visual Kanban Board**: Track tasks seamlessly across 4 workflow columns: `To Do` → `In Progress` → `Review` → `Done`.
- **Role-Based Access Control (RBAC)**: Comprehensive permission enforcement with 3 roles:
  - **`Owner`**: Full board control, manage settings, invite/remove members, modify roles, delete tasks/boards.
  - **`Member`**: Create tasks, update status and edit tasks assigned to or created by them, post comments.
  - **`Viewer`**: Read-only board access, post comments.
- **Collaborative Tasks**: Assign tasks to team members, set deadlines and priority levels (`Low`, `Medium`, `High`).
- **Real-time AJAX/Fetch API**: Dynamic drag-and-drop status transitions, comment addition, and board/member management without full page reloads.
- **Application Security**:
  - 100% SQLAlchemy ORM parameterized queries (SQL Injection prevention).
  - CSRF protection across all web forms and AJAX requests (`X-CSRFToken`).
  - Jinja2 auto-escaping + **Bleach** HTML content sanitization for descriptions and comments (XSS prevention).
  - Secure session cookies (`HttpOnly`, `SameSite=Lax`, permanent lifetime).
  - Password hashing with Werkzeug.
  - Optimistic Concurrency Control (OCC) using ISO 8601 `updated_at` timestamps to avoid edit conflicts (`409 Conflict`).
- **RESTful API**: Standardized JSON responses with HTTP status codes and stateless JWT authentication.

---

## Tech Stack

- **Backend**: Flask 3.0+, SQLAlchemy 2.0+, Flask-WTF, Flask-Login, Flask-JWT-Extended, Flask-Migrate
- **Database**: Microsoft SQL Server (Primary) / SQLite (Fallback/Testing)
- **Frontend**: Bootstrap 5.3+, Bootstrap Icons, Vanilla JavaScript (Fetch API / AJAX), Jinja2 template inheritance with reusable macros
- **Testing**: pytest (107 unit & integration tests)

---

## Demo Accounts (Seed Data)

The application includes pre-configured demo accounts for all 3 RBAC roles. When running `python run.py`, empty databases are automatically populated with these seed accounts, 1 sample board (`Website Development`), 8 tasks, and 5 discussion comments.

**Default Password for all seed accounts:** `Password123`

| Username | Email | Role | Permissions / Role Summary |
| :--- | :--- | :---: | :--- |
| **`alex`** | `alex@example.com` | **Owner** | Full administrative rights: edit/delete board, invite/remove members, change roles, delete tasks, create/edit all tasks. *(Sole owner is protected from self-demotion/removal)*. |
| **`ben`** | `ben@example.com` | **Member** | Create new tasks, edit & change status of assigned/created tasks, reassign created tasks, add/edit comments. |
| **`chris`** | `chris@example.com` | **Member** | Create new tasks, edit & change status of assigned/created tasks, reassign created tasks, add/edit comments. |
| **`david`** | `david@example.com` | **Viewer** | Read-only board access: view board and task details, add comments to tasks. Cannot create or edit tasks. |

---

## Getting Started

### 1. Prerequisites
- Python 3.11+
- Git

### 2. Installation & Setup
```bash
# Clone the repository
git clone <repository-url>
cd Team-Task-Board

# Create and activate virtual environment
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration (`.env`)
Create a `.env` file in the root directory:
```env
SECRET_KEY=your-secure-random-secret-key-32bytes
JWT_SECRET_KEY=your-jwt-secret-key-32bytes-secure

# Optional: Connect to Microsoft SQL Server (if omitted, SQLite instance/dev.db is used automatically)
# DATABASE_URL=mssql+pyodbc://sa:YourPassword@localhost:1433/TeamTaskBoard?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
```

### 4. Run Application
```bash
python run.py
```
`run.py` automatically checks the database connection, executes database migrations if tables are missing, and auto-seeds the demo data if the database is empty.

Open your browser at `http://127.0.0.1:5000` and sign in with any of the demo accounts above (e.g., `alex` / `Password123`).

- **To re-seed demo data:** `python run.py --reseed --yes`
- **To run standalone seed:** `python seed.py`

### 5. Run Automated Tests
```bash
pytest
```
Runs 107 test cases covering models, authentication, session management, RBAC custom decorators, REST API endpoints, optimistic concurrency control, and Jinja2 macros.

---

## Database Schema (5 Tables)

1. `users`: Credentials, profile information, and password hashes.
2. `boards`: Board metadata, workspace information, and ownership.
3. `board_memberships`: Association table mapping users to boards with specific roles (`owner`, `member`, `viewer`) and timestamps (Many-to-Many).
4. `tasks`: Kanban tasks with `title`, `description`, `status` (`todo`, `in_progress`, `review`, `done`), `priority` (`low`, `medium`, `high`), `deadline`, `board_id`, `created_by`, and `assigned_to`.
5. `comments`: Discussion threads linked to tasks and authoring users.

---

## Project Structure

```text
Team-Task-Board/
├── app/
│   ├── api/                  # RESTful API endpoints, OCC logic & API JsonForms
│   │   ├── forms.py          # Unified Flask-WTF validation for JSON payloads
│   │   ├── guards.py         # Request context, auth guards & permission checks
│   │   ├── routes.py         # Contract endpoints: tasks, status updates, comments
│   │   ├── boards.py         # Board CRUD & member management endpoints
│   │   ├── serializers.py   # JSON serialization helpers
│   │   └── tasks.py          # Detailed task endpoints & operations
│   ├── auth/                 # Authentication, JWT & RBAC
│   │   ├── forms.py          # Web forms: Login, Register, Change Password
│   │   ├── jwt_helpers.py    # Stateless JWT authentication & request_loader
│   │   ├── rbac.py           # Custom decorators (@role_required, @owner_required, ...)
│   │   ├── rbac_routes.py    # RBAC endpoints (/api/rbac and /m2/api)
│   │   ├── routes.py         # Web auth routes (login, register, logout, password change)
│   │   └── sanitizer.py      # Bleach XSS prevention for user-submitted content
│   ├── main/                 # Web UI bootstrap & page controllers
│   │   ├── demo.py           # Auto database verification & seed helpers
│   │   ├── routes.py         # Web page routes (/, /boards, /boards/<id>)
│   │   └── setup.py          # CSRF, LoginManager & custom error handlers
│   ├── models/               # SQLAlchemy ORM Models (User, Board, Task, Comment, Membership)
│   ├── static/kanban/        # Frontend assets (Bootstrap 5 CSS, boards.js, kanban.js)
│   └── templates/kanban/     # Jinja2 templates & reusable macros (_form_helpers.html)
├── docs/                     # API contracts, business rules & architecture plans
├── migrations/               # Alembic database migration scripts
├── tests/                    # Automated pytest test suite (107 tests)
├── config.py                 # Configuration classes (Development, Testing, Production)
├── requirements.txt          # Python dependencies
├── run.py                    # Application entry point with pre-flight checks
└── seed.py                   # Demo database seeding script
```

---

## License

Distributed under the [MIT License](LICENSE).
