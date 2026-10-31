from flask import request, jsonify
from flask_login import current_user

from app.api import api
from app.api.guards import (
    board_context, task_context, json_body, parse_token, check_fresh, require,
    ApiError, can_change_status,
)
from app.api.serializers import task_dict, comment_dict, iso
from app.api.forms import StatusForm, CommentForm
from app.extensions import db
from app.models import Task, Comment
from app.models.task import TaskStatus


@api.get("/boards/<int:board_id>/tasks")
def get_board_tasks(board_id):
    _, role = board_context(board_id)
    tasks = Task.query.filter_by(board_id=board_id).order_by(Task.created_at, Task.id).all()
    return jsonify([task_dict(t, role, current_user.id) for t in tasks]), 200


@api.put("/tasks/<int:task_id>/status")
def update_status(task_id):
    task, role = task_context(task_id)
    data = json_body()
    require(can_change_status(role, task, current_user.id),
            "Only the owner, or a member who created or is assigned to the task, can change its status.")

    form = StatusForm.from_json(data)
    if not form.validate():
        raise ApiError(400, "Invalid task status", form.errors)

    token = parse_token(data.get("updated_at"))
    if token is None:
        raise ApiError(400, "updated_at (ISO 8601 timestamp last read by the client) is required.")
    check_fresh(task, token)

    task.status = form.status.data
    db.session.commit()
    return jsonify({"id": task.id, "status": task.status, "updated_at": iso(task.updated_at)}), 200


@api.post("/tasks/<int:task_id>/comments")
def add_comment(task_id):
    task, _ = task_context(task_id)          # any active member (owner / member / viewer) may comment
    data = json_body()
    form = CommentForm.from_json(data)
    if not form.validate():
        raise ApiError(400, "Comment content is required", form.errors)

    comment = Comment(content=form.content.data, task_id=task.id, user_id=current_user.id)
    db.session.add(comment)
    db.session.commit()
    return jsonify(comment_dict(comment)), 201


# Extra endpoints used by the Kanban UI (board info, create / edit / delete / detail)
from app.api import tasks  # noqa: E402,F401
