"""
app/auth/sanitizer.py  –  Tiêu chí 8: XSS Prevention với bleach

Cung cấp hàm làm sạch nội dung người dùng nhập (Task title/description, Comment)
trước khi lưu vào Database, bổ sung thêm lớp bảo vệ ngoài auto-escape của Jinja2.

Cách dùng (cho các thành viên khác import vào):
    from app.auth.sanitizer import clean_text, clean_html, sanitize_task, sanitize_comment

NGUYÊN TẮC: File này CHỈ định nghĩa hàm helper.
Không import trực tiếp model hay sửa code của thành viên khác.
"""
import re
import bleach

# ---------------------------------------------------------------------------
# Cấu hình SafeList (allowlist)
# ---------------------------------------------------------------------------

# Không cho phép bất kỳ thẻ HTML nào trong text thuần (title, username…)
_PLAIN_TAGS: list[str] = []
_PLAIN_ATTRS: dict = {}

# Cho phép một số thẻ định dạng cơ bản trong mô tả / comment
_RICH_TAGS: list[str] = [
    "b", "i", "u", "em", "strong", "code", "pre",
    "p", "br", "ul", "ol", "li", "blockquote", "a",
]
_RICH_ATTRS: dict = {
    "a": ["href", "title", "rel"],
}

# Tự động thêm rel="nofollow noopener" vào mọi thẻ <a> từ user
_LINK_CALLBACKS = [bleach.callbacks.nofollow]

# Các thẻ nguy hiểm có nội dung phải bị xóa hoàn toàn (cả nội dung bên trong)
_DANGEROUS_TAGS_RE = re.compile(
    r"<(script|style|iframe|object|embed|form|input|textarea|button|select)"
    r"[^>]*>.*?</(script|style|iframe|object|embed|form|input|textarea|button|select)>",
    re.DOTALL | re.IGNORECASE,
)
# Xử lý thẻ tự đóng nguy hiểm (vd: <script src=.../>)
_DANGEROUS_SELF_CLOSE_RE = re.compile(
    r"<(script|style|iframe|object|embed|input)[^>]*/?>",
    re.IGNORECASE,
)


def _strip_dangerous(value: str) -> str:
    """
    Bước 1: Dùng regex xóa toàn bộ nội dung bên trong thẻ nguy hiểm
    (bleach 6.x strip=True chỉ xóa thẻ nhưng giữ nội dung bên trong,
     nên cần regex này để xóa cả payload như `alert(1)` hay `steal(cookie)`).
    """
    result = _DANGEROUS_TAGS_RE.sub("", value)
    result = _DANGEROUS_SELF_CLOSE_RE.sub("", result)
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def clean_text(value: str | None, max_length: int | None = None) -> str:
    """
    Làm sạch văn bản thuần (plain text).
    - Bước 1: Xóa toàn bộ nội dung nguy hiểm (script, style...) bằng regex.
    - Bước 2: Bleach loại bỏ tất cả thẻ HTML còn lại.
    - Dùng cho: Task title, username, tên Board…

    Args:
        value:      Chuỗi đầu vào từ người dùng.
        max_length: Nếu có, cắt ngắn chuỗi sau khi làm sạch.

    Returns:
        Chuỗi đã làm sạch, an toàn để lưu DB và hiển thị.

    Example:
        clean_text('<script>alert(1)</script>Fix bug')
        → 'Fix bug'
    """
    if not value:
        return ""
    value = _strip_dangerous(str(value))
    result = bleach.clean(value, tags=_PLAIN_TAGS, attributes=_PLAIN_ATTRS, strip=True)
    result = result.strip()
    if max_length:
        result = result[:max_length]
    return result


def clean_html(value: str | None, max_length: int | None = None) -> str:
    """
    Làm sạch nội dung có thể chứa HTML giới hạn (rich text).
    - Bước 1: Xóa toàn bộ nội dung nguy hiểm (script, style...) bằng regex.
    - Bước 2: Bleach chỉ giữ lại các thẻ trong _RICH_TAGS (b, i, code, a…).
    - Tự động thêm rel="nofollow noopener" vào thẻ <a>.
    - Dùng cho: Task description, Comment content.

    Args:
        value:      Chuỗi đầu vào từ người dùng.
        max_length: Nếu có, cắt ngắn chuỗi sau khi làm sạch.

    Returns:
        Chuỗi HTML đã được lọc an toàn.

    Example:
        clean_html('<script>xss</script><b>Bold text</b>')
        → '<b>Bold text</b>'
    """
    if not value:
        return ""
    value = _strip_dangerous(str(value))
    result = bleach.linkify(
        bleach.clean(
            value,
            tags=_RICH_TAGS,
            attributes=_RICH_ATTRS,
            strip=True,
        ),
        callbacks=_LINK_CALLBACKS,
    )
    result = result.strip()
    if max_length:
        result = result[:max_length]
    return result


def sanitize_task(data: dict) -> dict:
    """
    Làm sạch toàn bộ các trường của một Task payload trước khi lưu DB.
    Trả về dict mới đã được làm sạch, không sửa dict gốc.

    Dùng cho (member khác import vào route):
        from app.auth.sanitizer import sanitize_task
        data = sanitize_task(request.get_json())

    Các trường được xử lý:
        title       → clean_text  (plain text, max 200 ký tự)
        description → clean_html  (rich text, max 2000 ký tự)
    """
    cleaned = dict(data or {})
    if "title" in cleaned:
        cleaned["title"] = clean_text(cleaned["title"], max_length=200)
    if "description" in cleaned:
        cleaned["description"] = clean_html(cleaned["description"], max_length=2000)
    return cleaned


def sanitize_comment(data: dict) -> dict:
    """
    Làm sạch toàn bộ các trường của một Comment payload trước khi lưu DB.

    Dùng cho (member khác import vào route):
        from app.auth.sanitizer import sanitize_comment
        data = sanitize_comment(request.get_json())

    Các trường được xử lý:
        content → clean_html (rich text, max 1000 ký tự)
    """
    cleaned = dict(data or {})
    if "content" in cleaned:
        cleaned["content"] = clean_html(cleaned["content"], max_length=1000)
    return cleaned
