from app.extensions import db
from app.models.user import utcnow

class Board(db.Model):
    __tablename__ = "boards"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False) # onupdate: automatically refresh this column every UPDATE

    # One-to-Many: Board -> Tasks
    # cascade="all, delete-orphan": deleting a board also deletes all tasks inside
    # backref="board" adds tasks.board automatically
    tasks = db.relationship(
        "Task",
        backref="board",
        cascade="all, delete-orphan",
        lazy="select"
    )

    def __repr__(self):
        return f"<Board {self.name}>"