from urllib.parse import urlparse
from flask import render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from flask_jwt_extended import create_access_token
from sqlalchemy import or_, func

from app.auth import auth
from app.auth.forms import LoginForm, RegisterForm
from app.extensions import db
from app.models import User


def safe_next(target):
    if target and target.startswith("/") and not target.startswith("//") and not urlparse(target).netloc:
        return target
    return None


@auth.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    # JSON API client support (Bearer token / REST clients)
    if request.is_json:
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        errors = {}
        if not username or len(username) < 3 or len(username) > 50:
            errors["username"] = ["Username must be between 3 and 50 characters."]
        if not email or "@" not in email:
            errors["email"] = ["Valid email address is required."]
        if not password or len(password) < 6:
            errors["password"] = ["Password must be at least 6 characters."]

        if errors:
            return jsonify(detail="Validation failed.", errors=errors), 400

        existing = User.query.filter(
            or_(func.lower(User.username) == username.lower(), func.lower(User.email) == email)
        ).first()
        if existing:
            field = "username" if existing.username.lower() == username.lower() else "email"
            return jsonify(detail="User with this " + field + " already exists."), 409

        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        token = create_access_token(identity=str(new_user.id))
        return jsonify(
            message="User registered successfully.",
            access_token=token,
            token_type="Bearer",
            user={"id": new_user.id, "username": new_user.username, "email": new_user.email}
        ), 201

    # Browser Web Form submission
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip().lower()

        existing = User.query.filter(
            or_(func.lower(User.username) == username.lower(), func.lower(User.email) == email)
        ).first()
        if existing:
            if existing.username.lower() == username.lower():
                form.username.errors.append("Username is already taken.")
            if existing.email.lower() == email:
                form.email.errors.append("Email is already registered.")
            return render_template("kanban/register.html", form=form), 422

        new_user = User(username=username, email=email)
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully! Please sign in with your new credentials.", "success")
        return redirect(url_for("web_auth.login"))

    return render_template("kanban/register.html", form=form), (422 if form.errors else 200)


@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    # JSON API client support (returns JWT access_token)
    if request.is_json:
        data = request.get_json(silent=True) or {}
        ident = (data.get("identity") or data.get("email") or data.get("username") or "").strip().lower()
        password = data.get("password") or ""

        if not ident or not password:
            return jsonify(detail="Identity (email/username) and password are required."), 400

        user = User.query.filter(
            or_(func.lower(User.email) == ident, func.lower(User.username) == ident)
        ).first()

        if user and user.check_password(password):
            token = create_access_token(identity=str(user.id))
            return jsonify(
                access_token=token,
                token_type="Bearer",
                user={"id": user.id, "username": user.username, "email": user.email}
            ), 200

        return jsonify(detail="Incorrect email/username or password."), 401

    # Browser GET/POST fallback redirects to or uses web_auth
    return redirect(url_for("web_auth.login"))


@auth.route("/logout", methods=["GET", "POST"])
def logout():
    if current_user.is_authenticated:
        logout_user()
        flash("You have been signed out.", "info")
    return redirect(url_for("web_auth.login"))
