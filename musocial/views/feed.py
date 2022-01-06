from datetime import datetime

from babel.dates import format_timedelta
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_jwt_extended import current_user
import requests
from sqlalchemy import func
from urllib.parse import urlparse

import podcastindex

from musocial import forms, models as m
from musocial.parser import extract_feed_links, parse_feed
from musocial.main import db, jwt_required

import config

feed_blueprint = Blueprint('feed', __name__)

@feed_blueprint.route('/feeds/<int:feed_id>/follow', methods=['POST'])
@jwt_required
def follow(feed_id):
    if not bool(int(request.form['value'])): # unfollow
        for fg in m.FeedGroup.query \
            .join(m.Group) \
            .filter(m.Group.user == current_user, m.FeedGroup.feed_id == feed_id):
            db.session.delete(fg)
        for ue in m.UserItem.query \
            .join(m.Item) \
            .filter(m.UserItem.user == current_user, m.UserItem.liked == False, m.Item.feed_id == feed_id):
            db.session.delete(ue)
    else:
        group = m.Group.query.filter(m.Group.user == current_user, m.Group.name == m.Group.DEFAULT_GROUP).one_or_none()
        if not group:
            group = m.Group(user=current_user, name=m.Group.DEFAULT_GROUP)
            db.session.add(group)
            db.session.commit()
        db.session.add(m.FeedGroup(group=group, feed_id=feed_id))
        existing_item_ids = {ue.item_id for ue in m.UserItem.query.join(m.Item).filter(m.UserItem.user == current_user, m.Item.feed_id == feed_id)}
        for item in m.Feed.query.filter_by(id=feed_id).first().items:
            if item.id not in existing_item_ids:
                db.session.add(m.UserItem(user=current_user, item=item))
    db.session.commit()
    return jsonify(ok=True)

@feed_blueprint.route('/feeds/websites/add', methods=['GET', 'POST'])
@jwt_required
def follow_website():
    if request.method == 'GET':
        return render_template('follow_website.html', user=current_user,
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
            return redirect(url_for('feed.follow_website'))
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
        group = m.Group.query.filter(m.Group.user == current_user, m.Group.name == m.Group.DEFAULT_GROUP).one_or_none()
        if not group:
            group = m.Group(user=current_user, name=m.Group.DEFAULT_GROUP)
            db.session.add(group)
            db.session.commit()
        db.session.add(m.FeedGroup(group=group, feed_id=feed.id))
        db.session.commit()
        existing_item_ids = {ue.item_id for ue in m.UserItem.query.join(m.Item).filter(m.UserItem.user == current_user, m.Item.feed_id == feed.id)}
        for item in feed.items:
            if item.id not in existing_item_ids:
                db.session.add(m.UserItem(user=current_user, item=item))
        db.session.commit()
        return redirect(url_for('item.index'))
    else:
        form = forms.FollowFeedForm()
        form.url.choices = alt_links
        return render_template('follow_website.html',
            user=current_user,
            form=form, jwt_csrf_token=request.cookies.get('csrf_access_token'))

@feed_blueprint.route('/feeds/podcasts/search', methods=['GET', 'POST'])
@jwt_required
def podcast_search():
    if request.method == 'GET':
        return render_template('podcast_search.html', user=current_user,
            form=forms.SearchPodcastForm(), jwt_csrf_token=request.cookies.get('csrf_access_token'))

    q = m.Feed.query.join(m.FeedGroup).join(m.Group).filter(m.Group.user == current_user, m.Group.name == m.Group.PODCASTS_GROUP).all()
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

@feed_blueprint.route('/feeds/podcasts/follow', methods=['POST'])
@jwt_required
def follow_podcast():
    feed = m.Feed.query.filter_by(url=request.form['url']).one_or_none()
    if not feed:
        feed = m.Feed(
            url=request.form['url'],
            homepage_url=request.form['homepage_url'],
            title=request.form['title'])
        db.session.add(feed)
        db.session.commit()
    parsed_feed = parse_feed(feed.url)
    if not parsed_feed:
        return jsonify(ok=False)
    feed.update(parsed_feed)
    db.session.add(feed)
    db.session.commit()
    new_items, updated_items = feed.update_items(parsed_feed)
    db.session.add(feed)
    for item in new_items + updated_items:
        db.session.add(item)
    db.session.commit()
    group = m.Group.query.filter(m.Group.user == current_user, m.Group.name == m.Group.PODCASTS_GROUP).one_or_none()
    if not group:
        group = m.Group(user=current_user, name=m.Group.PODCASTS_GROUP)
        db.session.add(group)
        db.session.commit()
    db.session.add(m.FeedGroup(group=group, feed_id=feed.id))
    db.session.commit()
    existing_item_ids = {ue.item_id for ue in m.UserItem.query.join(m.Item).filter(m.UserItem.user == current_user, m.Item.feed_id == feed.id)}
    for item in feed.items:
        if item.id not in existing_item_ids:
            db.session.add(m.UserItem(user=current_user, item=item))
    db.session.commit()
    return jsonify(ok=True)

@feed_blueprint.route('/feeds/podcasts/unfollow', methods=['POST'])
@jwt_required
def unfollow_podcast():
    feed = m.Feed.query.filter_by(url=request.form['url']).one_or_none()
    if feed:
        for fg in m.FeedGroup.query.join(m.Group).filter(m.Group.user == current_user, models.FeedGroup.feed == feed):
            db.session.delete(fg)
        db.session.commit()
        # TODO: delete items!
    return jsonify(ok=True)
