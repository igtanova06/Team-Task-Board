# Team Task Board (Kanban)

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

## License

Distributed under the [MIT License](LICENSE).
