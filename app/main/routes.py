"""HTML pages of the Kanban UI. All data is loaded by the browser from /api (AJAX)."""
from flask import render_template, redirect, url_for, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.main import main
from app.models import Board, BoardMembership


@main.get("/")
@login_required
def index():
    return redirect(url_for("main.boards"))


@main.get("/boards")
@login_required
def boards():
    """Board list page. The list itself is loaded by the browser from GET /api/boards."""
    return render_template("kanban/boards.html")


@main.get("/boards/<int:board_id>")
@login_required
def board(board_id):
    board = db.session.get(Board, board_id)
    m = BoardMembership.query.filter_by(user_id=current_user.id, board_id=board_id).first()
    if board is None or m is None:
        abort(404)                      # same answer for "missing" and "not a member"
    return render_template("kanban/board.html", board=board, role=m.role)
