"""
app/auth/rbac.py

Role-Based Access Control (RBAC) Decorators cho Board & Membership APIs.
Đáp ứng Tiêu chí 6 trong Rubric:
- 3 Roles: owner, member, viewer
- Decorators kiểm tra quyền: @role_required, @board_role_required, @owner_required, @member_required, @viewer_required
- Hỗ trợ cả 2 luồng: JWT Bearer client (g.jwt_user) và Web session (current_user)
- Kiểm tra quyền sở hữu (ownership) & ngăn chặn IDOR
"""
from functools import wraps
from flask import request, jsonify, g
from flask_login import current_user

from app.extensions import db
from app.models import Role, BoardMembership, Task


ROLE_RANK = {
    Role.VIEWER: 1,
    Role.MEMBER: 2,
    Role.OWNER: 3,
}


def get_request_user():
    """Lấy user hiện tại từ JWT Bearer (g.jwt_user) hoặc Web session (current_user)."""
    jwt_user = getattr(g, "jwt_user", None)
    if jwt_user is not None:
        return jwt_user
    if current_user and current_user.is_authenticated:
        return current_user
    return None


def resolve_board_id(kwargs):
    """Trích xuất board_id từ URL parameters hoặc qua task_id."""
    if "board_id" in kwargs:
        return kwargs["board_id"]
    if "task_id" in kwargs:
        task = db.session.get(Task, kwargs["task_id"])
        if task:
            return task.board_id
    if request.is_json:
        data = request.get_json(silent=True) or {}
        if "board_id" in data:
            return data["board_id"]
    return None


def board_role_required(min_role=Role.VIEWER):
    """
    Decorator kiểm tra vai trò tối thiểu (min_role) trong Board.
    - Owner: Quản lý board, quản lý thành viên, xóa board, xóa task bất kỳ.
    - Member: Tạo task, sửa task được giao/do mình tạo.
    - Viewer: Chỉ xem nội dung và bình luận.
    
    Quy tắc an toàn:
    - Nếu không phải thành viên -> 404 (giấu sự tồn tại của board theo Lean baseline).
    - Nếu là thành viên nhưng không đủ quyền -> 403 Forbidden.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = get_request_user()
            if user is None:
                return jsonify({"detail": "Authentication required."}), 401

            board_id = resolve_board_id(kwargs)
            if board_id is None:
                return jsonify({"detail": "Board context could not be determined."}), 400

            membership = BoardMembership.query.filter_by(
                user_id=user.id,
                board_id=board_id
            ).first()

            if membership is None:
                return jsonify({"detail": "Board not found or access denied."}), 404

            user_rank = ROLE_RANK.get(membership.role.lower(), 0)
            required_rank = ROLE_RANK.get(min_role.lower(), 0)

            if user_rank < required_rank:
                return jsonify({
                    "detail": "You do not have permission to do that.",
                    "required_role": min_role,
                    "your_role": membership.role
                }), 403

            g.current_board_id = board_id
            g.current_membership = membership
            g.current_board_role = membership.role

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def role_required(min_role=Role.VIEWER):
    """
    Custom decorator @role_required theo yêu cầu Tiêu chí 6 của Rubric.
    Alias trực tiếp của @board_role_required.
    """
    return board_role_required(min_role)


def owner_required(fn):
    """Chỉ Owner của Board được phép thực hiện (vd: Xóa board, phân quyền thành viên)."""
    return board_role_required(Role.OWNER)(fn)


def member_required(fn):
    """Member hoặc Owner được phép (Viewer bị chặn, vd: Tạo task)."""
    return board_role_required(Role.MEMBER)(fn)


def viewer_required(fn):
    """Mọi thành viên (Viewer, Member, Owner) được phép xem."""
    return board_role_required(Role.VIEWER)(fn)
