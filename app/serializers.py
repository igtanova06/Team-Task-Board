def iso_date(dt):
    return dt.date().isoformat() if dt else None


def user_dict(u):
    return {"id": u.id, "username": u.username} if u else None


def task_dict(t):
    return {
        "id": t.id,
        "code": f"TSK-{t.id:03d}",
        "title": t.title,
        "description": t.description or "",
        "status": t.status,
        "priority": t.priority,
        "deadline": iso_date(t.deadline),
        "board_id": t.board_id,
        "assigned_to": t.assigned_to,
        "assignee": user_dict(t.assignee),
        "created_by": t.created_by,
        "comment_count": len(t.comments),
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


def comment_dict(c):
    return {
        "id": c.id,
        "content": c.content,
        "author": user_dict(c.author),
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }
