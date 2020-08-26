from bs4 import BeautifulSoup
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_jwt_extended import current_user, get_jwt_identity, verify_jwt_in_request
from flask_jwt_extended.exceptions import NoAuthorizationError
import requests

from mureader import forms, models
from mureader.main import db
from mureader.views.utils import jwt_required

feed_blueprint = Blueprint('feed', __name__)

@feed_blueprint.route('/news', methods=['GET'])
def news():
    try:
        verify_jwt_in_request()
    except NoAuthorizationError:
        pass
    if current_user:
        entries = models.UserEntry.query \
            .join(models.Entry) \
            .filter(models.UserEntry.user==current_user, models.UserEntry.liked==False)
    else:
        entries = models.Entry.query
    entries = entries.order_by(models.Entry.updated_at.desc()).limit(100)

    return render_template('news.html', entries=entries, user=current_user)

@feed_blueprint.route('/liked', methods=['GET'])
@jwt_required
def liked():
    entries = models.UserEntry.query \
        .join(models.Entry) \
        .filter(models.UserEntry.user==current_user, models.UserEntry.liked==True) \
        .order_by(models.Entry.updated_at.desc())
    return render_template('news.html', entries=entries, user=current_user)

@feed_blueprint.route('/subscriptions', methods=['GET'])
@jwt_required
def subscriptions():
    subscribed_feed_ids = {s.feed_id for s in models.Subscription.query.filter_by(user=current_user)}
    feeds = [f for f in models.Feed.query.all()]
    for f in feeds:
        if f.id in subscribed_feed_ids:
            f.subscribed = True
    return render_template('subscriptions.html',
        feeds=feeds, user=current_user,
        form=forms.FollowWebsiteForm(), jwt_csrf_token=request.cookies.get('csrf_access_token'))

@feed_blueprint.route('/follow-website', methods=['POST'])
@jwt_required
def follow_website():
    if not current_user.is_pro:
        flash("Only pro users can follow external websites")
        return redirect(url_for('feed.subscriptions'))

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
        subscription = models.Subscription(user_id=current_user.id, feed_id=feed.id)
        db.session.add(subscription)
        db.session.commit()
        return redirect(url_for('feed.subscriptions'))
    else:
        form = forms.FollowFeedForm()
        form.url.choices = links
        return render_template('follow.html',
            user=current_user,
            form=form, jwt_csrf_token=request.cookies.get('csrf_access_token'))
