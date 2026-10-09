from app.extensions import db
from app.models.user import utcnow


class Role:
    OWNER = "owner"
    MEMBER = "member"
    VIEWER = "viewer"
    ALL = (OWNER, MEMBER, VIEWER)


class BoardMembership(db.Model):
    # User <-> Board has Many-to-Many relationship
    __tablename__ = "board_memberships"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    board_id = db.Column(db.Integer, db.ForeignKey("boards.id", ondelete="CASCADE"), nullable=False)
    role = db.Column(db.String(20), nullable = False, default=Role.MEMBER)
    joined_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        # a user can join the same board only once
        db.UniqueConstraint("user_id", "board_id", name="uq_user_board"),
        db.CheckConstraint("role IN ('owner', 'member', 'viewer')", name="ck_membership_role")
    )

    user = db.relationship(
        "User",
        backref = db.backref("memberships", cascade="all, delete-orphan"),
    )
    board = db.relationship(
        "Board",
        backref = db.backref("memberships", cascade="all, delete-orphan")
    )

    def __repr__(self):
        return f"<Membership user={self.user_id} board={self.board_id} role={self.role}>"



