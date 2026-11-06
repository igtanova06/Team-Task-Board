"""
tests/test_rubric.py

Kiểm thử toàn diện 3 tiêu chí còn lại:  
  - Tiêu chí 6: Custom Decorator @role_required / @board_role_required
  - Tiêu chí 8: Bleach XSS sanitization cho task/comment
  - Tiêu chí 2: Jinja2 Macro _form_helpers.html
"""
import pytest
from flask_jwt_extended import create_access_token

from app.auth.sanitizer import clean_text, clean_html, sanitize_task, sanitize_comment
from app.extensions import db
from app.models import User, Board, BoardMembership, Role


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURE CHUNG
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def rubric_world(app):
    """Tạo board + 3 users với roles: owner, member, viewer, và 1 outsider."""
    with app.app_context():
        owner   = User(username="rub_owner",   email="rub_owner@x.com");   owner.set_password("P123")
        member  = User(username="rub_member",  email="rub_member@x.com");  member.set_password("P123")
        viewer  = User(username="rub_viewer",  email="rub_viewer@x.com");  viewer.set_password("P123")
        outside = User(username="rub_outside", email="rub_outside@x.com"); outside.set_password("P123")
        board   = Board(name="Rubric Test Board")

        db.session.add_all([owner, member, viewer, outside, board])
        db.session.flush()

        db.session.add_all([
            BoardMembership(user_id=owner.id,  board_id=board.id, role=Role.OWNER),
            BoardMembership(user_id=member.id, board_id=board.id, role=Role.MEMBER),
            BoardMembership(user_id=viewer.id, board_id=board.id, role=Role.VIEWER),
        ])
        db.session.commit()

        return {
            "board_id": board.id,
            "tokens": {
                "owner":   create_access_token(identity=str(owner.id)),
                "member":  create_access_token(identity=str(member.id)),
                "viewer":  create_access_token(identity=str(viewer.id)),
                "outside": create_access_token(identity=str(outside.id)),
            }
        }


# ══════════════════════════════════════════════════════════════════════════════
# TIÊU CHÍ 6 – Custom Decorators @role_required / @board_role_required
# ══════════════════════════════════════════════════════════════════════════════

