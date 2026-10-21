from app.extensions import db
from app.models.membership import BoardMembership, Role
from app.models.user import utcnow


class Board(db.Model):
    """Board model representing a team workspace for tasks."""
    __tablename__ = "boards"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    # One-to-Many: Board -> Tasks (deleting a board cascades to its tasks)
    tasks = db.relationship(
        "Task",
        backref="board",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # Many-to-Many: Direct relationship between Board and User via board_memberships
    members = db.relationship(
        "User",
        secondary="board_memberships",
        backref=db.backref("boards", lazy="select"),
        viewonly=True,
    )

    def get_role(self, user_id):
        """Return the membership role for a given user ID, or None if not a member."""
        membership = BoardMembership.query.filter_by(board_id=self.id, user_id=user_id).first()
        return membership.role if membership else None

    def is_owner(self, user_id):
        """Check whether the given user ID is an owner of this board."""
        return self.get_role(user_id) == Role.OWNER

    def is_member(self, user_id):
        """Check whether the given user ID is an active member or owner of this board."""
        return self.get_role(user_id) in (Role.OWNER, Role.MEMBER)

    def has_access(self, user_id):
        """Check whether the given user ID has any access (owner, member, viewer) to this board."""
        return self.get_role(user_id) is not None

    def owner_count(self):
        """Count the current number of owners on this board."""
        return BoardMembership.query.filter_by(board_id=self.id, role=Role.OWNER).count()

    def to_dict(self):
        """Serialize board attributes for REST responses."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description or "",
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
            "updated_at": self.updated_at.isoformat() + "Z" if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Board {self.name}>"