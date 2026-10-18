"""Endpoints added for the Kanban UI + auth/CSRF behaviour (see app/api/tasks.py)."""
import pytest

from app import create_app
from app.extensions import db
from app.models import User, Board, BoardMembership, Role, Task, Comment
from tests.conftest import FreshUserClient, login, token


# ------------------------------------------------------------------ web login
def test_login_validation_and_wrong_password(app, world):
    c = app.test_client()
    assert c.post("/login", data={"identity": "", "password": ""}).status_code == 422
    assert c.post("/login", data={"identity": "alex", "password": "nope"}).status_code == 422
    assert login(app, "alex@example.com")                      # email works too


def test_login_blocks_open_redirect(app, world):
    r = app.test_client().post("/login?next=https://evil.example",
                               data={"identity": "alex", "password": "Password123"})
    assert r.status_code == 302 and "evil" not in r.headers["Location"]


def test_pages_require_login_and_membership(app, world):
    assert app.test_client().get(f"/boards/{world['board']}").status_code == 302
    assert login(app, "eve").get(f"/boards/{world['board']}").status_code == 404      # concealed
    assert login(app, "alex").get(f"/boards/{world['board']}").status_code == 200
    assert login(app, "alex").get("/").status_code == 302


# ------------------------------------------------------------------ board info
def test_board_info(app, world):
    r = login(app, "dave").get(f"/api/boards/{world['board']}")
    assert r.status_code == 200
    body = r.get_json()
    assert body["role"] == "viewer" and body["can_create"] is False and len(body["members"]) == 4
    assert login(app, "eve").get(f"/api/boards/{world['board']}").status_code == 404
    assert login(app, "alex").get("/api/boards/9999").status_code == 404


def test_task_list_carries_per_task_permissions(app, world):
    for who, edit, status, reassign, delete in (
            ("alex", True, True, True, True), ("ben", True, True, True, False),
            ("chris", False, False, False, False), ("dave", False, False, False, False)):
        t = login(app, who).get(f"/api/boards/{world['board']}/tasks").get_json()[0]
        assert t["permissions"] == {"edit": edit, "status": status, "reassign": reassign, "delete": delete}, who


# ------------------------------------------------------------------ create
def test_create_task(app, world):
    c = login(app, "chris")
    r = c.post(f"/api/boards/{world['board']}/tasks", json={
        "title": "  Build API  ", "description": "d", "priority": "high", "deadline": "2026-10-20",
        "assigned_to": world["users"]["ben"].id, "status": "review"})
    assert r.status_code == 201
    t = r.get_json()
    assert t["title"] == "Build API" and t["status"] == "review" and t["deadline"] == "2026-10-20"
    assert db.session.get(Task, t["id"]).created_by == world["users"]["chris"].id


def test_create_defaults(app, world):
    t = login(app, "ben").post(f"/api/boards/{world['board']}/tasks", json={"title": "Only title"}).get_json()
    assert t["status"] == "todo" and t["priority"] == "medium" and t["assigned_to"] is None


@pytest.mark.parametrize("payload,field", [
    ({}, "title"), ({"title": "   "}, "title"), ({"title": "x" * 201}, "title"),
    ({"title": "ok", "priority": "urgent"}, "priority"), ({"title": "ok", "status": "blocked"}, "status"),
    ({"title": "ok", "deadline": "10/12/2026"}, "deadline"), ({"title": "ok", "assigned_to": "abc"}, "assigned_to"),
    ({"title": "ok", "assigned_to": 99999}, "assigned_to"),
])
def test_create_validation(app, world, payload, field):
    r = login(app, "ben").post(f"/api/boards/{world['board']}/tasks", json=payload)
    assert r.status_code == 400 and field in r.get_json()["errors"]
    assert Task.query.count() == 1


def test_cannot_assign_outsider(app, world):
    r = login(app, "ben").post(f"/api/boards/{world['board']}/tasks",
                               json={"title": "t", "assigned_to": world["users"]["eve"].id})
    assert r.status_code == 400


def test_create_permissions(app, world):
    assert login(app, "dave").post(f"/api/boards/{world['board']}/tasks", json={"title": "t"}).status_code == 403
    assert login(app, "eve").post(f"/api/boards/{world['board']}/tasks", json={"title": "t"}).status_code == 404
    assert Task.query.count() == 1


# ------------------------------------------------------------------ edit
def test_edit_partial_and_clear(app, world):
    c, t = login(app, "ben"), world["task"]
    r = c.patch(f"/api/tasks/{t}", json={"priority": "high", "deadline": "2026-10-20"})
    assert r.status_code == 200 and r.get_json()["priority"] == "high" and r.get_json()["title"] == "Existing"
    r = c.patch(f"/api/tasks/{t}", json={"deadline": None, "assigned_to": None})
    assert r.status_code == 200 and r.get_json()["deadline"] is None and r.get_json()["assigned_to"] is None


