from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


def utcnow():
    """Return current UTC datetime with tzinfo stripped for database storage."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(UserMixin, db.Model):
    """User account entity storing credentials, profile data, and session identities."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def set_password(self, password):
        """Hash raw password before storing in the database."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify candidate raw password against the stored password hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """Serialize user public attributes for REST responses."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
        }

    def __repr__(self):
        return f"<User {self.username}>"