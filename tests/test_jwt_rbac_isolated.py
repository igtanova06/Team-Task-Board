"""
tests/test_jwt_rbac_isolated.py

Kiểm thử toàn diện cho module JWT Bearer độc lập và RBAC Decorators:
- Tách JWT Bearer khỏi Flask-Login session (không lưu session cookie).
- Phân quyền RBAC cho Board: Owner / Member / Viewer.
- Ngăn chặn truy cập trái quyền (403) và giấu board với người ngoài (404).
"""
import pytest
from flask import jsonify
from flask_jwt_extended import create_access_token

from app.auth.jwt_helpers import jwt_api_required, get_jwt_user_id
from app.auth.rbac import (
    board_role_required,
    owner_required,
    member_required,
    viewer_required,
)
from app.extensions import db
from app.models import User, Board, BoardMembership, Role


@pytest.fixture
def rbac_app(app):
    """Đăng ký test endpoints sử dụng decorators rbac & jwt."""
    @app.get("/test/api/boards/<int:board_id>/viewer-only")
    @jwt_api_required
    @viewer_required
    def test_viewer(board_id):
        return jsonify({"message": "viewer access ok", "user_id": get_jwt_user_id()})

    @app.post("/test/api/boards/<int:board_id>/member-action")
    @jwt_api_required
    @member_required
    def test_member(board_id):
        return jsonify({"message": "member action ok"})

    @app.delete("/test/api/boards/<int:board_id>/owner-action")
    @jwt_api_required
    @owner_required
    def test_owner(board_id):
        return jsonify({"message": "owner action ok"})

    return app


@pytest.fixture
def rbac_world(app):
    """Tạo 1 board và 4 users với các role khác nhau: Owner, Member, Viewer, Outsider."""
    with app.app_context():
        # Users
        u_owner = User(username="rbac_owner", email="owner@test.com")
        u_owner.set_password("Password123")

        u_member = User(username="rbac_member", email="member@test.com")
        u_member.set_password("Password123")

        u_viewer = User(username="rbac_viewer", email="viewer@test.com")
        u_viewer.set_password("Password123")

        u_outsider = User(username="rbac_outsider", email="outsider@test.com")
        u_outsider.set_password("Password123")

        board = Board(name="RBAC Test Board")
        db.session.add_all([u_owner, u_member, u_viewer, u_outsider, board])
        db.session.flush()

        # Memberships
        m_owner = BoardMembership(user_id=u_owner.id, board_id=board.id, role=Role.OWNER)
        m_member = BoardMembership(user_id=u_member.id, board_id=board.id, role=Role.MEMBER)
        m_viewer = BoardMembership(user_id=u_viewer.id, board_id=board.id, role=Role.VIEWER)

        db.session.add_all([m_owner, m_member, m_viewer])
        db.session.commit()

        # Tạo tokens cho từng user
        t_owner = create_access_token(identity=str(u_owner.id))
        t_member = create_access_token(identity=str(u_member.id))
        t_viewer = create_access_token(identity=str(u_viewer.id))
        t_outsider = create_access_token(identity=str(u_outsider.id))

        return {
            "board_id": board.id,
            "tokens": {
                "owner": t_owner,
                "member": t_member,
                "viewer": t_viewer,
                "outsider": t_outsider,
            },
            "user_ids": {
                "owner": u_owner.id,
                "member": u_member.id,
                "viewer": u_viewer.id,
                "outsider": u_outsider.id,
            }
        }


def test_jwt_api_required_no_token_and_invalid(rbac_app, rbac_world):
    client = rbac_app.test_client()
    bid = rbac_world["board_id"]

    # 1. Không có header Authorization -> 401
    r_no_auth = client.get(f"/test/api/boards/{bid}/viewer-only")
    assert r_no_auth.status_code == 401
    assert "Missing or invalid" in r_no_auth.get_json()["detail"]

    # 2. Token không hợp lệ -> 401
    r_bad_auth = client.get(
        f"/test/api/boards/{bid}/viewer-only",
        headers={"Authorization": "Bearer invalid_malformed_token"}
    )
    assert r_bad_auth.status_code == 401
    assert "Invalid token" in r_bad_auth.get_json()["detail"]


