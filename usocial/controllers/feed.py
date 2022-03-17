from datetime import datetime
import json

from babel.dates import format_timedelta
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_jwt_extended import current_user
import requests
from sqlalchemy import func
from urllib.parse import urlparse

from feedparsley import extract_feed_links, parse_feed

from usocial import forms, models as m, payments
from usocial.main import app, db, get_podcastindex, jwt_required

import config

feed_blueprint = Blueprint('feed', __name__)

def get_items_feeds(feed_id, item_q):
    def item_to_dict(i):
        return {
            'user_item': i[0], 'url': i[1], 'title': i[2], 'feed_id': i[3], 'updated_at': i[4],
            'enclosure_url': i[5], 'enclosure_type': i[6]}
    items = m.UserItem.query \
            .join(m.Item) \
            .add_columns(m.Item.url, m.Item.title, m.Item.feed_id, m.Item.updated_at, m.Item.enclosure_url, m.Item.enclosure_type) \
            .filter(m.UserItem.user == current_user) \
            .filter(item_q) \
            .order_by(m.Item.updated_at.desc())
    try:
        feed_id = int(feed_id)
        items = items.filter(m.Item.feed_id == feed_id)
    except ValueError:
        if feed_id == 'playing':
            items = items.filter(m.UserItem.play_position != 0)
    feeds = []
    for feed in m.Feed.query \
        .join(m.FeedGroup).join(m.Group) \
        .filter(m.Group.user == current_user) \
        .order_by(db.func.lower(m.Feed.title)) \
        .all():

        feeds.append({
            'id': feed.id,
            'title': feed.title,
            'is_podcast': feed.is_podcast,
            'url': feed.url,
            'fetched_at': current_user.localize(feed.fetched_at),
            'fetch_failed': feed.fetch_failed,
            'subscribed': 1,
            'active': feed_id == feed.id,
        })
    counts = {f_id: c for f_id, c in db.session.query(m.Feed.id, db.func.count(m.UserItem.item_id)) \
        .select_from(m.Feed).join(m.Item).join(m.UserItem) \
        .filter(m.UserItem.user == current_user) \
        .filter(item_q) \
        .group_by(m.Feed.id).all()}
    counts['total'] = sum(counts.values())
    return map(item_to_dict, items), feeds, counts

