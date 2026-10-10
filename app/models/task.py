from app.extensions import db
from app.models.user import utcnow


class TaskStatus:
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    ALL = (TODO, IN_PROGRESS, REVIEW, DONE)


class TaskPriority:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ALL = (LOW, MEDIUM, HIGH)


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default=TaskStatus.TODO, index=True)
    priority = db.Column(db.String(20), nullable=False, default=TaskPriority.MEDIUM)
    deadline = db.Column(db.DateTime, nullable=True)
    board_id = db.Column(db.Integer, db.ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        db.CheckConstraint("status IN ('todo', 'in_progress', 'review', 'done')", name="ck_task_status"),
        db.CheckConstraint("priority IN ('low', 'medium', 'high')", name="ck_task_priority")
    )

    assignee = db.relationship(
        "User", foreign_keys=[assigned_to], backref="assigned_tasks"
    )
    creator = db.relationship(
        "User", foreign_keys=[created_by], backref="created_tasks"
    )

    # One-to-Many: Task -> Comments. Deleting a Task also deletes its comments
    comments = db.relationship(
        "Comment",
        backref="task",
        cascade="all, delete-orphan",
        order_by="Comment.created_at"
    )

    def __repr__(self):
        return f"<Task {self.title} [{self.status}]>"