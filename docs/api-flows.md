# Team Task Board — API Sequence Flows

**Version:** 1.0  
**Status:** Approved Reference  
**Reference Documents:** [docs/business_rules.md](file:///home/igtanova/Documents/NCKH/Team-Task-Board/docs/business_rules.md), [docs/api_contract.md](file:///home/igtanova/Documents/NCKH/Team-Task-Board/docs/api_contract.md)

---

## Overview

This document details the interaction flows between Frontend, API Gateway/Blueprint, Authentication Service, Permission Policy, and Database Layer using **Mermaid Sequence Diagrams**.

---

## 1. Comment Creation Flow

1. Client sends a request to post a comment.
2. API verifies authentication and board membership.
3. API validates content non-emptiness.
4. Database persists the comment associated with the authenticated user ID.

```mermaid
sequenceDiagram
    autonumber
    actor FE as Frontend Client
    participant API as Flask API (/api)
    participant Auth as Auth & Membership Check
    participant DB as SQL Server DB

    FE->>API: POST /api/tasks/{task_id}/comments (content)
    API->>Auth: Verify JWT Token & BoardMembership(user_id, board_id)
    
    alt Unauthenticated / Invalid Token
        Auth-->>API: Authentication Failed
        API-->>FE: 401 Unauthorized
    else No Board Membership
        Auth-->>API: Membership Not Found
        API-->>FE: 404 Not Found (Concealed Resource)
    else Active Member / Owner / Viewer
        Auth-->>API: Authorized
        API->>API: Validate Content (non-empty string)
        alt Empty or Whitespace Content
            API-->>FE: 400 Bad Request
        else Valid Content
            API->>DB: INSERT INTO comments (task_id, user_id, content, created_at, updated_at)
            DB-->>API: Return Persisted Comment (id, timestamps)
            API-->>FE: 201 Created (Comment Object)
        end
    end
```

---

## 2. Status Update & Concurrency Flow (OCC)

1. Client sends status update with previously read timestamp/version.
2. API verifies board membership and task-level update permissions:
   - `Owner`: Allowed for all tasks in board.
   - `Member`: Allowed only if `created_by == current_user` OR `assigned_to == current_user`.
3. API validates status enum value (`todo`, `in_progress`, `review`, `done`).
4. API verifies concurrency token (`updated_at` / version).
5. If stale, returns `409 Conflict`. Otherwise, updates status atomically.

```mermaid
sequenceDiagram
    autonumber
    actor FE as Frontend Client
    participant API as Flask API (/api)
    participant Auth as Auth & Permission Policy
    participant DB as SQL Server DB

    FE->>API: PUT /api/tasks/{task_id}/status (status, updated_at)
    API->>Auth: Check BoardMembership & Task Edit Permission
    
    alt Insufficient Permission (Viewer or Unassigned Member)
        Auth-->>API: Permission Denied
        API-->>FE: 403 Forbidden
    else Authorized (Owner or Creator/Assignee Member)
        Auth-->>API: Permission Granted
        API->>API: Validate Status in TaskStatus.ALL
        alt Invalid Status Value
            API-->>FE: 400 Bad Request
        else Valid Status
            API->>DB: SELECT updated_at FROM tasks WHERE id = task_id
            alt DB.updated_at > Payload.updated_at (Stale Data)
                API-->>FE: 409 Conflict ("Data modified by another user")
            else Timestamp Matches
                API->>DB: UPDATE tasks SET status = new_status, updated_at = now() WHERE id = task_id
                DB-->>API: Return Updated Task
                API-->>FE: 200 OK (Updated Task Object)
            end
        end
    end
```

---

## 3. JWT Authentication & Authorization Flow

1. User logs in with email/password and receives a signed JWT token.
2. Client attaches `Authorization: Bearer <token>` on protected requests.
3. Server decodes JWT to get `user_id`.
4. Server queries active `BoardMembership` for authorization decision.

```mermaid
sequenceDiagram
    autonumber
    actor FE as Frontend Client
    participant AuthAPI as Auth API (/api/auth)
    participant CoreAPI as Core API (/api)
    participant DB as SQL Server DB

    %% Step 1: Login
    FE->>AuthAPI: POST /api/auth/login (email, password)
    AuthAPI->>DB: Query User by email
    alt User Not Found or Invalid Password
        AuthAPI-->>FE: 401 Unauthorized ("Invalid credentials")
    else Credentials Valid
        AuthAPI->>AuthAPI: Generate JWT (sub=user_id, exp)
        AuthAPI-->>FE: 200 OK (access_token)
    end

    %% Step 2: Protected Resource Request
    FE->>CoreAPI: GET /api/boards/{board_id}/tasks (Header: Bearer token)
    CoreAPI->>CoreAPI: Verify JWT Signature & Expiration
    alt Invalid / Expired Token
        CoreAPI-->>FE: 401 Unauthorized ("Token expired or invalid")
    else Valid Token (user_id)
        CoreAPI->>DB: Query BoardMembership WHERE user_id = current_user AND board_id = requested_board
        alt Membership Active
            CoreAPI->>DB: Fetch Tasks for board_id
            DB-->>CoreAPI: Tasks List
            CoreAPI-->>FE: 200 OK (Tasks List)
        else No Membership
            CoreAPI-->>FE: 404 Not Found (Access Concealed)
        end
    end
```
