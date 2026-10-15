import pytest
from flask import g
from flask.testing import FlaskClient

from app import create_app
from app.extensions import db
from app.models import User, Board, BoardMembership, Role, Task, Comment


class FreshUserClient(FlaskClient):
    """The fixtures keep one app context open, so Flask-Login would cache the first user in `g`
    across requests. Drop that cache so every request authenticates from its own session cookie."""

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
    """alex=owner, ben=member, chris=member, dave=viewer, eve=outsider; one board, one task by ben."""
    users = {}
    for name in ("alex", "ben", "chris", "dave", "eve"):
        u = User(username=name, email=f"{name}@example.com")
        u.set_password("Password123")
        db.session.add(u)
        users[name] = u
    board = Board(name="Website Development")
    other = Board(name="Other board")
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


# ------------------------------------------------------------------ auth
def test_api_requires_login(app, world):
    c = app.test_client()
    r = c.get(f"/api/boards/{world['board']}")
    assert r.status_code == 401 and r.json["error"]
    assert c.post(f"/api/boards/{world['board']}/tasks", json={"title": "x"}).status_code == 401


def test_login_validation_and_wrong_password(app, world):
    c = app.test_client()
    assert c.post("/login", data={"identity": "", "password": ""}).status_code == 422
    r = c.post("/login", data={"identity": "alex", "password": "nope"})
    assert r.status_code == 422
    assert login(app, "alex@example.com")  # email works too


def test_login_blocks_open_redirect(app, world):
    c = app.test_client()
    r = c.post("/login?next=https://evil.example", data={"identity": "alex", "password": "Password123"})
    assert r.headers["Location"].endswith("/")
    assert "evil" not in r.headers["Location"]


def test_page_requires_login_and_membership(app, world):
    assert app.test_client().get(f"/boards/{world['board']}").status_code == 302
    assert login(app, "eve").get(f"/boards/{world['board']}").status_code == 403
    assert login(app, "alex").get(f"/boards/{world['board']}").status_code == 200


# ------------------------------------------------------------------ read
def test_get_board(app, world):
    r = login(app, "dave").get(f"/api/boards/{world['board']}")
    assert r.status_code == 200
    assert r.json["role"] == "viewer" and r.json["permissions"]["edit"] is False
    assert len(r.json["tasks"]) == 1 and len(r.json["members"]) == 4
    assert r.json["tasks"][0]["code"].startswith("TSK-")


def test_outsider_cannot_read(app, world):
    c = login(app, "eve")
    assert c.get(f"/api/boards/{world['board']}").status_code == 403
    assert c.get(f"/api/tasks/{world['task']}").status_code == 403
    assert c.get("/api/boards/9999").status_code == 404


# ------------------------------------------------------------------ create
def test_create_task(app, world):
    c = login(app, "ben")
    r = c.post(f"/api/boards/{world['board']}/tasks", json={
        "title": "  Build API  ", "description": "d", "priority": "high",
        "deadline": "2026-10-20", "assigned_to": world["users"]["chris"].id, "status": "review"})
    assert r.status_code == 201
    t = r.json["task"]
    assert t["title"] == "Build API" and t["status"] == "review" and t["deadline"] == "2026-10-20"
    assert db.session.get(Task, t["id"]).created_by == world["users"]["ben"].id


def test_create_defaults(app, world):
    r = login(app, "ben").post(f"/api/boards/{world['board']}/tasks", json={"title": "Only title"})
    assert r.status_code == 201
    assert r.json["task"]["status"] == "todo" and r.json["task"]["priority"] == "medium"


@pytest.mark.parametrize("payload,field", [
    ({}, "title"),
    ({"title": "   "}, "title"),
    ({"title": "x" * 201}, "title"),
    ({"title": "ok", "priority": "urgent"}, "priority"),
    ({"title": "ok", "status": "blocked"}, "status"),
    ({"title": "ok", "deadline": "10/12/2026"}, "deadline"),
    ({"title": "ok", "assigned_to": "abc"}, "assigned_to"),
    ({"title": "ok", "assigned_to": 99999}, "assigned_to"),
])
def test_create_validation(app, world, payload, field):
    r = login(app, "ben").post(f"/api/boards/{world['board']}/tasks", json=payload)
    assert r.status_code == 422
    assert field in r.json["errors"]
    assert Task.query.count() == 1


def test_cannot_assign_viewer_or_outsider(app, world):
    c = login(app, "ben")
    for who in ("dave", "eve"):
        r = c.post(f"/api/boards/{world['board']}/tasks", json={"title": "t", "assigned_to": world["users"][who].id})
        assert r.status_code == 422


def test_bad_json_body(app, world):
    r = login(app, "ben").post(f"/api/boards/{world['board']}/tasks", data="nope", content_type="application/json")
    assert r.status_code == 400


def test_viewer_and_outsider_cannot_create(app, world):
    for who in ("dave", "eve"):
        assert login(app, who).post(f"/api/boards/{world['board']}/tasks", json={"title": "t"}).status_code == 403
    assert Task.query.count() == 1


