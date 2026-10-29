"""
app/auth/jwt_helpers.py

JWT Bearer Authentication - Tách biệt hoàn toàn khỏi Flask-Login session.
- Flask-Login session: Dành cho trình duyệt web (cookie-based).
- JWT Bearer Token: Dành cho REST API clients (Authorization: Bearer <token>), stateless, KHÔNG tạo session cookie.
"""
from functools import wraps
from flask import request, jsonify, g
from flask_jwt_extended import decode_token
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from app.extensions import db


def get_jwt_user():
    """Lấy user được xác thực qua JWT từ flask.g (nếu có)."""
    return getattr(g, "jwt_user", None)


def get_jwt_user_id():
    """Lấy user_id được xác thực qua JWT từ flask.g (nếu có)."""
    return getattr(g, "jwt_user_id", None)


def jwt_api_required(fn):
    """
    Decorator bắt buộc request phải có header `Authorization: Bearer <token>`.
    Xác thực token và lưu user vào `g.jwt_user` và `g.jwt_user_id`.
    
    TUYỆT ĐỐI KHÔNG gọi `login_user()`, giữ cho request hoàn toàn stateless.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({
                "detail": "Missing or invalid Authorization header. Expected 'Bearer <token>'."
            }), 401

        token = auth_header.split(" ", 1)[1].strip()
        if not token:
            return jsonify({"detail": "Bearer token is empty."}), 401

        try:
            decoded = decode_token(token)
            uid = decoded.get("sub")
            if uid is None:
                return jsonify({"detail": "Token payload missing subject identity."}), 401

            from app.models import User
            user = db.session.get(User, int(uid))
            if user is None:
                return jsonify({"detail": "User not found or no longer active."}), 401

            # Lưu vào g cho request hiện tại, không đụng tới session
            g.jwt_user = user
            g.jwt_user_id = user.id
            g.jwt_claims = decoded

        except ExpiredSignatureError:
            return jsonify({"detail": "Token has expired. Please log in again."}), 401
        except (InvalidTokenError, Exception) as exc:
            return jsonify({"detail": f"Invalid token: {str(exc)}"}), 401

        return fn(*args, **kwargs)
    return wrapper
