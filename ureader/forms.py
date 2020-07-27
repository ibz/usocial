from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField

class RegisterForm(FlaskForm):
    email = StringField("Your email")
    password = PasswordField("Your password")

class LoginForm(FlaskForm):
    email = StringField("Your email")
    password = PasswordField("Your password")

class SubscribeForm(FlaskForm):
   url = StringField("URL of the feed")
