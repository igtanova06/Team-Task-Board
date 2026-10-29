import os
from flask import Flask
from config import config_by_name
from app.extensions import db, migrate


def create_app(config_name=None):
    if not config_name:
        config_name = os.environ.get("FLASK_CONFIG") or "development"
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    from app.main.setup import apply_defaults, init_web
    apply_defaults(app)

    db.init_app(app)
    migrate.init_app(app, db)

    from app import models
    from app.api import api
    app.register_blueprint(api, url_prefix="/api")

    init_web(app)   # web UI: session login, CSRF, pages, error handlers

    # Member 2: JWT & Auth blueprint
    app.config.setdefault("JWT_SECRET_KEY", app.config.get("SECRET_KEY"))
    from app.extensions import jwt
    jwt.init_app(app)

    from app.auth import auth as auth_bp
    app.register_blueprint(auth_bp)

    # Member 2 - Tieu chi 6: RBAC demo routes (prefix /m2/api)
    from app.auth.member2_routes import m2_api
    app.register_blueprint(m2_api, url_prefix='/m2/api')

    return app


