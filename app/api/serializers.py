"""JSON shapes returned by /api (fields of docs/api_contract.md plus a few UI extras)."""
from app.api import guards


def iso(dt):
    """2026-10-10T07:00:00.000Z  (UTC, millisecond precision, also the concurrency token)."""
    return dt.isoformat(timespec="milliseconds") + "Z" if dt else None


def user_dict(u):
    return {"id": u.id, "username": u.username} if u else None


def task_dict(t, role=None, uid=None):
    data = {
        "id": t.id,
        "title": t.title,
        "description": t.description or "",
        "status": t.status,
        "priority": t.priority,
        "board_id": t.board_id,
        "assigned_to": t.assigned_to,
        "created_by": t.created_by,
        "created_at": iso(t.created_at),
        "updated_at": iso(t.updated_at),
        # extras used by the Kanban UI
        "code": f"TSK-{t.id:03d}",
        "deadline": t.deadline.date().isoformat() if t.deadline else None,
        "comment_count": len(t.comments),
    }
    if role is not None:
        data["permissions"] = {
            "edit": guards.can_edit_task(role, t, uid),
            "status": guards.can_change_status(role, t, uid),
            "reassign": guards.can_reassign_task(role, t, uid),
            "delete": guards.can_delete_task(role),
        }
    return data


def comment_dict(c):
    return {
        "id": c.id,
        "task_id": c.task_id,
        "user_id": c.user_id,
        "content": c.content,
        "created_at": iso(c.created_at),
        "updated_at": iso(c.updated_at),
        "author": user_dict(c.author),
    }


def board_summary_dict(b, role=None):
    data = {
        "id": b.id,
        "name": b.name,
        "description": b.description or "",
        "created_at": iso(b.created_at),
        "updated_at": iso(b.updated_at),
        "task_count": len(b.tasks),
        "member_count": len(b.members),
    }
    if role is not None:
        data["role"] = role
    return data


def member_dict(m):
    return {
        "id": m.id,
        "user_id": m.user_id,
        "username": m.user.username if m.user else None,
        "email": m.user.email if m.user else None,
        "board_id": m.board_id,
        "role": m.role,
        "joined_at": iso(m.joined_at),
    }

