from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectField, StringField

class RegisterForm(FlaskForm):
    username = StringField("Your username")

class LoginForm(FlaskForm):
    username = StringField("Your username")
    password = PasswordField("Your password")

class NewPasswordForm(FlaskForm):
    new_password = PasswordField("Your new password")
    repeat_new_password = PasswordField("Repeat your new password")

class FollowWebsiteForm(FlaskForm):
   url = StringField("http://")

class FollowFeedForm(FlaskForm):
   url = SelectField("Feed")
