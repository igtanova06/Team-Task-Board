# Importing every model here makes sure SQLAlchemy/Alembic see all tables
from app.models.user import User
from app.models.board import Board
from app.models.membership import BoardMembership, Role
from app.models.task import Task, TaskStatus, TaskPriority
from app.models.comment import Comment


__all__ = ["User", "Board", "BoardMembership", "Role", "Task", "TaskStatus", "TaskPriority", "Comment"]