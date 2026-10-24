"""Server-side validation for Board and Member JSON payloads."""
from wtforms import StringField, TextAreaField, SelectField, IntegerField
from wtforms.validators import DataRequired, Length, Optional, NumberRange

from app.api.task_forms import JsonForm, _strip
from app.models import Role


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
