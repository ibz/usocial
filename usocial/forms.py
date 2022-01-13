from flask_wtf import FlaskForm
from wtforms import BooleanField, FieldList, FormField, HiddenField, IntegerField, PasswordField, SelectField, StringField

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

class RecipientForm(FlaskForm):
    id = HiddenField()
    name = StringField("Name", render_kw={'readonly': True, 'disabled': True})
    address = StringField("Address", render_kw={'readonly': True, 'disabled': True})

class PaymentForm(FlaskForm):
    recipient = FormField(RecipientForm)
    amount = IntegerField("Amount")

class PaymentListForm(FlaskForm):
    paid_for_items = HiddenField()
    payments = FieldList(FormField(PaymentForm))
