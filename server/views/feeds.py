
from flask import flash, make_response, redirect, render_template, request, url_for
from flask_jwt_extended import get_jwt_identity, jwt_refresh_token_required

from app import app, bcrypt, db, jwt
from forms import SubscribeForm
from models import User, Feed, Subscription
from views.auth import jwt_required

@app.route('/')
@jwt_required
def index():
    email = get_jwt_identity()
    if not email:
        return redirect(url_for('login'))
    user = User.query.filter_by(email=email).first()
    jwt_csrf_token = request.cookies.get('csrf_access_token')
    return render_template('index.html', email=email, subscriptions=user.subscriptions, form=SubscribeForm(), jwt_csrf_token=jwt_csrf_token)

@app.route('/subscribe', methods=('POST',))
@jwt_required
def subscribe():
    email = get_jwt_identity()
    user = User.query.filter_by(email=email).first()
    feed = Feed.query.filter_by(url=request.form['url']).first()
    if not feed:
        feed = Feed(url=request.form['url'])
        db.session.add(feed)
        db.session.commit()
    subscription = Subscription(user_id=user.id, feed_id=feed.id)
    db.session.add(subscription)
    db.session.commit()
    return redirect(url_for('index'))
