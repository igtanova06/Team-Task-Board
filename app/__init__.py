from flask import Flask
from config import config_by_name
from app.extensions import db, migrate


def create_app(config_name="development"):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    from app.main.setup import apply_defaults, init_web
    apply_defaults(app)

    db.init_app(app)
    migrate.init_app(app, db)

    from app import models
    from app.api import api
    app.register_blueprint(api, url_prefix="/api")

    init_web(app)   # web UI: session login, CSRF, pages, error handlers (app/main, app/auth/web.py)

    # Member 2: JWT & Auth blueprint
    app.config.setdefault("JWT_SECRET_KEY", app.config.get("SECRET_KEY", "jwt-secret-key"))
    from app.extensions import jwt
    jwt.init_app(app)

    from app.auth import auth as auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")

    @app.route("/register", methods=["GET", "POST"])
    def root_register():
        from app.auth.routes import register
        return register()

    return app
