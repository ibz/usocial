from io import BytesIO

from flask import abort, Blueprint, flash, redirect, render_template, request, url_for
from flask_mail import Message
from flask_jwt_extended import create_access_token, create_refresh_token, current_user, set_access_cookies, set_refresh_cookies, unset_jwt_cookies
from flask_jwt_extended import get_jwt_identity, jwt_refresh_token_required
from itsdangerous import URLSafeTimedSerializer
import pyqrcode
from sqlalchemy.exc import IntegrityError

from musocial import forms, models
from musocial.main import app, db, mail, jwt_required

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
    if current_user:
        return redirect(url_for('feed.news'))

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
    if current_user:
        return redirect(url_for('feed.news'))

    if request.method == 'GET':
        return render_template('user/login.html', form=forms.LoginForm())

    email_or_username = request.form['email_or_username']
    token_or_password = request.form['token_or_password']
    user = models.User.query.filter_by(email=email_or_username).first()
    if not user:
        user = models.User.query.filter_by(username=email_or_username).first()
    login_success = False
    if not user:
        app.logger.info("User not found: %s", email_or_username)
    else:
        if user.verify_totp(token_or_password):
            app.logger.info("Login success token: %s", email_or_username)
            login_success = True
        if user.verify_password(token_or_password):
            app.logger.info("Login success password: %s", email_or_username)
            login_success = True

    if login_success:
        response = redirect(url_for('feed.news'))
        set_access_cookies(response, create_access_token(identity=user.email))
        set_refresh_cookies(response, create_refresh_token(identity=user.email))
        return response
    else:
        flash("Incorrect email or password or one-time token")
        return redirect(url_for('user.login'))

@user_blueprint.route('/me', methods=['GET', 'POST'])
@jwt_required
def me():
    if request.method == 'GET':
        return render_template('user/me.html', user=current_user,
            form=forms.ProfileForm(obj=current_user), jwt_csrf_token=request.cookies.get('csrf_access_token'))

    form = forms.ProfileForm(request.form, obj=current_user)
    if form.validate():
        form.populate_obj(current_user)
        db.session.add(current_user)
    try:
        db.session.commit()
    except IntegrityError:
        flash("The username you want is already in use")
        return redirect(url_for('user.me'))
    return render_template('user/me.html', user=current_user,
        form=forms.ProfileForm(obj=current_user), jwt_csrf_token=request.cookies.get('csrf_access_token'))

@user_blueprint.route('/logout', methods=['GET'])
def logout():
    response = redirect(url_for('feed.news'))
    unset_jwt_cookies(response)
    return response

@user_blueprint.route('/refresh-jwt', methods=['GET'])
@jwt_refresh_token_required
def refresh_jwt():
    response = redirect(url_for('feed.news'))
    set_access_cookies(response, create_access_token(identity=get_jwt_identity()))
    return response
