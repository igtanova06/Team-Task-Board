import pytest

from app import create_app
from app.extensions import db
from app.models import (
    User, Board, BoardMembership, Role,
    Task, TaskStatus, TaskPriority, Comment,
)


@pytest.fixture
def app():
    """Create a clean application context with an in-memory SQLite database for each test."""
    test_app = create_app("testing")
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


def create_sample_entities():
    """Helper utility to persist a standard set of related entities."""
    user = User(username="alex", email="alex@example.com")
    user.set_password("Password123")

    board = Board(name="Website Development", description="Test board description")
    db.session.add_all([user, board])
    db.session.flush()

    membership = BoardMembership(user_id=user.id, board_id=board.id, role=Role.OWNER)
    task = Task(
        title="Initial Setup",
        board_id=board.id,
        created_by=user.id,
        assigned_to=user.id,
    )
    db.session.add_all([membership, task])
    db.session.flush()

    comment = Comment(content="Looks good!", task_id=task.id, user_id=user.id)
    db.session.add(comment)
    db.session.commit()

    return user, board, membership, task, comment


def test_query_all_models(app):
    """Verify that all models can be queried successfully."""
    create_sample_entities()
    assert len(User.query.all()) == 1
    assert len(Board.query.all()) == 1
    assert len(BoardMembership.query.all()) == 1
    assert len(Task.query.all()) == 1
    assert len(Comment.query.all()) == 1


def test_task_default_attributes(app):
    """Verify default status and priority assignments on tasks."""
    _, _, _, task, _ = create_sample_entities()
    assert task.status == TaskStatus.TODO
    assert task.priority == TaskPriority.MEDIUM


def test_password_hashing(app):
    """Verify passwords are encrypted and verification works as expected."""
    user, _, _, _, _ = create_sample_entities()
    assert user.password_hash != "Password123"
    assert user.check_password("Password123") is True
    assert user.check_password("WrongPassword") is False


def test_orm_relationships(app):
    """Verify bidirectional ORM relationships between models."""
    user, board, membership, task, comment = create_sample_entities()

    # Board <-> Task
    assert task.board == board
    assert board.tasks == [task]

    # User <-> Task (creator and assignee)
    assert task.creator == user
    assert task.assignee == user
    assert user.created_tasks == [task]
    assert user.assigned_tasks == [task]

    # Task <-> Comment
    assert comment.task == task
    assert task.comments == [comment]
    assert comment.author == user

    # User <-> BoardMembership <-> Board
    assert membership in user.memberships
    assert membership in board.memberships


def test_unique_membership_constraint(app):
    """Verify that adding duplicate user membership to the same board raises an error."""
    user, board, _, _, _ = create_sample_entities()
    duplicate_membership = BoardMembership(
        user_id=user.id,
        board_id=board.id,
        role=Role.MEMBER,
    )
    db.session.add(duplicate_membership)
    with pytest.raises(Exception):
        db.session.commit()
    db.session.rollback()


def test_cascade_delete_board(app):
    """Verify that deleting a board cascades to its tasks, comments, and memberships."""
    _, board, _, _, _ = create_sample_entities()
    db.session.delete(board)
    db.session.commit()

    assert Board.query.count() == 0
    assert BoardMembership.query.count() == 0
    assert Task.query.count() == 0
    assert Comment.query.count() == 0


def test_cascade_delete_task(app):
    """Verify that deleting a task cascades to its associated comments."""
    _, _, _, task, _ = create_sample_entities()
    db.session.delete(task)
    db.session.commit()

    assert Task.query.count() == 0
    assert Comment.query.count() == 0


def test_board_m2m_and_helpers(app):
    """Verify direct Many-to-Many relationships and Board/Membership/User helper methods."""
    user = User(username="alice", email="alice@example.com")
    user.set_password("Password123")
    board = Board(name="Project X", description="Test board description")
    db.session.add_all([user, board])
    db.session.flush()

    mem = BoardMembership(user_id=user.id, board_id=board.id, role=Role.OWNER)
    db.session.add(mem)
    db.session.commit()

    # Direct Many-to-Many relationship access
    assert user in board.members
    assert board in user.boards

    # Board helper methods
    assert board.is_owner(user.id) is True
    assert board.is_member(user.id) is True
    assert board.has_access(user.id) is True
    assert board.get_role(user.id) == Role.OWNER
    assert board.owner_count() == 1
    assert board.is_owner(9999) is False
    assert board.get_role(9999) is None

    # Serialization helpers
    b_dict = board.to_dict()
    assert b_dict["id"] == board.id
    assert b_dict["name"] == "Project X"
    assert b_dict["created_at"].endswith("Z")

    m_dict = mem.to_dict()
    assert m_dict["user_id"] == user.id
    assert m_dict["username"] == "alice"
    assert m_dict["role"] == Role.OWNER
    assert m_dict["joined_at"].endswith("Z")

    u_dict = user.to_dict()
    assert u_dict["username"] == "alice"
    assert u_dict["email"] == "alice@example.com"

