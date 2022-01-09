from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_jwt_extended import create_access_token, create_refresh_token, current_user, set_access_cookies, set_refresh_cookies, unset_jwt_cookies
from flask_jwt_extended import get_jwt_identity
from sqlalchemy.exc import IntegrityError

from musocial import forms, models as m
from musocial.main import app, db, jwt_required

user_blueprint = Blueprint('user', __name__)

@user_blueprint.route('/register', methods=['GET', 'POST'])
def register():
    if current_user:
        return redirect(url_for('feed.items'))

    if request.method == 'GET':
        return render_template('user/register.html', form=forms.RegisterForm())

    error = None
    username = request.form['username']
    if not username:
        error = "Username is required"
    elif m.User.query.filter_by(username=username).first():
        error = "Username is already in use"
    if error is None:
        try:
            db.session.add(m.User(username))
            db.session.commit()
        except Exception as e:
            app.log_exception(e)
            error = "Failed to create user"

    if error is None:
        return render_template('user/register.html', success=True)
    else:
        flash(error)
        return redirect(url_for('user.register'))

@user_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if current_user:
        return redirect(url_for('feed.items'))

    if request.method == 'GET':
        return render_template('user/login.html', form=forms.LoginForm())

    username = request.form['username']
    password = request.form['password']
    user = m.User.query.filter_by(username=username).first()
    login_success = False
    if not user:
        app.logger.info("User not found: %s", username)
    else:
        if not user.password:
            app.logger.info("Login success no auth: %s", username)
            login_success = True
        if user.verify_password(password):
            app.logger.info("Login success password: %s", username)
            login_success = True

    if login_success:
        response = redirect(url_for('feed.items'))
        set_access_cookies(response, create_access_token(identity=user.username))
        set_refresh_cookies(response, create_refresh_token(identity=user.username))
        return response
    else:
        flash("Incorrect username or password.")
        return redirect(url_for('user.login'))

@user_blueprint.route('/me', methods=['GET'])
@jwt_required
def me():
    q = db.session.query(m.UserItem).filter_by(user_id=current_user.id)
    sum_q = q.statement.with_only_columns([db.func.sum(m.UserItem.played_value_count), db.func.sum(m.UserItem.paid_value_count)])
    played_value, paid_value = q.session.execute(sum_q).one()

    return render_template('user/me.html', user=current_user, played_value=played_value, paid_value=paid_value)

@user_blueprint.route('/password', methods=['GET', 'POST'])
@jwt_required
def password():
    if request.method == 'GET':
        return render_template('user/password.html', user=current_user,
            form=forms.NewPasswordForm(),
            jwt_csrf_token=request.cookies.get('csrf_access_token'))
    else:
        if request.form['new_password'] != request.form['repeat_new_password']:
            flash("Passwords don't match")
            return redirect(url_for('user.password'))
        current_user.set_password(request.form['new_password'])
        flash("Your password was changed")
        db.session.add(current_user)
        db.session.commit()
        return redirect(url_for('user.me'))

@user_blueprint.route('/logout', methods=['GET'])
def logout():
    response = redirect(url_for('feed.items'))
    unset_jwt_cookies(response)
    return response