def test_jwt_stateless_no_session_cookie(rbac_app, rbac_world):
    """Kiểm tra JWT Bearer hoàn toàn stateless: không sinh cookie session trong response."""
    client = rbac_app.test_client()
    bid = rbac_world["board_id"]
    token = rbac_world["tokens"]["owner"]

    res = client.get(
        f"/test/api/boards/{bid}/viewer-only",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    # Không có session cookie được set bởi Flask-Login
    cookies = res.headers.getlist("Set-Cookie")
    session_cookies = [c for c in cookies if "session=" in c]
    assert len(session_cookies) == 0


def test_rbac_owner_has_full_access(rbac_app, rbac_world):
    """Owner có toàn quyền: xem (viewer), sửa (member), xóa (owner)."""
    client = rbac_app.test_client()
    bid = rbac_world["board_id"]
    headers = {"Authorization": f"Bearer {rbac_world['tokens']['owner']}"}

    # 1. Viewer endpoint -> OK
    assert client.get(f"/test/api/boards/{bid}/viewer-only", headers=headers).status_code == 200

    # 2. Member endpoint -> OK
    assert client.post(f"/test/api/boards/{bid}/member-action", headers=headers).status_code == 200

    # 3. Owner endpoint -> OK
    assert client.delete(f"/test/api/boards/{bid}/owner-action", headers=headers).status_code == 200


def test_rbac_member_permissions(rbac_app, rbac_world):
    """Member: được xem và thao tác member, nhưng bị 403 ở action của Owner."""
    client = rbac_app.test_client()
    bid = rbac_world["board_id"]
    headers = {"Authorization": f"Bearer {rbac_world['tokens']['member']}"}

    # 1. Viewer endpoint -> OK
    assert client.get(f"/test/api/boards/{bid}/viewer-only", headers=headers).status_code == 200

    # 2. Member endpoint -> OK
    assert client.post(f"/test/api/boards/{bid}/member-action", headers=headers).status_code == 200

    # 3. Owner endpoint -> 403 Forbidden
    res_owner = client.delete(f"/test/api/boards/{bid}/owner-action", headers=headers)
    assert res_owner.status_code == 403
    assert "You do not have permission" in res_owner.get_json()["detail"]


def test_rbac_viewer_permissions(rbac_app, rbac_world):
    """Viewer: chỉ được xem (200), bị chặn ở member-action (403) và owner-action (403)."""
    client = rbac_app.test_client()
    bid = rbac_world["board_id"]
    headers = {"Authorization": f"Bearer {rbac_world['tokens']['viewer']}"}

    # 1. Viewer endpoint -> OK
    assert client.get(f"/test/api/boards/{bid}/viewer-only", headers=headers).status_code == 200

    # 2. Member endpoint -> 403 Forbidden
    res_mem = client.post(f"/test/api/boards/{bid}/member-action", headers=headers)
    assert res_mem.status_code == 403

    # 3. Owner endpoint -> 403 Forbidden
    res_owner = client.delete(f"/test/api/boards/{bid}/owner-action", headers=headers)
    assert res_owner.status_code == 403


def test_rbac_outsider_is_concealed_404(rbac_app, rbac_world):
    """Người không thuộc board bị chặn bằng 404 (giấu sự tồn tại của board)."""
    client = rbac_app.test_client()
    bid = rbac_world["board_id"]
    headers = {"Authorization": f"Bearer {rbac_world['tokens']['outsider']}"}

    res = client.get(f"/test/api/boards/{bid}/viewer-only", headers=headers)
    assert res.status_code == 404
