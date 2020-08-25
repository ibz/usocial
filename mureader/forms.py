from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectField, StringField

class EmailForm(FlaskForm):
    email = StringField("Your email address")

class LoginForm(FlaskForm):
    email_or_username = StringField("Your email address or username")
    token_or_password = PasswordField("Your one-time token or password")

class NewPasswordForm(FlaskForm):
    new_password = PasswordField("Your new password")

class ProfileForm(FlaskForm):
    username = StringField("Username")
    public_profile = BooleanField("Public profile")

class FollowWebsiteForm(FlaskForm):
   url = StringField("URL of the website to follow")

class FollowFeedForm(FlaskForm):
   url = SelectField("URL of the feed to follow")