@feed_blueprint.route('/feeds/all/items', methods=['GET'], defaults={'feed_id': 'all', 'liked': False})
@feed_blueprint.route('/feeds/playing/items', methods=['GET'], defaults={'feed_id': 'playing', 'liked': False})
@feed_blueprint.route('/feeds/<int:feed_id>/items', methods=['GET'], defaults={'liked': False})
@feed_blueprint.route('/feeds/all/items/liked', methods=['GET'], defaults={'feed_id': 'all', 'liked': True})
@feed_blueprint.route('/feeds/playing/items/liked', methods=['GET'], defaults={'feed_id': 'playing', 'liked': True})
@feed_blueprint.route('/feeds/<int:feed_id>/items/liked', methods=['GET'], defaults={'liked': True})
@jwt_required
def items(liked, feed_id):
    user_item_filter = m.UserItem.liked == True if liked else m.UserItem.read == False
    items, feeds, counts = get_items_feeds(feed_id, user_item_filter)

    feed = None
    played_value, paid_value, paid_value_amounts, actions = 0, 0, [], []
    if feed_id == 'all':
        show_player = any(f['is_podcast'] for f in feeds)
    elif feed_id == 'playing':
        show_player = True
    else:
        feed = m.Feed.query.get_or_404(feed_id)
        show_player = feed.is_podcast
        q = db.session.query(m.UserItem) \
            .filter(m.UserItem.user_id == current_user.id, m.UserItem.item_id == m.Item.id, m.Item.feed_id == feed_id)
        sum_q = q.statement.with_only_columns([
            db.func.coalesce(db.func.sum(m.UserItem.stream_value_played), 0),
            db.func.coalesce(db.func.sum(m.UserItem.stream_value_paid), 0)])
        played_value, paid_value = q.session.execute(sum_q).one()
        paid_value_amounts = m.Action.get_total_amounts(current_user, feed_id)
        actions = m.Action.query.filter_by(user_id=current_user.id, feed_id=feed_id).order_by(m.Action.date)

    return render_template('items.html', liked=liked, user=current_user,
        feeds=feeds, items=items, counts=counts,
        feed=feed, show_player=show_player,
        played_value=played_value, paid_value=paid_value, paid_value_amounts=paid_value_amounts, actions=actions)

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
def add_website():
    if request.method == 'GET':
        return render_template('add_website.html', user=current_user,
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
            return redirect(url_for('feed.add_website'))
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
        return redirect(url_for('feed.items', liked=False))
    else:
        form = forms.FollowFeedForm()
        form.url.choices = alt_links
        return render_template('add_website.html',
            user=current_user,
            form=form, jwt_csrf_token=request.cookies.get('csrf_access_token'))

@feed_blueprint.route('/feeds/podcasts/search', methods=['GET', 'POST'])
@jwt_required
def search_podcasts():
    if request.method == 'GET':
        return render_template('search_podcasts.html', user=current_user,
            form=forms.SearchPodcastForm(), jwt_csrf_token=request.cookies.get('csrf_access_token'))

    q = m.Feed.query.join(m.FeedGroup).join(m.Group).filter(m.Group.user == current_user).all()
    subscribed_urls = {f.url for f in q}
    result = get_podcastindex().search(request.form['keywords'])
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
    return render_template('search_podcasts.html',
        user=current_user,
        podcastindex_feeds=feeds,
        form=forms.SearchPodcastForm(), jwt_csrf_token=request.cookies.get('csrf_access_token'))

@feed_blueprint.route('/feeds/podcasts/follow', methods=['POST'])
@jwt_required
def follow_podcast():
    feed_url = request.form['url']
    feed = m.Feed.query.filter_by(url=feed_url).one_or_none()
    if not feed:
        feed = m.Feed(
            url=request.form['url'],
            homepage_url=request.form['homepage_url'],
            title=request.form['title'])
        db.session.add(feed)
    parsed_feed = parse_feed(feed.url)
    if not parsed_feed:
        return jsonify(ok=False)
    feed_from_index = get_podcastindex().podcastByFeedUrl(feed_url)
    value_from_index = feed_from_index.get('feed', {}).get('value') if feed_from_index else None
    feed.update(parsed_feed)
    feed.update_value_spec(parsed_feed['value_spec'], parsed_feed['value_recipients'], value_from_index)
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
    return jsonify(ok=True)

@feed_blueprint.route('/feeds/podcasts/unfollow', methods=['POST'])
@jwt_required
def unfollow_podcast():
    feed = m.Feed.query.filter_by(url=request.form['url']).one_or_none()
    if feed:
        for fg in m.FeedGroup.query.join(m.Group).filter(m.Group.user == current_user, m.FeedGroup.feed == feed):
            db.session.delete(fg)
        db.session.commit()
        # TODO: delete items!
    return jsonify(ok=True)

def update_item(item_id, do):
    user_item = m.UserItem.query.filter_by(user=current_user, item_id=item_id).first()
    do(user_item)
    db.session.add(user_item)
    db.session.commit()
    return jsonify(ok=True)

@feed_blueprint.route('/feeds/<int:feed_id>/items/<int:item_id>/like', methods=['POST'])
@jwt_required
def like_item(feed_id, item_id):
    def update(ui):
        ui.liked = bool(int(request.form['value']))
    return update_item(item_id, update)

@feed_blueprint.route('/feeds/<int:feed_id>/items/<int:item_id>/hide', methods=['POST'])
@jwt_required
def hide_item(feed_id, item_id):
    def update(ui):
        ui.read = bool(int(request.form['value']))
    return update_item(item_id, update)

@feed_blueprint.route('/feeds/<int:feed_id>/items/<int:item_id>/position', methods=['POST'])
@jwt_required
def update_item_position(feed_id, item_id):
    def update(ui):
        ui.play_position = int(float(request.form['value']))
    return update_item(item_id, update)

# NB: the "value" here refers to the podcast:value interval which is a minute
# see: https://github.com/Podcastindex-org/podcast-namespace/blob/main/value/value.md#payment-intervals
@feed_blueprint.route('/feeds/<int:feed_id>/items/<int:item_id>/played-value', methods=['POST'])
@jwt_required
def increment_value_item(feed_id, item_id):
    def update(ui):
        ui.stream_value_played += int(request.form['value'])
    return update_item(item_id, update)

@feed_blueprint.route('/feeds/<int:feed_id>/send-value', methods=['POST'])
@feed_blueprint.route('/feeds/<int:feed_id>/items/<int:item_id>/send-value', methods=['POST'])
@jwt_required
def send_value(feed_id, item_id=None):
    feed = m.Feed.query.get_or_404(feed_id)
    user_items = None

    user_item = m.UserItem.query.get_or_404((current_user.id, item_id)) if item_id else None

    item = user_item.item if item_id else None
    ts = int(request.form['ts']) if 'ts' in request.form else None

    action = request.form['action']
    total_amount = int(request.form['amount'])
    total_amount_msat = total_amount * 1000

    if action == m.Action.Actions.stream.value:
        user_items = list(m.UserItem.query \
            .filter(m.UserItem.user == current_user) \
            .filter(m.UserItem.item_id == m.Item.id).filter(m.Item.feed_id == feed_id) \
            .filter(m.UserItem.stream_value_played > m.UserItem.stream_value_paid).all())
        total_value_to_pay = sum(i.stream_value_played - i.stream_value_paid for i in user_items)

    errors = []
    success_count = 0
    recipient_amount_sum_msat = 0
    for recipient_id, recipient_amount_msat in (item or feed).value_spec.split_amount(total_amount_msat).items():
        recipient_amount_sum_msat += recipient_amount_msat
        recipient = m.ValueRecipient.query.filter_by(id=recipient_id).first()
        try:
            if action == m.Action.Actions.boost.value:
                tlv = payments.get_podcast_tlv(recipient_amount_msat, current_user, action, feed, item, ts)
            elif action == m.Action.Actions.stream.value:
                tlvs = []
                for i in user_items:
                    amount_ratio = (i.stream_value_played - i.stream_value_paid) / total_value_to_pay
                    amount_msat = int(recipient_amount_msat * amount_ratio)
                    tlv = payments.get_podcast_tlv(amount_msat, current_user, action, feed, i.item)
                    tlvs.append(tlv)
                tlv = tlvs[0] if len(tlvs) == 1 else tlvs
            else:
                return "Invalid action.", 400

            payments.send_payment(recipient, amount_msat=recipient_amount_msat, podcast_tlv=tlv)

            success_count += 1
        except payments.PaymentFailed as e:
            app.logger.exception(e)
            error = m.Error(
                address=recipient.address, amount_msat=recipient_amount_msat,
                item_ids=str(item_id or ''), custom_records=json.dumps(e.custom_records),
                message=str(e))
            errors.append(error)

    if recipient_amount_sum_msat != total_amount_msat:
        app.logger.warn("Sum after splitting amongst recipients (%s) does not match original amount (%s)." % (recipient_amount_sum_msat, total_amount_msat))

    if success_count:
        if user_items:
            for user_item in user_items:
                user_item.stream_value_paid = user_item.stream_value_played
                db.session.add(user_item)
        a = m.Action(
            user=current_user,
            feed_id=feed_id,
            action=action,
            amount_msat=total_amount_msat,
            item=item,
            ts=ts,
            errors=errors)
        db.session.add(a)
        db.session.commit()
        return jsonify(ok=True, has_errors=bool(errors))
    else:
        return jsonify(ok=False)
