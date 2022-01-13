from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_jwt_extended import create_access_token, create_refresh_token, current_user, set_access_cookies, set_refresh_cookies, unset_jwt_cookies
from flask_jwt_extended import get_jwt_identity
from sqlalchemy.exc import IntegrityError

from usocial import forms, models as m
from usocial.main import app, db, jwt_required

account_blueprint = Blueprint('account', __name__)

@account_blueprint.route('/account/register', methods=['GET', 'POST'])
def register():
    if current_user:
        return redirect(url_for('feed.items'))

    if request.method == 'GET':
        return render_template('account/register.html', form=forms.RegisterForm())

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
        return redirect(url_for('account.login'))
    else:
        flash(error)
        return redirect(url_for('account.register'))

@account_blueprint.route('/account/login', methods=['GET', 'POST'])
def login():
    if current_user:
        return redirect(url_for('feed.items'))

    if request.method == 'GET':
        return render_template('account/login.html', user=None, form=forms.LoginForm())

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
        return redirect(url_for('account.login'))

@account_blueprint.route('/account/me', methods=['GET'])
@jwt_required
def me():
    q = db.session.query(m.UserItem).filter_by(user_id=current_user.id)
    sum_q = q.statement.with_only_columns([
        db.func.coalesce(db.func.sum(m.UserItem.played_value_count), 0),
        db.func.coalesce(db.func.sum(m.UserItem.paid_value_count), 0)])
    played_value, paid_value = q.session.execute(sum_q).one()

    return render_template('account/me.html', user=current_user, played_value=played_value, paid_value=paid_value)

@account_blueprint.route('/account/password', methods=['GET', 'POST'])
@jwt_required
def password():
    if request.method == 'GET':
        return render_template('account/password.html', user=current_user,
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
        return redirect(url_for('account.me'))

@account_blueprint.route('/account/logout', methods=['GET'])
def logout():
    response = redirect(url_for('feed.items'))
    unset_jwt_cookies(response)
    return response

@account_blueprint.route('/account/pay', methods=['GET', 'POST'])
@jwt_required
def pay():
    if request.method == 'GET':
        amounts = {}
        item_ids = []
        for ui in m.UserItem.query.filter(m.UserItem.user == current_user, m.UserItem.played_value_count > m.UserItem.paid_value_count).all():
            item_ids.append(ui.item_id)
            value_spec = ui.value_spec
            for recipient_id, amount in value_spec.split_sats(value_spec.sats_amount * (ui.played_value_count - ui.paid_value_count)).items():
                amounts[recipient_id] = amounts.get(recipient_id, 0) + amount

        form = forms.PaymentListForm()
        form.paid_for_items.data = ','.join(str(id) for id in item_ids)
        for recipient in m.ValueRecipient.query.filter(m.ValueRecipient.id.in_(amounts.keys())):
            payment_form = forms.PaymentForm()
            payment_form.recipient = forms.RecipientForm()
            payment_form.recipient.id = recipient.id
            payment_form.recipient.name = recipient.name
            payment_form.recipient.address = recipient.address
            payment_form.amount = amounts[recipient.id]
            form.payments.append_entry(payment_form)

        return render_template('pay.html', user=current_user, form=form, jwt_csrf_token=request.cookies.get('csrf_access_token'))
    else:
        form = forms.PaymentListForm()
        if form.validate_on_submit():
            item_ids = [int(id) for id in form.data['paid_for_items'].split(',')]
            user_items = m.UserItem.query.filter(m.UserItem.user == current_user, m.UserItem.item_id.in_(item_ids)).all()
            for user_item in user_items:
                user_item.paid_value_count = user_item.played_value_count
                db.session.add(user_item)
            for payment_data in form.data['payments']:
                payment = m.ValuePayment(recipient_id=payment_data['recipient']['id'], amount=payment_data['amount'])
                db.session.add(payment)
            db.session.commit()
        return redirect(url_for('account.me'))
