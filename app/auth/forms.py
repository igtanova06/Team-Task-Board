from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length, Regexp

EMAIL_REGEX = r'^[^@\s]+@[^@\s]+\.[^@\s]+$'

class LoginForm(FlaskForm):
    identity = StringField('Email or Username', validators=[DataRequired(message="Please enter your email or username.")])
    password = PasswordField('Password', validators=[DataRequired(message="Please enter your password.")])
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
