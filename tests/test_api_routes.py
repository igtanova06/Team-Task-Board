"""Contract tests for the three Week-1 endpoints in docs/api_contract.md (section 3).

The skeleton returned mock data; these endpoints now read/write the real database and enforce
the rules of docs/business_rules.md.
"""
from app.extensions import db
from app.models import Comment, Task
from tests.conftest import login, token


def test_get_board_tasks_returns_array(app, world):
    c = login(app, "dave")                                   # viewer may read
    r = c.get(f"/api/boards/{world['board']}/tasks")
    assert r.status_code == 200
    body = r.get_json()
    assert isinstance(body, list) and len(body) == 1
    for key in ("id", "title", "description", "status", "priority", "board_id",
                "assigned_to", "created_by", "created_at", "updated_at"):
        assert key in body[0]
    assert body[0]["created_at"].endswith("Z")


def test_get_board_tasks_empty_board_is_empty_array(app, world):
    r = login(app, "eve").get(f"/api/boards/{world['other']}/tasks")
    assert r.status_code == 200 and r.get_json() == []


def test_get_board_tasks_requires_login_and_membership(app, world):
    assert app.test_client().get(f"/api/boards/{world['board']}/tasks").status_code == 401
    r = login(app, "eve").get(f"/api/boards/{world['board']}/tasks")
    assert r.status_code == 404 and "detail" in r.get_json()   # access concealed


def test_update_status(app, world):
    c = login(app, "ben")                                    # creator + assignee
    r = c.put(f"/api/tasks/{world['task']}/status",
              json={"status": "in_progress", "updated_at": token(c, world["task"])})
    assert r.status_code == 200
    body = r.get_json()
    assert set(body) == {"id", "status", "updated_at"} and body["status"] == "in_progress"
    assert db.session.get(Task, world["task"]).status == "in_progress"


def test_update_status_validation(app, world):
    c, t = login(app, "ben"), world["task"]
    url = f"/api/tasks/{t}/status"
    assert c.put(url, json={"status": "invalid_status", "updated_at": token(c, t)}).status_code == 400
    assert c.put(url, json={"updated_at": token(c, t)}).status_code == 400
    assert c.put(url, json={"status": "done"}).status_code == 400                       # token required
    assert c.put(url, json={"status": "done", "updated_at": "yesterday"}).status_code == 400
    assert c.put(url, data="x", content_type="text/plain").status_code == 415
    assert c.put(url, data="[1]", content_type="application/json").status_code == 400
    assert db.session.get(Task, t).status == "todo"


def test_update_status_conflict_on_stale_token(app, world):
    ben, t = login(app, "ben"), world["task"]
    stale = token(ben, t)
    assert login(app, "alex").put(f"/api/tasks/{t}/status",
                                  json={"status": "review", "updated_at": stale}).status_code == 200
    r = ben.put(f"/api/tasks/{t}/status", json={"status": "done", "updated_at": stale})
    assert r.status_code == 409 and "modified by another user" in r.get_json()["detail"]
    assert db.session.get(Task, t).status == "review"


def test_update_status_permissions(app, world):
    t = world["task"]
    for who, expected in (("alex", 200), ("ben", 200), ("chris", 403), ("dave", 403)):
        c = login(app, who)
        r = c.put(f"/api/tasks/{t}/status", json={"status": "review", "updated_at": token(c, t)})
        assert r.status_code == expected, who
    assert login(app, "eve").put(f"/api/tasks/{t}/status",
                                 json={"status": "done", "updated_at": "2026-01-01T00:00:00Z"}).status_code == 404


def test_add_comment(app, world):
    t = world["task"]
    c = login(app, "dave")                                   # viewers may comment
    r = c.post(f"/api/tasks/{t}/comments", json={"content": "  Great task!  "})
    assert r.status_code == 201
    body = r.get_json()
    assert body["content"] == "Great task!" and body["task_id"] == t
    assert body["user_id"] == world["users"]["dave"].id      # taken from the session, never the payload
    assert Comment.query.count() == 1


def test_add_comment_validation_and_access(app, world):
    t = world["task"]
    c = login(app, "chris")
    assert c.post(f"/api/tasks/{t}/comments", json={"content": "   "}).status_code == 400
    assert c.post(f"/api/tasks/{t}/comments", json={}).status_code == 400
    assert c.post(f"/api/tasks/{t}/comments", json={"content": "x" * 1001}).status_code == 400
    assert c.post(f"/api/tasks/{t}/comments", data="hi", content_type="text/plain").status_code == 415
    assert login(app, "eve").post(f"/api/tasks/{t}/comments", json={"content": "x"}).status_code == 404
    assert app.test_client().post(f"/api/tasks/{t}/comments", json={"content": "x"}).status_code == 401
    assert Comment.query.count() == 0
