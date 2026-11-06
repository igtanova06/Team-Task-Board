"""Authentication, authorization and request helpers for the /api blueprint.

Rules come from docs/business_rules.md (section 1) and docs/api_contract.md:
  * no active BoardMembership  -> 404 (access concealed)
  * membership but not enough rights -> 403
  * viewer: read-only, but may comment
  * member: edit / change status only when creator or assignee, reassign only when creator
  * owner: everything, and the only role that can delete a task

Authentication today = the Flask-Login session cookie used by the web UI.
Member 2 (JWT): accept a Bearer token inside `authenticated_user()` below and nothing else
in /api needs to change.
"""
from datetime import datetime, timezone

from flask import request
from flask_login import current_user

from app.api import api
from app.extensions import db
from app.models import Board, BoardMembership, Role, Task


class ApiError(Exception):
    """Raised anywhere in /api; rendered as {"detail": ..., "errors": {...}} by app.main.setup."""

    def __init__(self, status, detail, errors=None):
        super().__init__(detail)
        self.status, self.detail, self.errors = status, detail, errors


# ------------------------------------------------------------------ authentication
def authenticated_user():
    """Return the logged-in user or None. (Extension point for Bearer JWT.)"""
    if current_user and current_user.is_authenticated:
        return current_user
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        try:
            from flask_jwt_extended import decode_token
            decoded = decode_token(token)
            uid = decoded.get("sub")
            if uid is not None:
                from app.models import User
                u = db.session.get(User, int(uid))
                if u:
                    from flask_login import login_user
                    login_user(u)
                    return u
        except Exception:
            return None
    return None


@api.before_request
def _require_authentication():
    if authenticated_user() is None:
        raise ApiError(401, "Authentication required.")


# ------------------------------------------------------------------ request body
def json_body():
    if not request.is_json:
        raise ApiError(415, "Content-Type must be application/json.")
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "JSON object required.")
    return data


# ------------------------------------------------------------------ concurrency token
def _to_naive_utc(value):
    if isinstance(value, str):
        text = value.strip()
        if text.endswith(("Z", "z")):
            text = text[:-1] + "+00:00"
        try:
            value = datetime.fromisoformat(text)
        except ValueError:
            return None
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.replace(microsecond=(value.microsecond // 1000) * 1000)  # millisecond precision


def parse_token(value):
    """Parse the `updated_at` the client last read. None when missing or not ISO 8601."""
    return _to_naive_utc(value) if isinstance(value, str) and value.strip() else None


def check_fresh(task, token):
    if _to_naive_utc(task.updated_at) != token:
        raise ApiError(409, "Task was modified by another user. Reload latest data.")


# ------------------------------------------------------------------ membership + permissions
def board_context(board_id):
    board = db.session.get(Board, board_id)
    m = (BoardMembership.query.filter_by(user_id=current_user.id, board_id=board_id).first()
         if board else None)
    if board is None or m is None:
        raise ApiError(404, "Board not found.")
    return board, m.role


def task_context(task_id):
    task = db.session.get(Task, task_id)
    m = (BoardMembership.query.filter_by(user_id=current_user.id, board_id=task.board_id).first()
         if task else None)
    if task is None or m is None:
        raise ApiError(404, "Task not found.")
    return task, m.role


def _is_involved(task, uid):
    return task.created_by == uid or task.assigned_to == uid


def can_create_task(role):
    return role in (Role.OWNER, Role.MEMBER)


def can_edit_task(role, task, uid):
    return role == Role.OWNER or (role == Role.MEMBER and _is_involved(task, uid))


can_change_status = can_edit_task


def can_reassign_task(role, task, uid):
    return role == Role.OWNER or (role == Role.MEMBER and task.created_by == uid)


def can_delete_task(role):
    return role == Role.OWNER


def can_manage_board(role):
    return role == Role.OWNER


def can_manage_members(role):
    return role == Role.OWNER


def can_remove_member(role, target_uid, current_uid):
    return role == Role.OWNER or target_uid == current_uid


def require(allowed, message="You do not have permission to do that."):
    if not allowed:
        raise ApiError(403, message)


def is_board_member(board_id, user_id):
    return BoardMembership.query.filter_by(board_id=board_id, user_id=user_id).first() is not None



