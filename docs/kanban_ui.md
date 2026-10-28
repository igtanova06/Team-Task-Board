# Kanban UI - structure, extra endpoints, demo checklist

## Where the code lives (so teammates do not overwrite each other)

| Folder / file | Owner | Content |
| :--- | :--- | :--- |
| `app/api/__init__.py` | Member 4 | blueprint `api` (unchanged) |
| `app/api/routes.py` | Member 4 | the 3 contract endpoints - **mock bodies replaced by real DB logic**, same paths / function names / validation order |
| `app/api/guards.py`, `serializers.py`, `task_forms.py`, `tasks.py` | Kanban UI | auth + RBAC helpers, JSON shapes, WTForms validation, extra endpoints |
| `app/auth/` (no `__init__.py` on purpose) | Member 2 | add `__init__.py` + `routes.py` here for JWT (`/api/auth/*`) |
| `app/auth/web.py` | Kanban UI | browser sign-in `/login`, `/logout` (blueprint `web_auth`) |
| `app/main/` | Kanban UI | HTML pages (`/`, `/boards/<id>`), `setup.py` (CSRF, login manager, error handlers), `demo.py` (DB check + seed) |
| `app/templates/kanban/`, `app/static/kanban/` | Kanban UI | templates, CSS, JS (namespaced folders) |
| `app/__init__.py`, `run.py` | shared | only a few additive lines (marked with comments) |

`config.py`, `app/extensions.py`, `seed.py`, `app/models/*` are untouched.

## API

Follows `docs/api_contract.md` + `docs/business_rules.md`: direct JSON, errors as `{"detail": "...", "errors": {field: [msg]}}`,
`400` validation, `401` not signed in, `403` not allowed, `404` not a member (access concealed), `409` stale `updated_at`, `415` not JSON.

Contract endpoints (implemented for real): `GET /api/boards/{id}/tasks`, `PUT /api/tasks/{id}/status`, `POST /api/tasks/{id}/comments`.

Extra endpoints used by the UI (not in the contract yet - Member 4 please review):

| Method | Endpoint | Notes |
| :--- | :--- | :--- |
| GET | `/api/boards/{id}` | board, my role, members |
| POST | `/api/boards/{id}/tasks` | create (owner, member) |
| GET | `/api/tasks/{id}` | task + comments |
| PATCH | `/api/tasks/{id}` | edit; optional `updated_at` => 409 if stale |
| DELETE | `/api/tasks/{id}` | owner only |

Timestamps are UTC ISO 8601 with milliseconds (`2026-10-10T07:00:00.000Z`); the client sends back the `updated_at` it last read.
Task objects also carry `permissions` (`edit`, `status`, `reassign`, `delete`) so the UI can lock cards.

Authentication is the Flask-Login session cookie (browser). Cookie requests must send the CSRF token (`X-CSRFToken`);
requests with `Authorization: Bearer ...` are exempt. **Member 2:** accept the JWT inside `authenticated_user()` in `app/api/guards.py`.

## Demo checklist (every machine, including the examiner's)

```
pip install -r requirements.txt
# .env next to run.py:  SECRET_KEY=...   DATABASE_URL=mssql+pyodbc://...   (see HUONG_DAN_TEST_DB.txt)
python run.py
```

`python run.py` always runs these checks first, then starts the server:

1. connects to the database (on failure it prints what to check and exits);
2. creates the tables with the migrations if they are missing;
3. runs `seed.py` automatically if the database is empty (never touches a database that already has users).

Other commands: `python run.py --reseed` (wipe + seed again, asks for `YES`; add `--yes` to skip), `AUTO_SEED=0` to disable auto-seed,
`python seed.py` still works on its own. Without `DATABASE_URL` a local SQLite file `instance/dev.db` is used.

Accounts (password `Password123`): `alex` owner, `ben` / `chris` members, `david` viewer.

Tests: `python -m pytest -v` (in-memory SQLite).

## Board management UI (boards list, board settings, members)

Pages / hooks (all data via Fetch/AJAX against `docs/board_and_member_api_plan.md` endpoints, CSRF header `X-CSRFToken`):

| UI | Where | API |
|---|---|---|
| Board list (`/boards`, `/` redirects here) with search, empty state | `kanban/boards.html`, `boards.js` | `GET /api/boards` |
| Navbar board switcher (every signed-in page) | `base.html`, `boards.js` | `GET /api/boards` |
| Create board modal -> redirects into the new board | `_board_form_modal.html` | `POST /api/boards` |
| Board settings (owner): rename / description / delete with confirmation | same modal | `PATCH` / `DELETE /api/boards/<id>` |
| Leave board (list menu) | `boards.js` | `DELETE /api/boards/<id>/members/<me>` |
| Members dialog: list, invite by username/email, change role, remove / leave | `_members_modal.html` | `GET /api/boards/<id>`, `POST .../members`, `PATCH/DELETE .../members/<uid>` |

Rules enforced in the UI **and** the API: only owners see settings / invite / role / remove controls; the sole owner cannot demote or remove themselves (server message shown as a toast, select reverts); removing a member unassigns their tasks; non-members get 404.
`boards.js` emits `ttb:board-saved`, `ttb:board-deleted`, `ttb:members-changed`; `kanban.js` listens to the last one to refresh avatars, assignee filter and cards.
Tests: `tests/test_board_pages.py` plus the 37-step browser run described in the PR.
