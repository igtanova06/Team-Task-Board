# Team Task Board (Kanban)

![Team Task Board](Logo/screen.png)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Framework](https://img.shields.io/badge/Framework-Flask-green.svg)](#)

> **Project Phase Notice**: Team Task Board is currently in its initial setup phase. Architecture, database migrations, and UI components are under active development.

A web-based Kanban task management application built with **Flask** for small team collaboration, offering visual workflow tracking, role-based permissions, and task comments.

---

## Key Features & Workflow

- **Visual Kanban Board**: Track tasks across stages: `To Do` → `In Progress` → `Review` → `Done`.
- **Role-Based Access**: Permission management with 3 roles: `Owner`, `Member`, `Viewer`.
- **Collaborative Tasks**: Task assignments, descriptions, and interactive comment threads.
- **Asynchronous UI**: Dynamic updates via JS Fetch API / AJAX.

---

## Tech Stack

- **Backend**: Flask, SQLAlchemy, Flask-WTF, Flask-Login, JWT
- **Frontend**: Bootstrap 5, Vanilla JavaScript (Fetch API / AJAX)
- **DevOps**: Docker

---

## Planned Database Schema (5 Tables)

1. `users`: Credentials & profile data.
2. `boards`: Board metadata & ownership.
3. `board_memberships`: Maps users to boards with roles (`Owner`, `Member`, `Viewer`).
4. `tasks`: Task items, assignees, board associations, and statuses (`To Do`, `In Progress`, `Review`, `Done`).
5. `comments`: Discussion notes linked to tasks and users.

---

## 4-Week Development Plan

| Week | Focus | Objectives |
| :--- | :--- | :--- |
| **Week 1** | **Setup & Auth** | Repo setup, Docker config, SQLAlchemy models, Flask-Login & JWT auth. |
| **Week 2** | **Backend Core** | Board CRUD APIs, membership role middleware, Flask-WTF forms. |
| **Week 3** | **Task Engine & UI** | Task CRUD, status updates, comments, Bootstrap 5 Kanban board with AJAX. |
| **Week 4** | **Testing & Deploy** | Integration testing, permission audits, UI polish, Docker optimization. |

---

## Running the app

```bash
pip install -r requirements.txt
# .env: SECRET_KEY=...  DATABASE_URL=mssql+pyodbc://...   (see HUONG_DAN_TEST_DB.txt)
flask --app run db upgrade      # create the 5 tables
python seed.py                  # sample data (password for every user: Password123)
python run.py                   # http://127.0.0.1:5000  -> sign in as alex / ben / chris / david
```

If `DATABASE_URL` is not set the app falls back to a local SQLite file (`instance/dev.db`) so the UI can be tried without SQL Server.

## Kanban board (Week 2-3)

- **Pages**: `/login`, `/boards/<id>` (Jinja + Bootstrap 5, theme "Agile Slate").
- **AJAX**: the board is loaded and changed through the JSON API with `fetch`; the CSRF token is sent in `X-CSRFToken`.
- **Drag & drop**: SortableJS (mouse + touch). Dropping a card calls `PATCH /api/tasks/<id>/status` optimistically and rolls back with an error toast if the request fails. Cards inside a column are sorted by priority, then deadline.
- **Validation**: Flask-WTF forms on the server (`app/forms.py`), mirrored inline on the client. Errors come back as `422 {"error", "errors": {field: [msg]}}`.

### API

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| GET | `/api/boards/<id>` | board, my role, members, tasks |
| POST | `/api/boards/<id>/tasks` | create task |
| GET | `/api/tasks/<id>` | task + comments |
| PUT / PATCH | `/api/tasks/<id>` | update task (partial allowed) |
| PATCH | `/api/tasks/<id>/status` | move task between columns |
| DELETE | `/api/tasks/<id>` | delete task |
| POST | `/api/tasks/<id>/comments` | add comment |

### Authorization (checked on the server for every request)

| Role | View | Create / edit / move / comment | Delete task |
| :--- | :---: | :---: | :--- |
| owner | yes | yes | any task |
| member | yes | yes | only tasks they created |
| viewer | yes | no | no |

Non-members get `403`; unauthenticated API calls get `401`. Assignees must be an owner/member of the board.

### Tests

`python -m pytest -v` (models + API, in-memory SQLite).

---

## License

Distributed under the [MIT License](LICENSE).
