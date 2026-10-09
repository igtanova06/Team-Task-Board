from datetime import timedelta

from app import create_app
from app.extensions import db
from app.models import (
    User, Board, BoardMembership, Role,
    Task, TaskStatus, TaskPriority, Comment,
)
from app.models.user import utcnow


def clear_data():
    """Clear existing data in child-first order to prevent foreign key constraint violations."""
    Comment.query.delete()
    Task.query.delete()
    BoardMembership.query.delete()
    Board.query.delete()
    User.query.delete()
    db.session.commit()


def seed():
    """Seed initial sample data for development and testing."""
    clear_data()

    # 1. Create 4 Users
    users = {}
    for name in ("Alex", "Ben", "Chris", "David"):
        user = User(
            username=name,
            email=f"{name.lower()}@example.com",
        )
        # Always hash passwords, never store plain text
        user.set_password("Password123")
        db.session.add(user)
        users[name] = user

    # 2. Create 1 Board
    board = Board(
        name="Website Development",
        description="Kanban board for developing the team web application project.",
    )
    db.session.add(board)
    # flush() issues INSERT queries to the DB to obtain generated primary key IDs without committing
    db.session.flush()

    # 3. Create 4 Memberships with assigned roles
    role_assignments = {
        "Alex": Role.OWNER,
        "Ben": Role.MEMBER,
        "Chris": Role.MEMBER,
        "David": Role.VIEWER,
    }
    for name, role in role_assignments.items():
        membership = BoardMembership(
            user_id=users[name].id,
            board_id=board.id,
            role=role,
        )
        db.session.add(membership)

    # 4. Create 8 Tasks evenly distributed across 4 statuses (2 tasks per column)
    now = utcnow()
    task_definitions = [
        # (title, status, priority, assignee, deadline_offset_days)
        ("Design homepage wireframe", TaskStatus.TODO, TaskPriority.HIGH, "Ben", 7),
        ("Write software specification", TaskStatus.TODO, TaskPriority.MEDIUM, "Chris", 10),
        ("Implement user authentication", TaskStatus.IN_PROGRESS, TaskPriority.HIGH, "Ben", 5),
        ("Set up SQL Server schema", TaskStatus.IN_PROGRESS, TaskPriority.MEDIUM, "Alex", 4),
        ("Build Kanban drag-and-drop UI", TaskStatus.REVIEW, TaskPriority.HIGH, "Chris", 3),
        ("Create responsive navigation bar", TaskStatus.REVIEW, TaskPriority.LOW, "Ben", 2),
        ("Initialize repository on GitHub", TaskStatus.DONE, TaskPriority.LOW, "Alex", -3),
        ("Select brand typography and palette", TaskStatus.DONE, TaskPriority.MEDIUM, "Chris", -1),
    ]

    tasks = []
    for title, status, priority, assignee_name, offset_days in task_definitions:
        task = Task(
            title=title,
            description=f"Detailed instructions and requirements for: {title}.",
            status=status,
            priority=priority,
            deadline=now + timedelta(days=offset_days),
            board_id=board.id,
            assigned_to=users[assignee_name].id,
            created_by=users["Alex"].id,
        )
        db.session.add(task)
        tasks.append(task)
    db.session.flush()

    # 5. Create 5 Comments
    comment_definitions = [
        # (task_index, author_name, content)
        (0, "Ben", "I have started sketching the layout on Figma."),
        (2, "Alex", "Please use Flask-Login for handling session states."),
        (2, "Ben", "Understood. Server-side form validation is also completed."),
        (4, "Chris", "The REST API endpoint for status updates is ready for review."),
        (4, "Alex", "Code looks solid, remember to add proper HTTP status codes."),
    ]
    for task_index, author_name, content in comment_definitions:
        comment = Comment(
            content=content,
            task_id=tasks[task_index].id,
            user_id=users[author_name].id,
        )
        db.session.add(comment)

    db.session.commit()
    print("Seed successful! Seeded 4 users, 1 board, 4 memberships, 8 tasks, and 5 comments.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        seed()
