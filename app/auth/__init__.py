from flask import Blueprint
#  JWT Bearer stateless cho /api (khong tao session cookie)
from app.auth import stateless_jwt  # noqa: E402,F401
auth = Blueprint('auth', __name__)

from app.auth import routes
from app.auth.jwt_helpers import jwt_api_required, get_jwt_user, get_jwt_user_id
from app.auth.rbac import (
    board_role_required,
    role_required,
    owner_required,
    member_required,
    viewer_required,
    get_request_user,
)
from app.auth.sanitizer import clean_text, clean_html, sanitize_task, sanitize_comment
