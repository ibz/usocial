from flask_wtf import FlaskForm
from wtforms import PasswordField, SelectField, StringField

class RegisterForm(FlaskForm):
    username = StringField("Username")

class LoginForm(FlaskForm):
    username = StringField("Username")
    password = PasswordField("Password")

class NewPasswordForm(FlaskForm):
    new_password = PasswordField("Password")
    repeat_new_password = PasswordField("Repeat password")

class FollowWebsiteForm(FlaskForm):
    url = StringField("http://")

class FollowFeedForm(FlaskForm):
    url = SelectField("Feed")

class SearchPodcastForm(FlaskForm):
    keywords = StringField("Keywords")
