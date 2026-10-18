"""Server-side validation (Flask-WTF) for JSON payloads sent to /api."""
from flask_wtf import FlaskForm
from werkzeug.datastructures import MultiDict
from wtforms import StringField, TextAreaField, SelectField, IntegerField, DateField
from wtforms.validators import DataRequired, Length, Optional, NumberRange

from app.models import TaskStatus, TaskPriority


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


class TaskForm(JsonForm):
    title = StringField("Title", filters=[_strip], validators=[
        DataRequired(message="Title is required."),
        Length(max=200, message="Title must be 200 characters or fewer.")])
    description = TextAreaField("Description", validators=[
        Optional(), Length(max=2000, message="Description must be 2000 characters or fewer.")])
    status = SelectField("Status", choices=[(s, s) for s in TaskStatus.ALL], validators=[
        DataRequired(message="Status is required.")])
    priority = SelectField("Priority", choices=[(p, p) for p in TaskPriority.ALL], validators=[
        DataRequired(message="Priority is required.")])
    deadline = DateField("Deadline", format="%Y-%m-%d", validators=[Optional()])
    assigned_to = IntegerField("Assignee", validators=[Optional(), NumberRange(min=1)])


class StatusForm(JsonForm):
    status = SelectField("Status", choices=[(s, s) for s in TaskStatus.ALL], validators=[
        DataRequired(message="Invalid task status.")])


class CommentForm(JsonForm):
    content = TextAreaField("Comment", filters=[_strip], validators=[
        DataRequired(message="Comment content is required."),
        Length(max=1000, message="Comment must be 1000 characters or fewer.")])
