from bs4 import BeautifulSoup
from flask import abort, jsonify, redirect, render_template, request, url_for
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_jwt_extended.exceptions import NoAuthorizationError
import requests

from mureader import app, db
from mureader import forms
from mureader import models
from mureader.views.utils import jwt_required

@app.route('/', methods=['GET'])
def index():
    return redirect(url_for('news'))

@app.route('/news', methods=['GET'])
def news():
    try:
        verify_jwt_in_request()
        email = get_jwt_identity()
    except NoAuthorizationError:
        email = None

    if email:
        user = models.User.query.filter_by(email=email).first()
        entries = models.UserEntry.query \
            .join(models.Entry) \
            .filter(models.UserEntry.user==user, models.UserEntry.liked==False)
    else:
        user = None
        entries = models.Entry.query
    entries = entries.order_by(models.Entry.updated_at.desc()).limit(100)

    return render_template('news.html', entries=entries, user=user)

@app.route('/liked', methods=['GET'])
@jwt_required
def liked():
    email = get_jwt_identity()
    user = models.User.query.filter_by(email=email).first()
    entries = models.UserEntry.query \
        .join(models.Entry) \
        .filter(models.UserEntry.user==user, models.UserEntry.liked==True) \
        .order_by(models.Entry.updated_at.desc())
    return render_template('news.html', entries=entries, user=user)

@app.route('/like', methods=['POST'])
@jwt_required
def like():
    email = get_jwt_identity()
    user = models.User.query.filter_by(email=email).first()
    entry_id = request.form['entry_id']
    user_entry = models.UserEntry.query.filter_by(user_id=user.id, entry_id=entry_id).first()
    if not user_entry: # you could like an entry that is not in your feed (if you see it in somebody else's feed)
        user_entry = models.UserEntry(user_id=user.id, entry_id=entry_id)
    user_entry.liked = bool(int(request.form['value']))
    db.session.add(user_entry)
    db.session.commit()
    return jsonify(ok=True)

@app.route('/delete', methods=['POST'])
@jwt_required
def delete():
    email = get_jwt_identity()
    user = models.User.query.filter_by(email=email).first()
    entry_id = request.form['entry_id']
    if bool(int(request.form['value'])):
        models.UserEntry.query.filter_by(user_id=user.id, entry_id=entry_id).delete()
    else:
        db.session.add(models.UserEntry(user_id=user.id, entry_id=entry_id))
    db.session.commit()
    return jsonify(ok=True)

@app.route('/subscriptions', methods=['GET'])
@jwt_required
def subscriptions():
    email = get_jwt_identity()
    user = models.User.query.filter_by(email=email).first()
    subscribed_feed_ids = {s.feed_id for s in models.Subscription.query.filter_by(user_id=user.id)}
    feeds = [f for f in models.Feed.query.all()]
    for f in feeds:
        if f.id in subscribed_feed_ids:
            f.subscribed = True
    return render_template('subscriptions.html',
        feeds=feeds, user=user,
        form=forms.FollowWebsiteForm(), jwt_csrf_token=request.cookies.get('csrf_access_token'))

@app.route('/follow', methods=['POST'])
@jwt_required
def follow():
    email = get_jwt_identity()
    user = models.User.query.filter_by(email=email).first()
    feed_id = request.form['feed_id']
    if not bool(int(request.form['value'])):
        models.Subscription.query.filter_by(user_id=user.id, feed_id=feed_id).delete()
    else:
        db.session.add(models.Subscription(user_id=user.id, feed_id=feed_id))
    db.session.commit()
    return jsonify(ok=True)

@app.route('/follow-website', methods=['POST'])
@jwt_required
def follow_website():
    email = get_jwt_identity()
    user = models.User.query.filter_by(email=email).first()

    url = request.form['url']
    if not '://' in url:
        url = 'http://' + url
    while url.endswith('/'):
        url = url[:-1]

    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    links = soup.find_all('link', rel='alternate')
    links = [(l.attrs['href'], l.attrs['title'])
        for l in links
        if l.attrs['type'] in ['application/atom+xml', 'application/rss+xml']]
    links = [(url + u if u.startswith('/') else u, title) for u, title in links]
    if not links: # NOTE: here we just assumed that "no links" means this is a feed on itself
        # TODO: validate feed
        feed = models.Feed(url=request.form['url'])
        db.session.add(feed)
        db.session.commit()
        subscription = models.Subscription(user_id=user.id, feed_id=feed.id)
        db.session.add(subscription)
        db.session.commit()
        return redirect(url_for('subscriptions'))
    else:
        form = forms.FollowFeedForm()
        form.url.choices = links
        return render_template('follow.html',
            user=user,
            form=form, jwt_csrf_token=request.cookies.get('csrf_access_token'))
