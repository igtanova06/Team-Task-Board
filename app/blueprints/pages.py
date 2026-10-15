from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

from app.models import BoardMembership
from app.permissions import board_or_403

bp = Blueprint("pages", __name__)


@bp.get("/")
@login_required
def index():
    m = (BoardMembership.query.filter_by(user_id=current_user.id)
         .order_by(BoardMembership.id).first())
    if m is None:
        return render_template("no_board.html")
    return redirect(url_for("pages.board", board_id=m.board_id))


@bp.get("/boards/<int:board_id>")
@login_required
def board(board_id):
    board, role = board_or_403(board_id)
    return render_template("board.html", board=board, role=role)
