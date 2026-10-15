from flask import Flask, jsonify, render_template, request, redirect, url_for
from flask_wtf.csrf import CSRFError

from config import config_by_name
from app.extensions import db, migrate, login_manager, csrf


def create_app(config_name="development"):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    from app import models
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        # AJAX calls get JSON 401 (the JS redirects to /login); pages get a redirect.
        if request.path.startswith("/api/"):
            return jsonify(error="Authentication required."), 401
        return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))

    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.pages import bp as pages_bp
    from app.blueprints.api import bp as api_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp)

    # ---- error handlers: JSON for /api, friendly page otherwise ----
    def wants_json():
        return request.path.startswith("/api/")

    @app.errorhandler(CSRFError)
    def csrf_error(err):
        if wants_json():
            return jsonify(error="Session expired. Please reload the page."), 400
        return render_template("error.html", code=400, message="Your session expired. Please reload and try again."), 400

    for code, msg in ((403, "You do not have permission to do that."),
                      (404, "Not found."),
                      (405, "Method not allowed."),
                      (500, "Something went wrong on our side.")):
        def handler(err, code=code, msg=msg):
            if code == 500:
                db.session.rollback()
            if wants_json():
                return jsonify(error=msg), code
            return render_template("error.html", code=code, message=msg), code
        app.register_error_handler(code, handler)

    return app
