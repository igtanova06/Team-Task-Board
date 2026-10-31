"""Server-side validation (Flask-WTF) for JSON payloads sent to /api (Boards, Tasks, Members, Comments)."""
from flask_wtf import FlaskForm
from werkzeug.datastructures import MultiDict
from wtforms import StringField, TextAreaField, SelectField, IntegerField, DateField
from wtforms.validators import DataRequired, Length, Optional, NumberRange

from app.models import Role, TaskStatus, TaskPriority


def _strip(v):
    return v.strip() if isinstance(v, str) else v


class JsonForm(FlaskForm):
    """A FlaskForm fed from a JSON dict. CSRF for cookie sessions is checked in app.main.setup."""

    class Meta:
        csrf = False

    @classmethod
    def from_json(cls, data):
        names = {n for n in dir(cls) if hasattr(getattr(cls, n), "field_class")}
        formdata = MultiDict()
        for key, value in (data or {}).items():
            if key in names:
                formdata[key] = "" if value is None else str(value)
        return cls(formdata=formdata)

    def error_summary(self):
        field, msgs = next(iter(self.errors.items()))
        return msgs[0] if isinstance(msgs, list) else str(msgs)


# ---------------------------------------------------------------------------
# Board & Member Forms
# ---------------------------------------------------------------------------

class BoardForm(JsonForm):
    """Validation for creating or updating a board."""
    name = StringField("Name", filters=[_strip], validators=[
        DataRequired(message="Board name is required."),
        Length(max=100, message="Board name must be 100 characters or fewer.")
    ])
    description = TextAreaField("Description", filters=[_strip], validators=[
        Optional(),
        Length(max=2000, message="Description must be 2000 characters or fewer.")
    ])


class AddMemberForm(JsonForm):
    """Validation for adding a member to a board."""
    user_id = IntegerField("User ID", validators=[Optional(), NumberRange(min=1)])
    identity = StringField("Username or Email", filters=[_strip], validators=[Optional()])
    role = SelectField("Role", choices=[(r, r) for r in Role.ALL], default=Role.MEMBER, validators=[
        DataRequired(message="Role is required.")
    ])

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators=extra_validators):
            return False
        if not self.user_id.data and not self.identity.data:
            self.user_id.errors.append("Either user_id or identity (username/email) is required.")
            return False
        return True


class UpdateMemberRoleForm(JsonForm):
    """Validation for updating a member's role."""
    role = SelectField("Role", choices=[(r, r) for r in Role.ALL], validators=[
        DataRequired(message="Role is required.")
    ])


# ---------------------------------------------------------------------------
# Task & Comment Forms
# ---------------------------------------------------------------------------

class TaskForm(JsonForm):
    title = StringField("Title", filters=[_strip], validators=[
        DataRequired(message="Title is required."),
        Length(max=200, message="Title must be 200 characters or fewer.")
    ])
    description = TextAreaField("Description", validators=[
        Optional(), Length(max=2000, message="Description must be 2000 characters or fewer.")
    ])
    status = SelectField("Status", choices=[(s, s) for s in TaskStatus.ALL], validators=[
        DataRequired(message="Status is required.")
    ])
    priority = SelectField("Priority", choices=[(p, p) for p in TaskPriority.ALL], validators=[
        DataRequired(message="Priority is required.")
    ])
    deadline = DateField("Deadline", format="%Y-%m-%d", validators=[Optional()])
    assigned_to = IntegerField("Assignee", validators=[Optional(), NumberRange(min=1)])


class StatusForm(JsonForm):
    status = SelectField("Status", choices=[(s, s) for s in TaskStatus.ALL], validators=[
        DataRequired(message="Invalid task status.")
    ])


class CommentForm(JsonForm):
    content = TextAreaField("Comment", filters=[_strip], validators=[
        DataRequired(message="Comment content is required."),
        Length(max=1000, message="Comment must be 1000 characters or fewer.")
    ])

