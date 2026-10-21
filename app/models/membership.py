from app.extensions import db
from app.models.user import utcnow


class Role:
    """Board membership roles defining authorization boundaries."""
    OWNER = "owner"
    MEMBER = "member"
    VIEWER = "viewer"
    ALL = (OWNER, MEMBER, VIEWER)


class BoardMembership(db.Model):
    """Associates users with boards and stores board-level roles (Many-to-Many)."""
    __tablename__ = "board_memberships"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    board_id = db.Column(db.Integer, db.ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False, default=Role.MEMBER)
    joined_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        # Ensure a user cannot join the same board multiple times
        db.UniqueConstraint("user_id", "board_id", name="uq_user_board"),
        # Enforce valid role enum values at the database level
        db.CheckConstraint("role IN ('owner', 'member', 'viewer')", name="ck_membership_role"),
    )

    user = db.relationship(
        "User",
        backref=db.backref("memberships", cascade="all, delete-orphan"),
    )
    board = db.relationship(
        "Board",
        backref=db.backref("memberships", cascade="all, delete-orphan"),
    )

    def to_dict(self):
        """Serialize membership information with associated user details."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else None,
            "email": self.user.email if self.user else None,
            "board_id": self.board_id,
            "role": self.role,
            "joined_at": self.joined_at.isoformat() + "Z" if self.joined_at else None,
        }

    def __repr__(self):
        return f"<Membership user={self.user_id} board={self.board_id} role={self.role}>"




