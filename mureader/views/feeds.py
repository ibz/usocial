from bs4 import BeautifulSoup
from flask import abort, redirect, render_template, request, url_for
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

    entries = models.Entry.query
    if email:
        user = models.User.query.filter_by(email=email).first()
        entries = entries.join(models.UserEntry).filter_by(user=user)
    else:
        user = None
    entries = entries.order_by(models.Entry.updated_at.desc()).limit(100)

    return render_template('news.html', entries=entries, user=user)

@app.route('/subscriptions', methods=['GET'])
@jwt_required
def subscriptions():
    email = get_jwt_identity()
    user = models.User.query.filter_by(email=email).first()
    subscriptions = models.Subscription.query.filter(models.Subscription.user_id==user.id)
    return render_template('subscriptions.html',
        subscriptions=subscriptions, user=user,
        form=forms.FollowWebsiteForm(), jwt_csrf_token=request.cookies.get('csrf_access_token'))

@app.route('/follow', defaults={}, methods=['POST'])
@jwt_required
def follow():
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