# ------------------------------------------------------------------ update / status
def test_update_partial(app, world):
    c = login(app, "chris")  # any editor may edit
    r = c.put(f"/api/tasks/{world['task']}", json={"priority": "high"})
    assert r.status_code == 200
    assert r.json["task"]["priority"] == "high" and r.json["task"]["title"] == "Existing"


def test_update_can_clear_deadline_and_assignee(app, world):
    c = login(app, "ben")
    c.put(f"/api/tasks/{world['task']}", json={"deadline": "2026-10-20"})
    r = c.put(f"/api/tasks/{world['task']}", json={"deadline": None, "assigned_to": None})
    assert r.status_code == 200 and r.json["task"]["deadline"] is None and r.json["task"]["assigned_to"] is None


def test_update_validation(app, world):
    r = login(app, "ben").put(f"/api/tasks/{world['task']}", json={"title": ""})
    assert r.status_code == 422 and "title" in r.json["errors"]
    assert db.session.get(Task, world["task"]).title == "Existing"


def test_update_status(app, world):
    c = login(app, "ben")
    for s in ("in_progress", "review", "done", "todo"):
        r = c.patch(f"/api/tasks/{world['task']}/status", json={"status": s})
        assert r.status_code == 200 and r.json["task"]["status"] == s
    r = c.patch(f"/api/tasks/{world['task']}/status", json={"status": "archived"})
    assert r.status_code == 422
    assert db.session.get(Task, world["task"]).status == "todo"


def test_viewer_cannot_update_or_move(app, world):
    c = login(app, "dave")
    assert c.put(f"/api/tasks/{world['task']}", json={"title": "hack"}).status_code == 403
    assert c.patch(f"/api/tasks/{world['task']}/status", json={"status": "done"}).status_code == 403
    t = db.session.get(Task, world["task"])
    assert t.title == "Existing" and t.status == "todo"


def test_outsider_cannot_update_move_delete(app, world):
    c = login(app, "eve")
    assert c.put(f"/api/tasks/{world['task']}", json={"title": "x"}).status_code == 403
    assert c.patch(f"/api/tasks/{world['task']}/status", json={"status": "done"}).status_code == 403
    assert c.delete(f"/api/tasks/{world['task']}").status_code == 403


# ------------------------------------------------------------------ delete
def test_delete_rules(app, world):
    tid = world["task"]  # created by ben
    assert login(app, "dave").delete(f"/api/tasks/{tid}").status_code == 403      # viewer
    assert login(app, "chris").delete(f"/api/tasks/{tid}").status_code == 403     # member, not creator
    assert db.session.get(Task, tid) is not None
    assert login(app, "ben").delete(f"/api/tasks/{tid}").status_code == 204       # creator
    assert db.session.get(Task, tid) is None


def test_owner_can_delete_any_and_comments_cascade(app, world):
    tid = world["task"]
    db.session.add(Comment(content="hi", task_id=tid, user_id=world["users"]["ben"].id))
    db.session.commit()
    assert login(app, "alex").delete(f"/api/tasks/{tid}").status_code == 204
    assert Comment.query.count() == 0


def test_delete_missing_task(app, world):
    assert login(app, "alex").delete("/api/tasks/9999").status_code == 404


# ------------------------------------------------------------------ comments
def test_comments(app, world):
    tid = world["task"]
    c = login(app, "chris")
    r = c.post(f"/api/tasks/{tid}/comments", json={"content": " Looks good "})
    assert r.status_code == 201 and r.json["comment"]["content"] == "Looks good"
    assert c.post(f"/api/tasks/{tid}/comments", json={"content": "  "}).status_code == 422
    assert login(app, "dave").post(f"/api/tasks/{tid}/comments", json={"content": "x"}).status_code == 403
    detail = login(app, "dave").get(f"/api/tasks/{tid}").json
    assert len(detail["comments"]) == 1 and detail["permissions"] == {"edit": False, "delete": False}
    assert login(app, "ben").get(f"/api/tasks/{tid}").json["task"]["comment_count"] == 1


# ------------------------------------------------------------------ csrf
def test_csrf_enforced_when_enabled(world):
    app = create_app("testing")
    app.test_client_class = FreshUserClient
    app.config["WTF_CSRF_ENABLED"] = True
    with app.app_context():
        db.create_all()
        u = User(username="zed", email="zed@example.com"); u.set_password("Password123")
        b = Board(name="b"); db.session.add_all([u, b]); db.session.flush()
        db.session.add(BoardMembership(user_id=u.id, board_id=b.id, role=Role.OWNER)); db.session.commit()
        c = app.test_client()
        with c.session_transaction() as s:
            s["_user_id"] = str(u.id); s["_fresh"] = True
        r = c.post(f"/api/boards/{b.id}/tasks", json={"title": "x"})
        assert r.status_code == 400 and "session" in r.json["error"].lower()
        db.session.remove(); db.drop_all()
