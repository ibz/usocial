from io import BytesIO

from flask import abort, Blueprint, flash, redirect, render_template, request, url_for
from flask_mail import Message
from flask_jwt_extended import create_access_token, create_refresh_token, set_access_cookies, set_refresh_cookies, unset_jwt_cookies
from flask_jwt_extended import get_jwt_identity, jwt_refresh_token_required
from itsdangerous import URLSafeTimedSerializer

import pyqrcode

from mureader import app, db, mail
from mureader import forms
from mureader import models

user_blueprint = Blueprint('user', __name__)


def send_confirmation_email(email):
    token = generate_confirmation_token(email)
    confirm_url = url_for('user.confirm_email', token=token, _external=True)
    try:
        subject = "Please confirm your email address"
        html = render_template('user/confirm-email-message.html', confirm_url=confirm_url)
        m = Message(subject, recipients=[email], html=html, sender=app.config['MAIL_DEFAULT_SENDER'])
        mail.send(m)
    except Exception as e:
        app.log_exception(e)
        app.logger.info('Confirmation url: %s', confirm_url)
        return "Failed to send confirmation email"

def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(email)

def check_token(token, expiration=(60 * 10)):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.loads(token, max_age=expiration)

@user_blueprint.route('/register', methods=['GET', 'POST'])
def register():
    if get_jwt_identity():
        return redirect(url_for('news'))

    if request.method == 'GET':
        return render_template('user/register.html', form=forms.EmailForm())

    error = None
    email = request.form['email']
    if not email:
        error = "Email is required"
    elif models.User.query.filter_by(email=email).first():
        error = "Email is already in use"
    if error is None:
        try:
            db.session.add(models.User(email))
            db.session.commit()
        except Exception as e:
            app.log_exception(e)
            error = "Failed to create user"

        error = send_confirmation_email(email)

    if error is None:
        return render_template('user/register.html', success=True)
    else:
        flash(error)
        return redirect(url_for('user.register'))

@user_blueprint.route('/confirm-email', defaults={'token': None}, methods=['GET', 'POST'])
@user_blueprint.route('/confirm-email/<token>', methods=['GET', 'POST'])
def confirm_email(token):
    if token is None:
        if request.method == 'GET':
            return render_template('user/confirm-email.html', form=forms.EmailForm())
        else:
            user = models.User.query.filter_by(email=request.form['email']).first()
            if not user:
                # don't need to say the user was not found
                app.logger.warn("Trying to confirm email for an inexisting user: %s", request.form['email'])
                return render_template('user/register.html', success=True)
            else:
                error = send_confirmation_email(user.email)
                if error:
                    flash(error)
                    return redirect(url_for('user.confirm_email'))
                else:
                    return render_template('user/register.html', success=True)

    try:
        email = check_token(token)
    except Exception:
        flash("The confirmation link is invalid or has expired")
        return redirect(url_for('user.register'))

    user = models.User.query.filter_by(email=email).first_or_404()
    if not user.email_confirmed:
        user.email_confirmed = True
        flash("Your email address was confirmed")
    if request.method == 'POST':
        user.set_password(request.form['new_password'])
        flash("Your password was changed")
    db.session.add(user)
    db.session.commit()

    url = pyqrcode.create(user.get_totp_uri())
    stream = BytesIO()
    url.svg(stream, scale=5, xmldecl=False, svgns=False, module_color="#802929")
    qr = stream.getvalue().decode('utf-8')

    return render_template('user/new-password.html', qr=qr, user=user, form=forms.NewPasswordForm())

@user_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if get_jwt_identity():
        return redirect(url_for('news'))

    if request.method == 'GET':
        return render_template('user/login.html', form=forms.LoginForm())

    email = request.form['email']
    token_or_password = request.form['token_or_password']
    user = models.User.query.filter_by(email=email).first()
    login_success = False
    if not user:
        app.logger.info("User not found: %s", email)
    else:
        if user.verify_totp(token_or_password):
            app.logger.info("Login success token: %s", email)
            login_success = True
        if user.verify_password(token_or_password):
            app.logger.info("Login success password: %s", email)
            login_success = True

    if login_success:
        response = redirect(url_for('news'))
        set_access_cookies(response, create_access_token(identity=email))
        set_refresh_cookies(response, create_refresh_token(identity=email))
        return response
    else:
        flash("Incorrect email or password or one-time token")
        return redirect(url_for('user.login'))

@user_blueprint.route('/logout', methods=['GET',])
def logout():
    response = redirect(url_for('news'))
    unset_jwt_cookies(response)
    return response

@user_blueprint.route('/refresh-jwt', methods=['GET',])
@jwt_refresh_token_required
def refresh_jwt():
    email = get_jwt_identity()
    response = redirect(url_for('news'))
    set_access_cookies(response, create_access_token(identity=email))
    return response
