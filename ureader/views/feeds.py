from flask import redirect, render_template, request, url_for
from flask_jwt_extended import get_jwt_identity

from ureader import app, db
from ureader import forms
from ureader import models
from ureader.views.utils import jwt_required

@app.route('/feed', methods=('GET',))
@jwt_required
def feed():
    email = get_jwt_identity()
    if not email:
        return redirect(url_for('login'))
    user = models.User.query.filter_by(email=email).first()
    jwt_csrf_token = request.cookies.get('csrf_access_token')
    entries = models.Entry.query \
        .join(models.Feed) \
        .join(models.Subscription) \
        .filter(models.Subscription.user_id==user.id) \
        .order_by(models.Entry.updated_at.desc())
    return render_template('feed.html', user=user, entries=entries)

@app.route('/subscriptions', methods=('GET',))
@jwt_required
def subscriptions():
    email = get_jwt_identity()
    if not email:
        return redirect(url_for('login'))
    user = models.User.query.filter_by(email=email).first()
    jwt_csrf_token = request.cookies.get('csrf_access_token')
    subscriptions = models.Subscription.query \
        .filter(models.Subscription.user_id==user.id)
    return render_template('subscriptions.html', user=user, subscriptions=subscriptions, form=forms.FollowForm(), jwt_csrf_token=jwt_csrf_token)

@app.route('/follow', methods=('POST',))
@jwt_required
def follow():
    email = get_jwt_identity()
    user = models.User.query.filter_by(email=email).first()
    feed = models.Feed.query.filter_by(url=request.form['url']).first()
    if not feed:
        feed = models.Feed(url=request.form['url'])
        db.session.add(feed)
        db.session.commit()
    subscription = models.Subscription(user_id=user.id, feed_id=feed.id)
    db.session.add(subscription)
    db.session.commit()
    return redirect(url_for('subscriptions'))
