from datetime import datetime

from babel.dates import format_timedelta
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_jwt_extended import current_user
import requests
from sqlalchemy import func
from urllib.parse import urlparse

import podcastindex

from musocial import forms, models as m
from musocial.parser import extract_feed_links, parse_feed
from musocial.main import db, jwt_required

import config

subscription_blueprint = Blueprint('subscription', __name__)

@subscription_blueprint.route('/subscriptions', methods=['GET'])
@jwt_required
def subscriptions():
    feeds = []
    q = db.session.query(m.Feed, func.count(m.Item.id), func.max(m.Item.updated_at)) \
                        .join(m.Subscription) \
                        .filter(m.Subscription.user_id == current_user.id) \
                        .outerjoin(m.Item) \
                        .group_by(m.Feed) \
                        .order_by(func.max(m.Item.updated_at).desc()).all()
    for f, item_count, last_item_date in q:
        f.subscribed = True
        f.item_count = item_count
        f.last_item_relative = format_timedelta(last_item_date - datetime.now(), add_direction=True) if last_item_date else 'never'
        feeds.append(f)
    return render_template('subscription/feeds.html', feeds=feeds, user=current_user)

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
        existing_feed = m.Feed.query.filter_by(url=feed_url).one_or_none()
        feed = existing_feed or m.Feed(url=feed_url)
        feed.update(parsed_feed)
        db.session.add(feed)
        db.session.commit()
        new_items, updated_items = feed.update_items(parsed_feed)
        db.session.add(feed)
        for item in new_items + updated_items:
            db.session.add(item)
        db.session.commit()
        subscription = m.Subscription(user_id=current_user.id, feed_id=feed.id)
        db.session.add(subscription)
        db.session.commit()
        for item in new_items + updated_items:
            db.session.add(m.UserItem(user=current_user, item=item))
        db.session.commit()
        return redirect(url_for('subscription.subscriptions'))
    else:
        form = forms.FollowFeedForm()
        form.url.choices = alt_links
        return render_template('subscription/follow-website.html',
            user=current_user,
            form=form, jwt_csrf_token=request.cookies.get('csrf_access_token'))

@subscription_blueprint.route('/podcast-search', methods=['GET', 'POST'])
@jwt_required
def podcast_search():
    if request.method == 'GET':
        return render_template('podcast_search.html', user=current_user,
            form=forms.SearchPodcastForm(), jwt_csrf_token=request.cookies.get('csrf_access_token'))

    q = m.Feed.query.join(m.Subscription).filter(m.Subscription.user_id == current_user.id).all()
    subscribed_urls = {f.url for f in q}
    index = podcastindex.init({'api_key': config.PODCASTINDEX_API_KEY, 'api_secret': config.PODCASTINDEX_API_SECRET})
    result = index.search(request.form['keywords'])
    feeds = [{'id': f['id'],
              'url': f['url'],
              'title': f['title'],
              'domain': urlparse(f['link']).netloc,
              'homepage_url': f['link'],
              'description': f['description'],
              'image': f['artwork'],
              'categories': [c for c in (f['categories'] or {}).values()],
              'subscribed': f['url'] in subscribed_urls}
             for f in result['feeds']]
    return render_template('podcast_search.html',
        user=current_user,
        podcastindex_feeds=feeds,
        form=forms.SearchPodcastForm(), jwt_csrf_token=request.cookies.get('csrf_access_token'))
