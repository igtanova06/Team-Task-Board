"""Endpoints for Board CRUD and Board Membership management.

  GET    /api/boards                       list boards the current user belongs to
  POST   /api/boards                       create board (creator becomes owner)
  GET    /api/boards/<id>                  board details, current role, members
  PATCH  /api/boards/<id>                  update board name / description (owner only)
  PUT    /api/boards/<id>                  update board name / description (owner only)
  DELETE /api/boards/<id>                  delete board and cascade all children (owner only)
  POST   /api/boards/<id>/members          add member to board (owner only)
  PATCH  /api/boards/<id>/members/<uid>    update member role (owner only, protects sole owner)
  PUT    /api/boards/<id>/members/<uid>    update member role (owner only, protects sole owner)
  DELETE /api/boards/<id>/members/<uid>    remove member or leave board (owner or self, protects sole owner)
"""
from flask import jsonify
from flask_login import current_user

from app.api import api
from app.api.forms import BoardForm, AddMemberForm, UpdateMemberRoleForm
from app.api.guards import (
    ApiError, board_context, json_body, require,
    can_manage_board, can_manage_members, can_remove_member,
    is_board_member, can_create_task,
)
from app.api.serializers import board_summary_dict, member_dict, user_dict
from app.extensions import db
from app.models import User, Board, BoardMembership, Role, Task


@api.get("/boards")
def list_my_boards():
    """Return all boards the authenticated user is a member of."""
    memberships = (
        BoardMembership.query.filter_by(user_id=current_user.id)
        .order_by(BoardMembership.id)
        .all()
    )
    return jsonify([board_summary_dict(m.board, role=m.role) for m in memberships]), 200


@api.post("/boards")
def create_board():
    """Create a new board; authenticated user is automatically set as owner."""
    data = json_body()
    form = BoardForm.from_json(data)
    if not form.validate():
        raise ApiError(400, "Invalid board data.", form.errors)

    board = Board(
        name=form.name.data,
        description=(form.description.data or "").strip() or None,
    )
    db.session.add(board)
    db.session.flush()

    membership = BoardMembership(
        board_id=board.id,
        user_id=current_user.id,
        role=Role.OWNER,
    )
    db.session.add(membership)
    db.session.commit()

    return jsonify(board_summary_dict(board, role=Role.OWNER)), 201


@api.get("/boards/<int:board_id>")
def get_board(board_id):
    """Board info, user role, and member list (used for UI bootstrap and detail)."""
    board, role = board_context(board_id)
    members = (
        BoardMembership.query.filter_by(board_id=board_id)
        .order_by(BoardMembership.id)
        .all()
    )
    return jsonify({
        "board": {"id": board.id, "name": board.name, "description": board.description or ""},
        "role": role,
        "me": user_dict(current_user),
        "can_create": can_create_task(role),
        "members": [{**user_dict(m.user), "email": m.user.email, "role": m.role} for m in members],
    }), 200


@api.route("/boards/<int:board_id>", methods=["PATCH", "PUT"])
def update_board(board_id):
    """Update board name or description (owner only)."""
    board, role = board_context(board_id)
    require(can_manage_board(role), "Only the board owner can update board details.")

    data = json_body()
    merged = {
        "name": data.get("name", board.name),
        "description": data.get("description", board.description or ""),
    }
    form = BoardForm.from_json(merged)
    if not form.validate():
        raise ApiError(400, "Invalid board data.", form.errors)

    board.name = form.name.data
    board.description = (form.description.data or "").strip() or None
    db.session.commit()

    return jsonify(board_summary_dict(board, role=role)), 200


@api.delete("/boards/<int:board_id>")
def delete_board(board_id):
    """Delete a board; cascades to tasks, memberships, and comments (owner only)."""
    board, role = board_context(board_id)
    require(can_manage_board(role), "Only the board owner can delete this board.")

    db.session.delete(board)
    db.session.commit()
    return "", 204


@api.post("/boards/<int:board_id>/members")
def add_member(board_id):
    """Add a user to the board with a specified role (owner only)."""
    board, role = board_context(board_id)
    require(can_manage_members(role), "Only the board owner can add members.")

    data = json_body()
    form = AddMemberForm.from_json(data)
    if not form.validate():
        raise ApiError(400, "Invalid member data.", form.errors)

    target_user = None
    if form.user_id.data:
        target_user = db.session.get(User, form.user_id.data)
    elif form.identity.data:
        from sqlalchemy import func
        ident = form.identity.data.strip().lower()
        target_user = User.query.filter(
            (func.lower(User.username) == ident) | (func.lower(User.email) == ident)
        ).first()

    if target_user is None:
        raise ApiError(404, "User not found.")

    if is_board_member(board_id, target_user.id):
        raise ApiError(400, "User is already a member of this board.")

    membership = BoardMembership(
        board_id=board_id,
        user_id=target_user.id,
        role=form.role.data,
    )
    db.session.add(membership)
    db.session.commit()

    return jsonify(member_dict(membership)), 201


@api.route("/boards/<int:board_id>/members/<int:user_id>", methods=["PATCH", "PUT"])
def update_member_role(board_id, user_id):
    """Update a member's role (owner only, protects sole owner)."""
    board, role = board_context(board_id)
    require(can_manage_members(role), "Only the board owner can update member roles.")

    data = json_body()
    form = UpdateMemberRoleForm.from_json(data)
    if not form.validate():
        raise ApiError(400, "Invalid role data.", form.errors)

    membership = BoardMembership.query.filter_by(board_id=board_id, user_id=user_id).first()
    if membership is None:
        raise ApiError(404, "Member not found on this board.")

    # Guard: Sole owner cannot be demoted
    if membership.role == Role.OWNER and form.role.data != Role.OWNER:
        if board.owner_count() <= 1:
            raise ApiError(400, "Cannot demote the sole owner of the board.")

    membership.role = form.role.data
    db.session.commit()

    return jsonify(member_dict(membership)), 200


@api.delete("/boards/<int:board_id>/members/<int:user_id>")
def remove_member(board_id, user_id):
    """Remove a member from the board or leave board (owner or self, protects sole owner)."""
    board, role = board_context(board_id)
    require(
        can_remove_member(role, user_id, current_user.id),
        "You do not have permission to remove this member.",
    )

    membership = BoardMembership.query.filter_by(board_id=board_id, user_id=user_id).first()
    if membership is None:
        raise ApiError(404, "Member not found on this board.")

    # Guard: Sole owner cannot leave or be removed
    if membership.role == Role.OWNER and board.owner_count() <= 1:
        raise ApiError(400, "The sole owner cannot leave or be removed from the board.")

    # Explicitly unassign any tasks assigned to this user on this board
    Task.query.filter_by(board_id=board_id, assigned_to=user_id).update(
        {Task.assigned_to: None}, synchronize_session="fetch"
    )

    db.session.delete(membership)
    db.session.commit()
    return "", 204
