from urllib.parse import urlparse
from flask import render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from flask_jwt_extended import create_access_token
from sqlalchemy import or_, func

from app.auth import auth
from app.auth.forms import LoginForm, RegisterForm, ChangePasswordForm
from app.extensions import db
from app.models import User


def safe_next(target):
    if target and target.startswith("/") and not target.startswith("//") and not urlparse(target).netloc:
        return target
    return None


@auth.route("/register", methods=["GET", "POST"])
@auth.route("/auth/register", methods=["GET", "POST"])
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
        return redirect(url_for("auth.login"))

    return render_template("kanban/register.html", form=form), (422 if form.errors else 200)


@auth.route("/login", methods=["GET", "POST"])
@auth.route("/auth/login", methods=["GET", "POST"])
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

    # Browser Web Form submission (session cookie)
    form = LoginForm()
    if form.validate_on_submit():
        ident = form.identity.data.strip().lower()
        user = User.query.filter(
            or_(func.lower(User.email) == ident, func.lower(User.username) == ident)
        ).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            return redirect(safe_next(request.args.get("next")) or url_for("main.index"))
        # Same error message for unknown user / wrong password to avoid account enumeration
        form.password.errors.append("Incorrect email/username or password.")

    return render_template("kanban/login.html", form=form), (422 if form.errors else 200)


@auth.route("/logout", methods=["GET", "POST"])
@auth.route("/auth/logout", methods=["GET", "POST"])
def logout():
    if current_user.is_authenticated:
        logout_user()
        flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))


@auth.route("/change-password", methods=["GET", "POST"])
@auth.route("/auth/change-password", methods=["GET", "POST"])
def change_password():
    # Resolve user from session cookie or Bearer JWT token
    user = current_user if current_user.is_authenticated else None
    if not user and request.headers.get("Authorization", "").startswith("Bearer "):
        try:
            from flask_jwt_extended import decode_token
            decoded = decode_token(request.headers.get("Authorization").split(" ", 1)[1].strip())
            uid = decoded.get("sub")
            if uid is not None:
                user = db.session.get(User, int(uid))
                if user:
                    login_user(user)
        except Exception:
            pass

    if not user:
        if request.is_json:
            return jsonify(detail="Authentication required."), 401
        return redirect(url_for("auth.login", next=request.path))

    # JSON API client support
    if request.is_json:
        data = request.get_json(silent=True) or {}
        current_password = data.get("current_password") or ""
        new_password = data.get("new_password") or ""
        confirm_password = data.get("confirm_password") or new_password

        errors = {}
        if not current_password:
            errors["current_password"] = ["Current password is required."]
        elif not user.check_password(current_password):
            errors["current_password"] = ["Incorrect current password."]

        if not new_password or len(new_password) < 6:
            errors["new_password"] = ["New password must be at least 6 characters."]
        elif new_password == current_password:
            errors["new_password"] = ["New password must be different from current password."]

        if confirm_password != new_password:
            errors["confirm_password"] = ["New passwords must match."]

        if errors:
            return jsonify(detail="Validation failed.", errors=errors), 422

        user.set_password(new_password)
        db.session.commit()
        return jsonify(message="Password changed successfully."), 200

    # Browser Web Form submission (session cookie)
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not user.check_password(form.current_password.data):
            form.current_password.errors.append("Incorrect current password.")
            return render_template("kanban/change_password.html", form=form), 422

        if form.new_password.data == form.current_password.data:
            form.new_password.errors.append("New password must be different from current password.")
            return render_template("kanban/change_password.html", form=form), 422

        user.set_password(form.new_password.data)
        db.session.commit()

        # Require the user to re-authenticate with the new password
        logout_user()
        flash("Your password has been changed successfully! Please sign in with your new password.", "success")
        return redirect(url_for("auth.login"))

    return render_template("kanban/change_password.html", form=form), (422 if form.errors else 200)



