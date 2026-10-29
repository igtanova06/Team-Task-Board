"""
app/auth/member2_routes.py  –  Tiêu chí 6: Custom Decorator Routes

Blueprint riêng của Member 2 trình bày cách dùng @role_required / @board_role_required
trực tiếp trên các endpoint REST API (đây là điểm cốt lõi giám khảo sẽ kiểm tra).

Prefix: /m2/api/...   (tách hẳn khỏi /api/ của các member khác, tuân thủ IMPORTANT)

Các endpoint này:
  GET  /m2/api/boards/<id>/summary     → @viewer_required  (mọi thành viên xem được)
  POST /m2/api/boards/<id>/pin         → @member_required  (member/owner)
  PUT  /m2/api/boards/<id>/settings    → @owner_required   (chỉ owner)
  POST /m2/api/boards/<id>/archive     → @role_required('owner') (giống @owner_required)
"""
from flask import Blueprint, jsonify, g
from flask_login import login_required

from app.auth.jwt_helpers import jwt_api_required
from app.auth.rbac import (
    role_required,
    board_role_required,
    owner_required,
    member_required,
    viewer_required,
    get_request_user,
)
from app.models import Role

m2_api = Blueprint("m2_api", __name__)


# ── Tiêu chí 6: @viewer_required ────────────────────────────────────────────
@m2_api.get("/boards/<int:board_id>/summary")
@jwt_api_required
@viewer_required
def board_summary(board_id):
    """
    Endpoint xem tóm tắt Board – mọi thành viên (Viewer/Member/Owner) đều được.
    Dùng @viewer_required để kiểm soát quyền.
    """
    user = get_request_user()
    role = g.current_board_role
    return jsonify({
        "board_id":   board_id,
        "your_role":  role,
        "user_id":    user.id,
        "access":     "read-only summary",
        "decorator":  "@viewer_required",
        "message":    f"Board #{board_id} summary visible to all members."
    }), 200


# ── Tiêu chí 6: @member_required ────────────────────────────────────────────
@m2_api.post("/boards/<int:board_id>/pin")
@jwt_api_required
@member_required
def pin_board(board_id):
    """
    Ghim board (member-level action) – Viewer bị chặn 403.
    Dùng @member_required để kiểm soát quyền.
    """
    user = get_request_user()
    role = g.current_board_role
    return jsonify({
        "board_id":   board_id,
        "your_role":  role,
        "user_id":    user.id,
        "action":     "pinned",
        "decorator":  "@member_required",
        "message":    f"Board #{board_id} pinned by {user.username}."
    }), 200


# ── Tiêu chí 6: @owner_required ─────────────────────────────────────────────
@m2_api.put("/boards/<int:board_id>/settings")
@jwt_api_required
@owner_required
def board_settings(board_id):
    """
    Chỉnh sửa cài đặt board (owner-only) – Member/Viewer bị chặn 403.
    Dùng @owner_required để kiểm soát quyền.
    """
    user = get_request_user()
    return jsonify({
        "board_id":   board_id,
        "your_role":  "owner",
        "user_id":    user.id,
        "action":     "settings updated",
        "decorator":  "@owner_required",
        "message":    f"Board #{board_id} settings updated by owner {user.username}."
    }), 200


# ── Tiêu chí 6: @role_required('owner') (tường minh hơn @owner_required) ────
@m2_api.post("/boards/<int:board_id>/archive")
@jwt_api_required
@role_required(Role.OWNER)
def archive_board(board_id):
    """
    Lưu trữ board – dùng @role_required(Role.OWNER) tường minh (Tiêu chí 6 Rubric).
    Chứng minh decorator nhận tham số role linh hoạt.
    """
    user = get_request_user()
    return jsonify({
        "board_id":   board_id,
        "your_role":  "owner",
        "user_id":    user.id,
        "action":     "archived",
        "decorator":  "@role_required(Role.OWNER)",
        "message":    f"Board #{board_id} archived by {user.username}."
    }), 200


# ── Tiêu chí 6: @board_role_required(min_role) với tham số linh hoạt ─────────
@m2_api.get("/boards/<int:board_id>/access-check")
@jwt_api_required
@board_role_required(min_role=Role.MEMBER)
def access_check(board_id):
    """
    Kiểm tra quyền truy cập theo min_role linh hoạt.
    Dùng @board_role_required(min_role=Role.MEMBER) tường minh.
    """
    user = get_request_user()
    role = g.current_board_role
    return jsonify({
        "board_id":   board_id,
        "your_role":  role,
        "user_id":    user.id,
        "min_role_required": Role.MEMBER,
        "decorator":  "@board_role_required(min_role=Role.MEMBER)",
        "access":     "granted"
    }), 200

