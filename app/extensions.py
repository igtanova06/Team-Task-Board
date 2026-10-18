from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate


db=SQLAlchemy()
migrate = Migrate()

# Member 2: Authentication extensions
from flask_jwt_extended import JWTManager
from app.main.setup import login_manager

jwt = JWTManager()
