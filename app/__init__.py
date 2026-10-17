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

    return app