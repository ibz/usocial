import pytz

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_jwt_extended import create_access_token, create_refresh_token, current_user, get_jwt_identity, set_access_cookies, set_refresh_cookies, unset_jwt_cookies, verify_jwt_in_request
from flask_jwt_extended.exceptions import NoAuthorizationError
from sqlalchemy.exc import IntegrityError

from usocial import forms, models as m, payments
from usocial.main import app, db, jwt_required

import config

account_blueprint = Blueprint('account', __name__)

def login_success(user):
    response = redirect(url_for('feed.items'))
    set_access_cookies(response, create_access_token(identity=user.username))
    set_refresh_cookies(response, create_refresh_token(identity=user.username))
    return response

def only_default_user():
    if m.User.query.count() == 1:
        return m.User.query.filter_by(username=m.User.DEFAULT_USERNAME).one_or_none()

def login_default_user():
    default_user = only_default_user()
    if default_user and not default_user.password:
        return login_success(default_user)

@account_blueprint.route('/', methods=['GET'])
def index():
    try:
        verify_jwt_in_request()
        return redirect(url_for('feed.items'))
    except NoAuthorizationError:
        return login_default_user() or redirect(url_for('account.login'))

@account_blueprint.route('/account', methods=['GET'])
@jwt_required
def account():
    q = db.session.query(m.UserItem).filter_by(user_id=current_user.id)
    sum_q = q.statement.with_only_columns([
        db.func.coalesce(db.func.sum(m.UserItem.stream_value_played), 0),
        db.func.coalesce(db.func.sum(m.UserItem.stream_value_paid), 0)])
    played_value, paid_value = q.session.execute(sum_q).one()
    paid_value_amounts = m.Action.get_total_amounts(current_user)

    return render_template('account.html', user=current_user,
        played_value=played_value, paid_value=paid_value, paid_value_amounts=paid_value_amounts,
        only_default_user=only_default_user(),
        version=config.VERSION, build=config.BUILD,
        lnd_info=payments.get_lnd_info())

@account_blueprint.route('/account/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if current_user:
            return redirect(url_for('feed.items'))
        else:
            return login_default_user() or render_template('login.html', user=None, skip_username=bool(only_default_user()), form=forms.LoginForm())

    username = request.form['username'] if not only_default_user() else m.User.DEFAULT_USERNAME
    password = request.form['password']
    user = m.User.query.filter_by(username=username).first()
    success = False
    if not user:
        app.logger.info("User not found: %s", username)
    else:
        if not user.password and not password:
            app.logger.info("Login success no auth: %s", username)
            success = True
        if user.verify_password(password):
            app.logger.info("Login success password: %s", username)
            success = True
    if success:
        return login_success(user)
    else:
        flash("Incorrect credentials.")
        return redirect(url_for('account.login'))

@account_blueprint.route('/account/password', methods=['GET', 'POST'])
@jwt_required
def password():
    if request.method == 'GET':
        return render_template('password.html', user=current_user,
            form=forms.NewPasswordForm(),
            jwt_csrf_token=request.cookies.get('csrf_access_token'))
    else:
        if request.form['new_password'] != request.form['repeat_new_password']:
            flash("Passwords don't match")
            return redirect(url_for('account.password'))
        current_user.set_password(request.form['new_password'])
        flash("Your password was changed")
        db.session.add(current_user)
        db.session.commit()
        return redirect(url_for('account.account'))

@account_blueprint.route('/account/logout', methods=['GET'])
def logout():
    response = redirect(url_for('account.login'))
    unset_jwt_cookies(response)
    return response

@account_blueprint.route('/account/volume', methods=['POST'])
@jwt_required
def update_volume():
    current_user.audio_volume = float(request.form['value'])
    db.session.add(current_user)
    db.session.commit()
    return jsonify(ok=True)

@account_blueprint.route('/account/timezone', methods=['POST'])
@jwt_required
def update_timezone():
    try:
        current_user.timezone = pytz.timezone(request.form['value']).zone
    except pytz.exceptions.UnknownTimeZoneError:
        return "Invalid timezone.", 400
    db.session.add(current_user)
    db.session.commit()
    return jsonify(ok=True)
