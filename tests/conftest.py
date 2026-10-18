"""Shared fixtures for the API tests (in-memory SQLite, no SQL Server needed)."""
import pytest
from flask import g
from flask.testing import FlaskClient

from app import create_app
from app.extensions import db
from app.models import User, Board, BoardMembership, Role, Task


class FreshUserClient(FlaskClient):
    """The fixtures keep one app context open, so Flask-Login would cache the first user in `g`
    across requests. Drop that cache so every request authenticates from its own cookie."""

    def open(self, *args, **kwargs):
        g.pop("_login_user", None)
        return super().open(*args, **kwargs)


@pytest.fixture
def app():
    app = create_app("testing")
    app.test_client_class = FreshUserClient
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def world(app):
    """alex=owner, ben/chris=member, dave=viewer, eve=outsider.
    One board with task `task` (created by ben, assigned to ben) + a second board for eve."""
    users = {}
    for name in ("alex", "ben", "chris", "dave", "eve"):
        u = User(username=name, email=f"{name}@example.com")
        u.set_password("Password123")
        db.session.add(u)
        users[name] = u
    board, other = Board(name="Website Development"), Board(name="Other board")
    db.session.add_all([board, other])
    db.session.flush()
    for name, role in (("alex", Role.OWNER), ("ben", Role.MEMBER), ("chris", Role.MEMBER), ("dave", Role.VIEWER)):
        db.session.add(BoardMembership(user_id=users[name].id, board_id=board.id, role=role))
    db.session.add(BoardMembership(user_id=users["eve"].id, board_id=other.id, role=Role.OWNER))
    task = Task(title="Existing", board_id=board.id, created_by=users["ben"].id, assigned_to=users["ben"].id)
    db.session.add(task)
    db.session.commit()
    return {"users": users, "board": board.id, "other": other.id, "task": task.id}


def login(app, name):
    c = app.test_client()
    r = c.post("/login", data={"identity": name, "password": "Password123"})
    assert r.status_code == 302
    return c


def token(client, task_id):
    """The updated_at a UI would send back (what GET /boards/<id>/tasks returned)."""
    return client.get(f"/api/tasks/{task_id}").json["updated_at"]
