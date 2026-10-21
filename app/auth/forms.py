from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length, Regexp

EMAIL_REGEX = r'^[^@\s]+@[^@\s]+\.[^@\s]+$'

class LoginForm(FlaskForm):
    identity = StringField('Email or Username', validators=[
        DataRequired(message="Please enter your email or username."),
        Length(max=100)
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Please enter your password."),
        Length(max=128)
    ])
    remember = BooleanField('Keep me signed in')
    submit = SubmitField('Sign In')


class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(message="Username is required."),
        Length(min=3, max=50, message="Username must be between 3 and 50 characters.")
    ])
    email = StringField('Email', validators=[
        DataRequired(message="Email is required."),
        Length(max=100),
        Regexp(EMAIL_REGEX, message="Please enter a valid email address.")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required."),
        Length(min=6, max=128, message="Password must be at least 6 characters.")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message="Please confirm your password."),
        EqualTo('password', message="Passwords must match.")
    ])
    submit = SubmitField('Register')


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[
        DataRequired(message="Current password is required."),
        Length(max=128)
    ])
    new_password = PasswordField('New Password', validators=[
        DataRequired(message="New password is required."),
        Length(min=6, max=128, message="New password must be at least 6 characters.")
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(message="Please confirm your new password."),
        EqualTo('new_password', message="New passwords must match.")
    ])
    submit = SubmitField('Update Password')

