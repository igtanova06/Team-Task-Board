from urllib.parse import urlparse

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, current_user, login_required
from sqlalchemy import or_, func

from app.forms import LoginForm
from app.models import User

bp = Blueprint("auth", __name__)


def safe_next(target):
    """Only allow same-site relative redirects (prevents open redirect)."""
    if target and target.startswith("/") and not target.startswith("//") and not urlparse(target).netloc:
        return target
    return None


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("pages.index"))
    form = LoginForm()
    if form.validate_on_submit():
        ident = form.identity.data.strip().lower()
        user = User.query.filter(or_(func.lower(User.email) == ident, func.lower(User.username) == ident)).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            return redirect(safe_next(request.args.get("next")) or url_for("pages.index"))
        # Same message for unknown user / wrong password: do not reveal which accounts exist.
        form.password.errors.append("Incorrect email/username or password.")
    return render_template("login.html", form=form), (422 if form.errors else 200)


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))
