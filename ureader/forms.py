from flask_wtf import FlaskForm
from wtforms import PasswordField, TextField

class RegisterForm(FlaskForm):
    email = TextField("Your email")
    password = PasswordField("Your password")

class LoginForm(FlaskForm):
    email = TextField("Your email")
    password = PasswordField("Your password")

class SubscribeForm(FlaskForm):
   url = TextField("URL of the feed")
