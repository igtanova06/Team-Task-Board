import os
from dotenv import load_dotenv


load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "my-secret-key")
    # SQL Server in production (see HUONG_DAN_TEST_DB.txt). Falls back to a local SQLite
    # file only when DATABASE_URL is not set, so the UI can be tried without SQL Server.
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///dev.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class DevelopmentConfig(Config):
    DEBUG =True


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
        # In-memory SQLite for fast testing without touching the real SQL Server
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig
}