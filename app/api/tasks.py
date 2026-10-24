"""Endpoints the Kanban UI needs beyond the three in docs/api_contract.md (section 3).

  GET    /api/boards/<id>        board info, my role, members            (UI bootstrap)
  POST   /api/boards/<id>/tasks  create task
  GET    /api/tasks/<id>         task + comments
  PATCH  /api/tasks/<id>         edit task (partial; optional updated_at => 409 on stale data)
  DELETE /api/tasks/<id>         delete task (owner only)
"""
from datetime import datetime

from flask import jsonify
from flask_login import current_user

from app.api import api
from app.api.guards import (
    ApiError, board_context, task_context, json_body, parse_token, check_fresh, require,
    can_create_task, can_edit_task, can_reassign_task, can_delete_task, is_board_member,
)
from app.api.serializers import task_dict, comment_dict, user_dict
from app.api.task_forms import TaskForm
from app.extensions import db
from app.models import BoardMembership, Task

TASK_FIELDS = ("title", "description", "status", "priority", "deadline", "assigned_to")


def _validate(data, board_id):
    form = TaskForm.from_json(data)
    errors = dict(form.errors) if not form.validate() else {}
    uid = form.assigned_to.data
    if "assigned_to" not in errors and uid is not None and not is_board_member(board_id, uid):
        errors["assigned_to"] = ["Assignee must be an active member of this board."]
    if errors:
        raise ApiError(400, "Please fix the highlighted fields.", errors)
    return form


def _deadline(d):
    return datetime(d.year, d.month, d.day) if d else None


@api.post("/boards/<int:board_id>/tasks")
def create_task(board_id):
    _, role = board_context(board_id)
    data = json_body()
    require(can_create_task(role), "Viewers cannot create tasks.")
    form = _validate({"status": "todo", "priority": "medium", **data}, board_id)
    task = Task(
        title=form.title.data, description=(form.description.data or "").strip() or None,
        status=form.status.data, priority=form.priority.data, deadline=_deadline(form.deadline.data),
        assigned_to=form.assigned_to.data, board_id=board_id, created_by=current_user.id,
    )
    db.session.add(task)
    db.session.commit()
    return jsonify(task_dict(task, role, current_user.id)), 201


@api.get("/tasks/<int:task_id>")
def get_task(task_id):
    task, role = task_context(task_id)
    body = task_dict(task, role, current_user.id)
    body["comments"] = [comment_dict(c) for c in task.comments]
    return jsonify(body)


@api.patch("/tasks/<int:task_id>")
def update_task(task_id):
    task, role = task_context(task_id)
    data = json_body()
    require(can_edit_task(role, task, current_user.id),
            "Only the owner, or a member who created or is assigned to the task, can edit it.")

    merged = {
        "title": task.title, "description": task.description or "", "status": task.status,
        "priority": task.priority, "assigned_to": task.assigned_to,
        "deadline": task.deadline.date().isoformat() if task.deadline else "",
    }
    merged.update({k: v for k, v in data.items() if k in TASK_FIELDS})
    form = _validate(merged, task.board_id)

    if "updated_at" in data:
        token = parse_token(data["updated_at"])
        if token is None:
            raise ApiError(400, "updated_at must be an ISO 8601 timestamp.")
        check_fresh(task, token)
    if form.assigned_to.data != task.assigned_to:
        require(can_reassign_task(role, task, current_user.id),
                "Only the owner, or the member who created the task, can reassign it.")

    task.title = form.title.data
    task.description = (form.description.data or "").strip() or None
    task.status, task.priority = form.status.data, form.priority.data
    task.deadline, task.assigned_to = _deadline(form.deadline.data), form.assigned_to.data
    db.session.commit()
    return jsonify(task_dict(task, role, current_user.id))


@api.delete("/tasks/<int:task_id>")
def delete_task(task_id):
    task, role = task_context(task_id)
    require(can_delete_task(role), "Only the board owner can delete tasks.")
    db.session.delete(task)
    db.session.commit()
    return "", 204
