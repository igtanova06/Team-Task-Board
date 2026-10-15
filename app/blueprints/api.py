"""JSON API used by the Kanban UI (fetch / AJAX).

  GET    /api/boards/<id>              board + role + members + tasks
  POST   /api/boards/<id>/tasks        create task
  GET    /api/tasks/<id>               task + comments
  PUT    /api/tasks/<id>               update task (partial updates allowed)
  PATCH  /api/tasks/<id>/status        move task (drag & drop)
  DELETE /api/tasks/<id>               delete task
  POST   /api/tasks/<id>/comments      add comment

Errors: {"error": "...", "errors": {field: [messages]}}  with 400/401/403/404/422.
"""
from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.forms import TaskForm, StatusForm, CommentForm
from app.models import BoardMembership, Role, Task, Comment
from app.permissions import board_or_403, task_or_403, can_edit, can_delete_task
from app.serializers import task_dict, comment_dict, user_dict

bp = Blueprint("api", __name__, url_prefix="/api")

TASK_FIELDS = ("title", "description", "status", "priority", "deadline", "assigned_to")


@bp.before_request
@login_required
def _require_login():
    pass


def error(message, status, errors=None):
    body = {"error": message}
    if errors:
        body["errors"] = errors
    return jsonify(body), status


def json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def validation_error(form):
    return error("Please fix the highlighted fields.", 422, form.errors)


def check_assignee(form, board_id):
    """Assignee must be an owner/member of this board (viewers cannot hold tasks)."""
    uid = form.assigned_to.data
    if uid is None:
        return True
    m = BoardMembership.query.filter_by(user_id=uid, board_id=board_id).first()
    if m is None or m.role == Role.VIEWER:
        form.assigned_to.errors.append("Assignee must be an editor of this board.")
        return False
    return True


def deadline_value(d):
    return datetime(d.year, d.month, d.day) if d else None


# ---------------------------------------------------------------- board
@bp.get("/boards/<int:board_id>")
def get_board(board_id):
    board, role = board_or_403(board_id)
    tasks = (Task.query.filter_by(board_id=board_id)
             .options(selectinload(Task.comments), selectinload(Task.assignee))
             .order_by(Task.created_at, Task.id).all())
    members = (BoardMembership.query.filter_by(board_id=board_id)
               .order_by(BoardMembership.id).all())
    return jsonify(
        board={"id": board.id, "name": board.name, "description": board.description or ""},
        role=role,
        permissions={"edit": can_edit(role), "delete_any": role == Role.OWNER},
        me=user_dict(current_user),
        members=[{**user_dict(m.user), "role": m.role} for m in members],
        tasks=[task_dict(t) for t in tasks],
    )


# ---------------------------------------------------------------- tasks
@bp.post("/boards/<int:board_id>/tasks")
def create_task(board_id):
    board_or_403(board_id, write=True)
    data = json_body()
    if data is None:
        return error("Request body must be a JSON object.", 400)
    form = TaskForm.from_json({"status": "todo", "priority": "medium", **data})
    if not (form.validate() and check_assignee(form, board_id)):
        return validation_error(form)
    task = Task(
        title=form.title.data, description=(form.description.data or "").strip() or None,
        status=form.status.data, priority=form.priority.data,
        deadline=deadline_value(form.deadline.data), assigned_to=form.assigned_to.data,
        board_id=board_id, created_by=current_user.id,
    )
    db.session.add(task)
    db.session.commit()
    return jsonify(task=task_dict(task)), 201


@bp.get("/tasks/<int:task_id>")
def get_task(task_id):
    task, role = task_or_403(task_id)
    return jsonify(
        task=task_dict(task),
        comments=[comment_dict(c) for c in task.comments],
        permissions={"edit": can_edit(role), "delete": can_delete_task(role, task)},
    )


@bp.route("/tasks/<int:task_id>", methods=["PUT", "PATCH"])
def update_task(task_id):
    task, _ = task_or_403(task_id, write=True)
    data = json_body()
    if data is None:
        return error("Request body must be a JSON object.", 400)
    current = {
        "title": task.title, "description": task.description or "", "status": task.status,
        "priority": task.priority, "deadline": task.deadline.date().isoformat() if task.deadline else "",
        "assigned_to": task.assigned_to,
    }
    current.update({k: v for k, v in data.items() if k in TASK_FIELDS})
    form = TaskForm.from_json(current)
    if not (form.validate() and check_assignee(form, task.board_id)):
        return validation_error(form)
    task.title = form.title.data
    task.description = (form.description.data or "").strip() or None
    task.status = form.status.data
    task.priority = form.priority.data
    task.deadline = deadline_value(form.deadline.data)
    task.assigned_to = form.assigned_to.data
    db.session.commit()
    return jsonify(task=task_dict(task))


@bp.patch("/tasks/<int:task_id>/status")
def update_status(task_id):
    task, _ = task_or_403(task_id, write=True)
    data = json_body()
    if data is None:
        return error("Request body must be a JSON object.", 400)
    form = StatusForm.from_json(data)
    if not form.validate():
        return error("Invalid status.", 422, form.errors)
    task.status = form.status.data
    db.session.commit()
    return jsonify(task=task_dict(task))


@bp.delete("/tasks/<int:task_id>")
def delete_task(task_id):
    task, role = task_or_403(task_id, write=True)
    if not can_delete_task(role, task):
        return error("Only the board owner or the task's creator can delete it.", 403)
    db.session.delete(task)
    db.session.commit()
    return "", 204


# ---------------------------------------------------------------- comments
@bp.post("/tasks/<int:task_id>/comments")
def add_comment(task_id):
    task, _ = task_or_403(task_id, write=True)
    data = json_body()
    if data is None:
        return error("Request body must be a JSON object.", 400)
    form = CommentForm.from_json(data)
    if not form.validate():
        return validation_error(form)
    comment = Comment(content=form.content.data, task_id=task.id, user_id=current_user.id)
    db.session.add(comment)
    db.session.commit()
    return jsonify(comment=comment_dict(comment)), 201
