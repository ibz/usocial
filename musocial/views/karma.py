from flask import Blueprint, render_template, redirect, request, url_for
from flask_jwt_extended import current_user
from flask_sqlalchemy import get_debug_queries
from werkzeug.datastructures import MultiDict

from musocial import forms, models as m
from musocial.main import app, db, jwt_required

karma_blueprint = Blueprint('karma', __name__)

@karma_blueprint.route('/karma/pay', methods=['GET', 'POST'])
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
        return redirect(url_for('user.me'))
