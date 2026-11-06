"""  JWT Bearer tren /api that phai stateless (khong session cookie) va giu dung RBAC."""
from flask_jwt_extended import create_access_token

from tests.conftest import login


def _bearer(world, name):
    return {"Authorization": f"Bearer {create_access_token(identity=str(world['users'][name].id))}"}


def _session_cookies(res):
    return [c for c in res.headers.getlist("Set-Cookie") if c.startswith("session=")]


def test_bearer_on_real_api_sets_no_session_cookie(app, world):
    c = app.test_client()
    res = c.get("/api/boards", headers=_bearer(world, "alex"))
    assert res.status_code == 200
    assert _session_cookies(res) == []
    with c.session_transaction() as s:
        assert "_user_id" not in s


def test_bearer_write_endpoint_is_stateless(app, world):
    c = app.test_client()
    res = c.post("/api/boards", json={"name": "Stateless"}, headers=_bearer(world, "alex"))
    assert res.status_code == 201
    assert _session_cookies(res) == []


def test_invalid_bearer_still_401(app, world):
    c = app.test_client()
    assert c.get("/api/boards", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert c.get("/api/boards").status_code == 401


def test_bearer_rbac_on_membership_api(app, world):
    b = world["board"]
    payload = {"identity": "eve", "role": "viewer"}
    assert app.test_client().post(f"/api/boards/{b}/members", json=payload,
                                  headers=_bearer(world, "dave")).status_code == 403   # viewer
    assert app.test_client().post(f"/api/boards/{b}/members", json=payload,
                                  headers=_bearer(world, "ben")).status_code == 403    # member
    assert app.test_client().get(f"/api/boards/{b}", headers=_bearer(world, "eve")).status_code == 404  # outsider
    assert app.test_client().post(f"/api/boards/{b}/members", json=payload,
                                  headers=_bearer(world, "alex")).status_code == 201   # owner


def test_cookie_session_login_still_works(app, world):
    c = login(app, "alex")
    assert c.get("/api/boards").status_code == 200
