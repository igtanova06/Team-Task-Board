import os
from dotenv import load_dotenv


load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "my-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class DevelopmentConfig(Config):
    DEBUG =True


class TestingConfig(Config):
    TESTING = True
        # In-memory SQLite for fast testing without touching the real SQL Server
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig
}