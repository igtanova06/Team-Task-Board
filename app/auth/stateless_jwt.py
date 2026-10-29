"""
app/auth/stateless_jwt.py  -  tach JWT Bearer khoi Flask-Login session (/api that).

Van de: app.api.guards.authenticated_user() goi login_user() khi gap Bearer token,
nen moi request Bearer deu bi ghi session cookie (khong con stateless).

Cach xu ly KHONG sua guards.py: dang ky mot `request_loader` cho Flask-Login.
Flask-Login se goi loader nay khi session khong co user. User duoc nap vao
`current_user` cho rieng request do, KHONG ghi session va KHONG Set-Cookie, nen
`authenticated_user()` thay current_user da xac thuc va khong bao gio toi nhanh login_user().
"""
from flask import g
from flask_jwt_extended import decode_token

from app.extensions import db
from app.main.setup import login_manager


@login_manager.request_loader
def load_user_from_bearer(req):
    """Tra ve User neu request co `Authorization: Bearer <jwt hop le>`, nguoc lai None."""
    header = req.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    token = header.split(" ", 1)[1].strip()
    if not token:
        return None
    try:
        decoded = decode_token(token)
        uid = decoded.get("sub")
        if uid is None:
            return None
        from app.models import User
        user = db.session.get(User, int(uid))
    except Exception:
        return None
    if user is not None:
        g.jwt_user, g.jwt_user_id, g.jwt_claims = user, user.id, decoded
    return user