def test_edit_validation(app, world):
    r = login(app, "alex").patch(f"/api/tasks/{world['task']}", json={"title": ""})
    assert r.status_code == 400 and "title" in r.get_json()["errors"]
    assert db.session.get(Task, world["task"]).title == "Existing"


def test_edit_permissions(app, world):
    t = world["task"]
    assert login(app, "alex").patch(f"/api/tasks/{t}", json={"priority": "low"}).status_code == 200   # owner
    assert login(app, "ben").patch(f"/api/tasks/{t}", json={"priority": "low"}).status_code == 200    # creator
    assert login(app, "chris").patch(f"/api/tasks/{t}", json={"priority": "high"}).status_code == 403  # unrelated member
    assert login(app, "dave").patch(f"/api/tasks/{t}", json={"priority": "high"}).status_code == 403   # viewer
    assert login(app, "eve").patch(f"/api/tasks/{t}", json={"priority": "high"}).status_code == 404    # outsider


def test_assignee_can_edit_but_not_reassign(app, world):
    ben = login(app, "ben")
    t = ben.post(f"/api/boards/{world['board']}/tasks",
                 json={"title": "Chris owns", "assigned_to": world["users"]["chris"].id}).get_json()["id"]
    chris = login(app, "chris")
    assert chris.patch(f"/api/tasks/{t}", json={"priority": "high"}).status_code == 200      # assignee: edit ok
    r = chris.patch(f"/api/tasks/{t}", json={"assigned_to": world["users"]["alex"].id})      # not creator
    assert r.status_code == 403
    assert ben.patch(f"/api/tasks/{t}", json={"assigned_to": world["users"]["alex"].id}).status_code == 200


def test_edit_conflict_on_stale_token(app, world):
    ben, t = login(app, "ben"), world["task"]
    stale = token(ben, t)
    login(app, "alex").patch(f"/api/tasks/{t}", json={"title": "Changed by Alex"})
    r = ben.patch(f"/api/tasks/{t}", json={"title": "Mine", "updated_at": stale})
    assert r.status_code == 409
    assert db.session.get(Task, t).title == "Changed by Alex"
    assert ben.patch(f"/api/tasks/{t}", json={"title": "Mine", "updated_at": token(ben, t)}).status_code == 200


# ------------------------------------------------------------------ detail + delete
def test_task_detail_with_comments(app, world):
    t = world["task"]
    login(app, "dave").post(f"/api/tasks/{t}/comments", json={"content": "hi"})
    body = login(app, "chris").get(f"/api/tasks/{t}").get_json()
    assert len(body["comments"]) == 1 and body["comments"][0]["author"]["username"] == "dave"
    assert login(app, "eve").get(f"/api/tasks/{t}").status_code == 404


def test_delete_owner_only(app, world):
    t = world["task"]
    for who in ("ben", "chris", "dave"):                       # even the creator cannot delete
        assert login(app, who).delete(f"/api/tasks/{t}").status_code == 403, who
    assert login(app, "eve").delete(f"/api/tasks/{t}").status_code == 404
    assert db.session.get(Task, t) is not None
    db.session.add(Comment(content="hi", task_id=t, user_id=world["users"]["ben"].id))
    db.session.commit()
    assert login(app, "alex").delete(f"/api/tasks/{t}").status_code == 204
    assert db.session.get(Task, t) is None and Comment.query.count() == 0
    assert login(app, "alex").delete("/api/tasks/9999").status_code == 404


# ------------------------------------------------------------------ CSRF
def _csrf_app():
    app = create_app("testing")
    app.test_client_class = FreshUserClient
    app.config["WTF_CSRF_ENABLED"] = True
    return app


def test_csrf_required_for_cookie_sessions_but_not_for_bearer_clients():
    app = _csrf_app()
    with app.app_context():
        db.create_all()
        u = User(username="zed", email="zed@example.com"); u.set_password("Password123")
        b = Board(name="b"); db.session.add_all([u, b]); db.session.flush()
        db.session.add(BoardMembership(user_id=u.id, board_id=b.id, role=Role.OWNER)); db.session.commit()
        c = app.test_client()
        with c.session_transaction() as s:
            s["_user_id"] = str(u.id); s["_fresh"] = True
        url = f"/api/boards/{b.id}/tasks"
        r = c.post(url, json={"title": "x"})                                   # cookie session, no token
        assert r.status_code == 400 and "csrf" in r.get_json()["detail"].lower()
        r = c.post(url, json={"title": "x"}, headers={"Authorization": "Bearer abc"})   # API client
        assert r.status_code == 201
        db.session.remove(); db.drop_all()
