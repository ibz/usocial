from datetime import datetime

from babel.dates import format_timedelta
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_jwt_extended import current_user
import requests
from sqlalchemy import func

from musocial import forms, models as m
from musocial.parser import extract_feed_links, parse_feed
from musocial.main import db, jwt_required

subscription_blueprint = Blueprint('subscription', __name__)

@subscription_blueprint.route('/subscriptions', methods=['GET'])
@jwt_required
def subscriptions():
    feeds = []
    q = db.session.query(m.Feed, func.count(m.Entry.id), func.max(m.Entry.updated_at)) \
                        .join(m.Subscription) \
                        .filter(m.Subscription.user_id == current_user.id) \
                        .outerjoin(m.Entry) \
                        .group_by(m.Feed) \
                        .order_by(func.max(m.Entry.updated_at).desc()).all()
    for f, entry_count, last_entry_date in q:
        f.subscribed = True
        f.entry_count = entry_count
        f.last_entry_relative = format_timedelta(last_entry_date - datetime.now(), add_direction=True) if last_entry_date else 'never'
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
        new_entries, updated_entries = feed.update_entries(parsed_feed)
        db.session.add(feed)
        for entry in new_entries + updated_entries:
            db.session.add(entry)
        db.session.commit()
        subscription = m.Subscription(user_id=current_user.id, feed_id=feed.id)
        db.session.add(subscription)
        db.session.commit()
        for entry in new_entries + updated_entries:
            db.session.add(m.UserEntry(user=current_user, entry=entry))
        db.session.commit()
        return redirect(url_for('subscription.subscriptions'))
    else:
        form = forms.FollowFeedForm()
        form.url.choices = alt_links
        return render_template('subscription/follow-website.html',
            user=current_user,
            form=form, jwt_csrf_token=request.cookies.get('csrf_access_token'))
