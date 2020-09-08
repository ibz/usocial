from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_jwt_extended import current_user
import requests

from musocial import forms, models
from musocial.parser import extract_feed_links, parse_feed
from musocial.main import db, jwt_required

subscription_blueprint = Blueprint('subscription', __name__)

@subscription_blueprint.route('/discover', methods=['GET'])
@jwt_required
def discover():
    subscribed_feed_ids = {s.feed_id for s in models.Subscription.query.filter_by(user=current_user)}
    feeds = [f for f in models.Feed.query.all()]
    for f in feeds:
        if f.id in subscribed_feed_ids:
            f.subscribed = True
    return render_template('subscription/discover.html', feeds=feeds, user=current_user)

@subscription_blueprint.route('/follow-website', methods=['GET', 'POST'])
@jwt_required
def follow_website():
    if request.method == 'GET':
        return render_template('subscription/follow-website.html', user=current_user,
            form=forms.FollowWebsiteForm(), jwt_csrf_token=request.cookies.get('csrf_access_token'))

    url = request.form['url']
    if not '://' in url:
        url = f"http://{url}"
    while url.endswith('/'):
        url = url[:-1]

    r = requests.get(url)
    alt_links = extract_feed_links(url, r.text)
    if not alt_links: # NOTE: here we just assumed that "no links" means this is a feed on itself
        feed_url = request.form['url']
        parsed_feed = parse_feed(feed_url)
        if not parsed_feed:
            flash(f"Cannot parse feed at: {feed_url}")
            return redirect(url_for('subscription.follow_website'))
        feed = models.Feed(url=feed_url)
        feed.update(parsed_feed)
        db.session.add(feed)
        db.session.commit()
        subscription = models.Subscription(user_id=current_user.id, feed_id=feed.id)
        db.session.add(subscription)
        db.session.commit()
        return redirect(url_for('subscription.follow_website'))
    else:
        form = forms.FollowFeedForm()
        form.url.choices = alt_links
        return render_template('subscription/follow-website.html',
            user=current_user,
            form=form, jwt_csrf_token=request.cookies.get('csrf_access_token'))