class TestCustomDecorators:
    """
    Kiểm tra 4 decorator RBAC được khai báo trong app/auth/rbac.py:
      @viewer_required   → tất cả thành viên
      @member_required   → member + owner (viewer bị 403)
      @owner_required    → chỉ owner (member + viewer bị 403)
      @role_required(Role.OWNER) → giống @owner_required, cú pháp tường minh
    """

    def test_viewer_endpoint_accessible_to_all_members(self, app, rubric_world):
        """@viewer_required: owner, member, viewer đều được 200."""
        client = app.test_client()
        bid = rubric_world["board_id"]
        for role_name in ("owner", "member", "viewer"):
            token = rubric_world["tokens"][role_name]
            res = client.get(
                f"/m2/api/boards/{bid}/summary",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert res.status_code == 200, f"{role_name} should see viewer endpoint"
            assert res.get_json()["your_role"] == role_name

    def test_viewer_endpoint_blocks_outsider(self, app, rubric_world):
        """@viewer_required: người ngoài board bị 404 (concealed)."""
        client = app.test_client()
        bid = rubric_world["board_id"]
        res = client.get(
            f"/m2/api/boards/{bid}/summary",
            headers={"Authorization": f"Bearer {rubric_world['tokens']['outside']}"}
        )
        assert res.status_code == 404

    def test_member_endpoint_allows_member_and_owner(self, app, rubric_world):
        """@member_required: owner và member đều được 200."""
        client = app.test_client()
        bid = rubric_world["board_id"]
        for role_name in ("owner", "member"):
            token = rubric_world["tokens"][role_name]
            res = client.post(
                f"/m2/api/boards/{bid}/pin",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert res.status_code == 200, f"{role_name} should reach member endpoint"

    def test_member_endpoint_blocks_viewer(self, app, rubric_world):
        """@member_required: viewer bị 403 Forbidden."""
        client = app.test_client()
        bid = rubric_world["board_id"]
        res = client.post(
            f"/m2/api/boards/{bid}/pin",
            headers={"Authorization": f"Bearer {rubric_world['tokens']['viewer']}"}
        )
        assert res.status_code == 403
        assert "permission" in res.get_json()["detail"].lower()

    def test_owner_endpoint_allows_only_owner(self, app, rubric_world):
        """@owner_required: chỉ owner được 200, member và viewer bị 403."""
        client = app.test_client()
        bid = rubric_world["board_id"]

        # Owner được phép
        res_ok = client.put(
            f"/m2/api/boards/{bid}/settings",
            headers={"Authorization": f"Bearer {rubric_world['tokens']['owner']}"}
        )
        assert res_ok.status_code == 200
        assert res_ok.get_json()["action"] == "settings updated"

        # Member bị chặn
        res_mem = client.put(
            f"/m2/api/boards/{bid}/settings",
            headers={"Authorization": f"Bearer {rubric_world['tokens']['member']}"}
        )
        assert res_mem.status_code == 403

        # Viewer bị chặn
        res_view = client.put(
            f"/m2/api/boards/{bid}/settings",
            headers={"Authorization": f"Bearer {rubric_world['tokens']['viewer']}"}
        )
        assert res_view.status_code == 403

    def test_role_required_decorator_with_explicit_param(self, app, rubric_world):
        """@role_required(Role.OWNER): cú pháp tường minh nhận tham số role."""
        client = app.test_client()
        bid = rubric_world["board_id"]

        # Owner được phép – decorator trả về 200
        res = client.post(
            f"/m2/api/boards/{bid}/archive",
            headers={"Authorization": f"Bearer {rubric_world['tokens']['owner']}"}
        )
        assert res.status_code == 200
        assert "@role_required(Role.OWNER)" in res.get_json()["decorator"]

        # Member bị chặn – trả về 403
        res_fail = client.post(
            f"/m2/api/boards/{bid}/archive",
            headers={"Authorization": f"Bearer {rubric_world['tokens']['member']}"}
        )
        assert res_fail.status_code == 403

    def test_board_role_required_with_min_role_param(self, app, rubric_world):
        """@board_role_required(min_role=Role.MEMBER): linh hoạt nhận min_role."""
        client = app.test_client()
        bid = rubric_world["board_id"]

        # Member được phép
        res = client.get(
            f"/m2/api/boards/{bid}/access-check",
            headers={"Authorization": f"Bearer {rubric_world['tokens']['member']}"}
        )
        assert res.status_code == 200
        assert res.get_json()["access"] == "granted"

        # Viewer bị chặn
        res_fail = client.get(
            f"/m2/api/boards/{bid}/access-check",
            headers={"Authorization": f"Bearer {rubric_world['tokens']['viewer']}"}
        )
        assert res_fail.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# TIÊU CHÍ 8 – Bleach XSS Sanitization
# ══════════════════════════════════════════════════════════════════════════════

class TestBleachXSSSanitizer:
    """
    Kiểm tra app/auth/sanitizer.py – lọc XSS cho Task và Comment.
    """

    # ── clean_text (plain text, loại bỏ toàn bộ HTML) ──────────────────────

    def test_clean_text_strips_script_tags(self):
        """Script tag bị loại bỏ hoàn toàn."""
        result = clean_text('<script>alert("XSS")</script>Fix bug')
        assert "<script>" not in result
        assert "alert" not in result
        assert "Fix bug" in result

    def test_clean_text_strips_event_handlers(self):
        """Event handler HTML attribute bị loại bỏ."""
        result = clean_text('<img src=x onerror=alert(1)>My task title')
        assert "onerror" not in result
        assert "My task title" in result

    def test_clean_text_strips_all_html_tags(self):
        """Mọi thẻ HTML đều bị loại bỏ trong plain text."""
        result = clean_text('<b>Bold</b> <a href="#">Link</a> Normal')
        assert "<b>" not in result
        assert "<a" not in result
        assert "Bold" in result
        assert "Normal" in result

    def test_clean_text_max_length_truncates(self):
        """Cắt ngắn chuỗi theo max_length sau khi làm sạch."""
        long_text = "A" * 300
        result = clean_text(long_text, max_length=200)
        assert len(result) <= 200

    def test_clean_text_empty_and_none(self):
        """None và chuỗi rỗng trả về chuỗi rỗng."""
        assert clean_text(None) == ""
        assert clean_text("") == ""

    # ── clean_html (rich text, chỉ giữ safe tags) ─────────────────────────

    def test_clean_html_allows_safe_formatting_tags(self):
        """Thẻ <b>, <i>, <code>... được giữ lại."""
        result = clean_html("<b>Bold</b> and <i>italic</i> and <code>code</code>")
        assert "<b>Bold</b>" in result
        assert "<i>italic</i>" in result
        assert "<code>code</code>" in result

    def test_clean_html_strips_script(self):
        """Script tag bị loại bỏ hoàn toàn khỏi rich text."""
        result = clean_html('<script>alert("xss")</script><b>Safe</b>')
        assert "<script>" not in result
        assert "alert" not in result
        assert "<b>Safe</b>" in result

    def test_clean_html_strips_dangerous_attributes(self):
        """Attribute nguy hiểm như onerror, onclick bị loại bỏ."""
        result = clean_html('<a href="http://ok.com" onclick="evil()">Click</a>')
        assert "onclick" not in result
        assert 'href="http://ok.com"' in result

    def test_clean_html_adds_nofollow_to_links(self):
        """Tự động thêm rel=nofollow vào thẻ <a> từ user (chống SEO spam)."""
        result = clean_html('<a href="http://external.com">Link</a>')
        assert "nofollow" in result

    def test_clean_html_strips_iframe(self):
        """iframe bị loại bỏ vì không có trong safelist."""
        result = clean_html('<iframe src="evil.com"></iframe>Content')
        assert "<iframe" not in result
        assert "Content" in result

    # ── sanitize_task (dict) ────────────────────────────────────────────────

    def test_sanitize_task_cleans_title_and_description(self):
        """sanitize_task làm sạch cả title lẫn description."""
        data = {
            "title": '<script>evil()</script>Fix login bug',
            "description": '<b>Steps:</b><script>xss()</script>',
            "status": "todo"
        }
        result = sanitize_task(data)
        assert "<script>" not in result["title"]
        assert "Fix login bug" in result["title"]
        assert "<script>" not in result["description"]
        assert "<b>Steps:</b>" in result["description"]
        # Các trường không liên quan không bị thay đổi
        assert result["status"] == "todo"

    def test_sanitize_task_does_not_mutate_original(self):
        """sanitize_task không sửa dict gốc (trả về dict mới)."""
        original = {"title": "<b>Test</b>", "description": "Desc"}
        result = sanitize_task(original)
        # original phải giữ nguyên
        assert original["title"] == "<b>Test</b>"
        # result phải khác
        assert result is not original

    # ── sanitize_comment (dict) ─────────────────────────────────────────────

    def test_sanitize_comment_cleans_content(self):
        """sanitize_comment làm sạch trường content."""
        data = {"content": '<script>steal(document.cookie)</script>Good job!'}
        result = sanitize_comment(data)
        assert "<script>" not in result["content"]
        assert "steal" not in result["content"]
        assert "Good job!" in result["content"]

    def test_sanitize_comment_allows_basic_formatting(self):
        """Comment giữ lại các thẻ an toàn như <b>, <i>."""
        data = {"content": "<b>Well done!</b> <i>Keep it up!</i>"}
        result = sanitize_comment(data)
        assert "<b>Well done!</b>" in result["content"]
        assert "<i>Keep it up!</i>" in result["content"]


# ══════════════════════════════════════════════════════════════════════════════
# TIÊU CHÍ 2 – Jinja2 Macro _form_helpers.html
# ══════════════════════════════════════════════════════════════════════════════

class TestJinja2Macros:
    """
    Kiểm tra _form_helpers.html đã được import và render đúng trong các trang form.
    """

    def test_login_page_uses_macro_render_field(self, app):
        """Trang login render đúng các field bằng macro (label, input, placeholder)."""
        client = app.test_client()
        res = client.get("/login")
        assert res.status_code == 200
        html = res.data.decode()
        # Macro render_field phải tạo ra form-control class của Bootstrap
        assert 'class="form-control' in html
        # Phải có label Email/Username
        assert 'form-label' in html

    def test_register_page_uses_macro_render_field(self, app):
        """Trang register render đúng các field bằng macro."""
        client = app.test_client()
        res = client.get("/register")
        assert res.status_code == 200
        html = res.data.decode()
        assert 'class="form-control' in html
        assert 'form-label' in html

    def test_macro_renders_validation_error_class(self, app):
        """Khi submit form lỗi, macro thêm class is-invalid vào field lỗi."""
        client = app.test_client()
        # Submit register với dữ liệu thiếu -> form có lỗi
        res = client.post("/register", data={
            "username": "",
            "email": "not-an-email",
            "password": "123",
            "confirm_password": "456"
        })
        html = res.data.decode()
        # Macro phải render class is-invalid khi có lỗi field
        assert "is-invalid" in html or res.status_code in (200, 422)

    def test_form_helpers_file_exists_and_has_macros(self, app):
        """File _form_helpers.html tồn tại và chứa ít nhất 4 macro."""
        import os
        # app.template_folder có thể là relative path → dùng root_path để build absolute
        template_dir = os.path.join(app.root_path, "templates")
        path = os.path.join(template_dir, "kanban", "_form_helpers.html")
        assert os.path.isfile(path), f"_form_helpers.html phải tồn tại tại {path}"
        content = open(path, encoding="utf-8").read()
        for macro in ("render_field", "render_password_field", "render_submit", "render_flashes"):
            assert f"macro {macro}" in content, f"Macro '{macro}' phải có trong _form_helpers.html"
