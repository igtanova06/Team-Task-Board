"""Browser sign-in (session cookie) for the web UI: GET/POST /login and POST /logout.

Kept in its own file (and blueprint `web_auth`) so it never collides with Member 2's JWT API
(`/api/auth/*`), which can live in app/auth/__init__.py + app/auth/routes.py.
"""
from urllib.parse import urlparse

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, current_user, login_required
from flask_wtf import FlaskForm
from sqlalchemy import or_, func
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Length

from app.models import User

web_auth = Blueprint("web_auth", __name__)


class LoginForm(FlaskForm):
    identity = StringField("Email or username", validators=[
        DataRequired(message="Enter your email or username."), Length(max=100)])
    password = PasswordField("Password", validators=[
        DataRequired(message="Enter your password."), Length(max=128)])
    remember = BooleanField("Keep me signed in")


def safe_next(target):
    """Only same-site relative redirects (prevents open redirect)."""
    if target and target.startswith("/") and not target.startswith("//") and not urlparse(target).netloc:
        return target
    return None


@web_auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = LoginForm()
    if form.validate_on_submit():
        ident = form.identity.data.strip().lower()
        user = User.query.filter(or_(func.lower(User.email) == ident, func.lower(User.username) == ident)).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            return redirect(safe_next(request.args.get("next")) or url_for("main.index"))
        # Same message for unknown user / wrong password: do not reveal which accounts exist.
        form.password.errors.append("Incorrect email/username or password.")
    return render_template("kanban/login.html", form=form), (422 if form.errors else 200)


@web_auth.post("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("web_auth.login"))
