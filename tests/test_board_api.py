"""Tests for Board CRUD and Member management APIs."""
import pytest
from app.extensions import db
from app.models import Board, BoardMembership, Role, Task
from tests.conftest import login


# ------------------------------------------------------------------ List & Detail
def test_list_my_boards(app, world):
    # alex is owner of world["board"]
    r = login(app, "alex").get("/api/boards")
    assert r.status_code == 200
    boards = r.get_json()
    assert len(boards) == 1
    assert boards[0]["id"] == world["board"]
    assert boards[0]["role"] == "owner"
    assert boards[0]["member_count"] == 4

    # eve is owner of world["other"]
    r_eve = login(app, "eve").get("/api/boards")
    assert r_eve.status_code == 200
    eve_boards = r_eve.get_json()
    assert len(eve_boards) == 1
    assert eve_boards[0]["id"] == world["other"]


def test_get_board_detail(app, world):
    r = login(app, "alex").get(f"/api/boards/{world['board']}")
    assert r.status_code == 200
    body = r.get_json()
    assert body["board"]["name"] == "Website Development"
    assert body["role"] == "owner"
    assert len(body["members"]) == 4

    # Outsider sees 404 concealed
    r_eve = login(app, "eve").get(f"/api/boards/{world['board']}")
    assert r_eve.status_code == 404


# ------------------------------------------------------------------ Create Board
def test_create_board_success(app, world):
    c = login(app, "ben")
    r = c.post("/api/boards", json={"name": "Ben's Secret Board", "description": "Top secret"})
    assert r.status_code == 201
    data = r.get_json()
    assert data["name"] == "Ben's Secret Board"
    assert data["role"] == "owner"
    assert data["member_count"] == 1

    # Verify database state
    b = db.session.get(Board, data["id"])
    assert b is not None
    assert b.is_owner(world["users"]["ben"].id)


def test_create_board_validation_error(app, world):
    c = login(app, "ben")
    r = c.post("/api/boards", json={"name": ""})
    assert r.status_code == 400
    assert "name" in r.get_json()["errors"]


# ------------------------------------------------------------------ Update Board
def test_update_board(app, world):
    board_id = world["board"]

    # Owner can update
    r = login(app, "alex").patch(f"/api/boards/{board_id}", json={"name": "Renamed Board", "description": "New Desc"})
    assert r.status_code == 200
    assert r.get_json()["name"] == "Renamed Board"

    # Member cannot update (403)
    r_ben = login(app, "ben").patch(f"/api/boards/{board_id}", json={"name": "Hacked"})
    assert r_ben.status_code == 403

    # Viewer cannot update (403)
    r_dave = login(app, "dave").patch(f"/api/boards/{board_id}", json={"name": "Hacked 2"})
    assert r_dave.status_code == 403

    # Outsider sees 404
    r_eve = login(app, "eve").patch(f"/api/boards/{board_id}", json={"name": "Hacked 3"})
    assert r_eve.status_code == 404


# ------------------------------------------------------------------ Delete Board
def test_delete_board_and_cascade(app, world):
    board_id = world["board"]

    # Non-owner cannot delete
    assert login(app, "ben").delete(f"/api/boards/{board_id}").status_code == 403

    # Owner deletes
    assert login(app, "alex").delete(f"/api/boards/{board_id}").status_code == 204

    # Verify board and children are gone
    assert db.session.get(Board, board_id) is None
    assert BoardMembership.query.filter_by(board_id=board_id).count() == 0
    assert Task.query.filter_by(board_id=board_id).count() == 0


# ------------------------------------------------------------------ Add Member
def test_add_member(app, world):
    board_id = world["board"]
    eve = world["users"]["eve"]

    # Non-owner cannot add
    assert login(app, "ben").post(f"/api/boards/{board_id}/members", json={"user_id": eve.id, "role": "member"}).status_code == 403

    # Owner adds eve
    r = login(app, "alex").post(f"/api/boards/{board_id}/members", json={"user_id": eve.id, "role": "member"})
    assert r.status_code == 201
    assert r.get_json()["user_id"] == eve.id
    assert r.get_json()["role"] == "member"

    # Adding already-member fails
    r_dup = login(app, "alex").post(f"/api/boards/{board_id}/members", json={"user_id": eve.id, "role": "viewer"})
    assert r_dup.status_code == 400

    # Adding non-existent user fails (404)
    r_none = login(app, "alex").post(f"/api/boards/{board_id}/members", json={"user_id": 99999})
    assert r_none.status_code == 404


# ------------------------------------------------------------------ Update Member Role
def test_update_member_role_and_sole_owner_guard(app, world):
    board_id = world["board"]
    ben = world["users"]["ben"]
    alex = world["users"]["alex"]

    # Owner changes ben to viewer
    r = login(app, "alex").patch(f"/api/boards/{board_id}/members/{ben.id}", json={"role": "viewer"})
    assert r.status_code == 200
    assert r.get_json()["role"] == "viewer"

    # alex is the sole owner; trying to demote alex fails (400)
    r_demote = login(app, "alex").patch(f"/api/boards/{board_id}/members/{alex.id}", json={"role": "member"})
    assert r_demote.status_code == 400
    assert "sole owner" in r_demote.get_json()["detail"].lower()

    # Promote ben to owner -> now there are 2 owners
    assert login(app, "alex").patch(f"/api/boards/{board_id}/members/{ben.id}", json={"role": "owner"}).status_code == 200

    # Now alex can demote himself since ben is also owner
    assert login(app, "alex").patch(f"/api/boards/{board_id}/members/{alex.id}", json={"role": "member"}).status_code == 200


# ------------------------------------------------------------------ Remove Member & Unassign Tasks
def test_remove_member_and_leave_board(app, world):
    board_id = world["board"]
    ben = world["users"]["ben"]
    chris = world["users"]["chris"]
    alex = world["users"]["alex"]

    # Dave (viewer) cannot kick chris (403)
    assert login(app, "dave").delete(f"/api/boards/{board_id}/members/{chris.id}").status_code == 403

    # Alex (sole owner) cannot leave/remove himself (400)
    r_leave = login(app, "alex").delete(f"/api/boards/{board_id}/members/{alex.id}")
    assert r_leave.status_code == 400
    assert "sole owner" in r_leave.get_json()["detail"].lower()

    # Ben is assigned to task world["task"]. Ben leaves the board:
    task = db.session.get(Task, world["task"])
    assert task.assigned_to == ben.id

    r_ben_leave = login(app, "ben").delete(f"/api/boards/{board_id}/members/{ben.id}")
    assert r_ben_leave.status_code == 204

    # Verify ben is no longer a member and the task was unassigned
    assert BoardMembership.query.filter_by(board_id=board_id, user_id=ben.id).first() is None
    db.session.refresh(task)
    assert task.assigned_to is None

    # Alex kicks chris (204)
    assert login(app, "alex").delete(f"/api/boards/{board_id}/members/{chris.id}").status_code == 204
    assert BoardMembership.query.filter_by(board_id=board_id, user_id=chris.id).first() is None
