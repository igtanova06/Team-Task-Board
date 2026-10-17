# Team Task Board — Business Rules Specification (Lean Baseline)

**Version:** 1.2 (Lean)  
**Status:** Active Baseline  
**Scope:** Core Board, Task, and Comment API Implementation

---

## 1. Roles and Permission Matrix

Board access is governed per-board via `BoardMembership`. Roles are board-specific:
- **`owner`**: Administrative control over the board, tasks, and members.
- **`member`**: Creates tasks; manages tasks they created or are assigned to.
- **`viewer`**: Read-only access to tasks; permitted to post comments.

### Permission Matrix

| Action | Owner | Member | Viewer | Notes |
|---|:---:|:---:|:---:|---|
| View board & tasks | Yes | Yes | Yes | Requires active board membership |
| Edit / Delete board | Yes | No | No | |
| Manage board members | Yes | No | No | Owner cannot leave if sole owner |
| Create task | Yes | Yes | No | |
| Edit task | Yes | Conditional | No | Member: only if creator or current assignee |
| Delete task | Yes | No | No | Hard delete cascades to comments |
| Reassign task | Yes | Conditional | No | Member: only if creator of the task |
| Change task status | Yes | Conditional | No | Member: only if creator or current assignee |
| View / Add comments | Yes | Yes | Yes | Comment author fixed to current user |
| Edit / Delete own comment | Yes | Yes | Yes | Users can only modify their own comments |
| Delete others' comments | Yes | No | No | Moderation right reserved for Owner |

---

## 2. Core Invariants

### 2.1 Access & Authorization
- **Membership Boundary:** Every API request must verify active `BoardMembership` before returning or mutating data.
- **User Identity:** `user_id` is resolved from verified authentication (session/token), never from client payloads.
- **Authorization Freshness:** Permissions must be evaluated against current board membership at request time.

### 2.2 Task Management
- **Assignment Scope:** Tasks can be unassigned or assigned only to users with active membership on the same board.
- **Assignment Boundary:** Task editing permission does not implicitly grant task reassignment permission.
- **Task Status:** Allowed values are `todo`, `in_progress`, `review`, and `done`. All transitions among valid values are permitted.
- **Concurrency Safety:** Task updates must supply the last observed `updated_at` timestamp. Updates with stale timestamps are rejected with `409 Conflict` to prevent overwriting concurrent modifications.

### 2.3 Comments
- **Content Validation:** Blank or whitespace-only content is rejected (`400 Bad Request`).


---

## 3. API Conventions & Scope

### 3.1 HTTP Status Codes & Direct JSON Standard
- `200 OK` / `201 Created`: Operation successful. Returns resource payload directly (no custom envelope wrapper).
- `400 Bad Request`: Payload validation error (e.g. invalid status, empty comment).
- `401 Unauthorized` / `403 Forbidden`: Unauthenticated or insufficient role permissions.
- `404 Not Found`: Resource does not exist or user lacks access.
- `409 Conflict`: Concurrency update conflict (submitted `updated_at` does not match current state).

### 3.2 Target Endpoints (Week 1 Scope)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/boards/{board_id}/tasks` | Retrieve board tasks |
| PUT | `/api/tasks/{task_id}/status` | Update task status |
| POST | `/api/tasks/{task_id}/comments` | Add comment to task |

---

## 4. Deferred Extensions (Future Scope)

- Comment listing endpoint with pagination (`GET /api/tasks/{task_id}/comments`).
- Task detail retrieval and full patch (`GET` / `PATCH /api/tasks/{task_id}`).
- Comment modification and deletion endpoints.
- Board ownership transfer workflows.

---

## 5. Implementation Notes & Concurrency Decision

- **Implementation Note:** Week 1 baseline establishes API endpoints with mock data and payload validation. Authentication, authorization enforcement, and database persistence will be integrated in subsequent phases.
- **Concurrency Decision:** Existing `updated_at` field in `Task` model and database migration is adopted as the Optimistic Concurrency Control token. No schema migration or additional `version` column is required.


