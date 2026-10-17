"""Wires the web UI into the Flask app: session login, CSRF, error pages, JSON errors for /api.

create_app() only needs two calls:  apply_defaults(app)  before db.init_app,  init_web(app)  after.
"""
from flask import jsonify, render_template, request, redirect, url_for
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect, CSRFError
from werkzeug.exceptions import HTTPException

login_manager = LoginManager()
csrf = CSRFProtect()

UNSAFE = ("POST", "PUT", "PATCH", "DELETE")


def apply_defaults(app):
    """Local fallbacks so a fresh clone runs without extra config."""
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///dev.db"     # -> instance/dev.db
        app.config["USING_SQLITE_FALLBACK"] = True
    if app.config.get("TESTING"):
        app.config.setdefault("WTF_CSRF_ENABLED", False)
    app.config["WTF_CSRF_CHECK_DEFAULT"] = False                       # we call csrf.protect() ourselves


def _wants_json():
    return request.path.startswith("/api/")


def init_web(app):
    from app.models import User
    from app.api.guards import ApiError
    from app.auth.web import web_auth
    from app.main import main

    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "web_auth.login"

    @login_manager.user_loader
    def load_user(user_id):
        from app.extensions import db
        return db.session.get(User, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        return redirect(url_for("web_auth.login", next=request.full_path.rstrip("?")))

    app.register_blueprint(web_auth)
    app.register_blueprint(main)

    @app.before_request
    def csrf_for_cookie_sessions():
        # Browser requests (session cookie) must carry the CSRF token. Requests that authenticate
        # with an `Authorization: Bearer ...` header (API clients / Member 2's JWT) are not cookie
        # based, so CSRF does not apply to them.
        if (request.method in UNSAFE and app.config.get("WTF_CSRF_ENABLED", True)
                and not request.headers.get("Authorization", "").startswith("Bearer ")):
            csrf.protect()

    # ---------------- errors: {"detail": ...} for /api, a friendly page otherwise
    @app.errorhandler(ApiError)
    def api_error(err):
        body = {"detail": err.detail}
        if err.errors:
            body["errors"] = err.errors
        return jsonify(body), err.status

    @app.errorhandler(CSRFError)
    def csrf_error(err):
        if _wants_json():
            return jsonify(detail="Session expired or invalid CSRF token. Reload the page."), 400
        return render_template("kanban/error.html", code=400, message="Your session expired. Reload and try again."), 400

    @app.errorhandler(HTTPException)
    def http_error(err):
        if _wants_json():
            return jsonify(detail=err.description), err.code
        return render_template("kanban/error.html", code=err.code, message=err.description), err.code

    @app.errorhandler(500)
    def server_error(err):
        from app.extensions import db
        db.session.rollback()
        if _wants_json():
            return jsonify(detail="Internal server error."), 500
        return render_template("kanban/error.html", code=500, message="Something went wrong on our side."), 500
