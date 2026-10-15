"""Role-based authorization for boards and tasks.

Roles (BoardMembership.role):
  owner  - everything, including deleting any task
  member - create / edit / move / comment; delete only tasks they created
  viewer - read-only
"""
from functools import wraps

from flask import abort
from flask_login import current_user

from app.extensions import db
from app.models import Board, BoardMembership, Role, Task

EDIT_ROLES = (Role.OWNER, Role.MEMBER)


def get_role(board_id):
    """Role of the current user on a board, or None when not a member."""
    m = BoardMembership.query.filter_by(user_id=current_user.id, board_id=board_id).first()
    return m.role if m else None


def can_edit(role):
    return role in EDIT_ROLES


def can_delete_task(role, task):
    return role == Role.OWNER or (role == Role.MEMBER and task.created_by == current_user.id)


def board_or_403(board_id, *, write=False):
    """Load a board for the current user. 404 if missing, 403 if no access / read-only."""
    board = db.session.get(Board, board_id)
    if board is None:
        abort(404)
    role = get_role(board_id)
    if role is None or (write and not can_edit(role)):
        abort(403)
    return board, role


def task_or_403(task_id, *, write=False):
    """Load a task, enforcing access to its board. Returns (task, role)."""
    task = db.session.get(Task, task_id)
    if task is None:
        abort(404)
    role = get_role(task.board_id)
    if role is None or (write and not can_edit(role)):
        abort(403)
    return task, role
