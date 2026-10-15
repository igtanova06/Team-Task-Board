from flask_wtf import FlaskForm
from werkzeug.datastructures import MultiDict
from wtforms import StringField, PasswordField, TextAreaField, SelectField, IntegerField, DateField, BooleanField
from wtforms.validators import DataRequired, Length, Optional, NumberRange

from app.models import TaskStatus, TaskPriority


class LoginForm(FlaskForm):
    identity = StringField("Email or username", validators=[
        DataRequired(message="Enter your email or username."), Length(max=100)])
    password = PasswordField("Password", validators=[
        DataRequired(message="Enter your password."), Length(max=128)])
    remember = BooleanField("Keep me signed in")


class JsonForm(FlaskForm):
    """FlaskForm fed from a JSON dict (CSRF is enforced globally by CSRFProtect via X-CSRFToken)."""

    class Meta:
        csrf = False

    @classmethod
    def from_json(cls, data):
        formdata = MultiDict()
        for key, value in (data or {}).items():
            if key in cls._fields_set():
                formdata[key] = "" if value is None else str(value)
        return cls(formdata=formdata)

    @classmethod
    def _fields_set(cls):
        return {n for n in dir(cls) if hasattr(getattr(cls, n), "field_class")}


class TaskForm(JsonForm):
    title = StringField("Title", filters=[lambda v: v.strip() if isinstance(v, str) else v], validators=[
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
        DataRequired(message="Status is required.")])


class CommentForm(JsonForm):
    content = TextAreaField("Comment", filters=[lambda v: v.strip() if isinstance(v, str) else v], validators=[
        DataRequired(message="Comment cannot be empty."),
        Length(max=1000, message="Comment must be 1000 characters or fewer.")])
