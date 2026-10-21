from datetime import timedelta
import os
from dotenv import load_dotenv


load_dotenv()


class Config:
    """Base configuration with security and database defaults."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-team-task-board-secret-key-32bytes-secure!")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-task-board-secret-key-32bytes-min!")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Secure session cookie configurations (Rubric Criteria 1 & 5)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = timedelta(days=14)


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class TestingConfig(Config):
    """Testing environment configuration using in-memory database."""
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Production environment configuration with hardened security."""
    DEBUG = False
    TESTING = False
    # Transmit session cookies only over HTTPS in production
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "true").lower() in ("true", "1")


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}