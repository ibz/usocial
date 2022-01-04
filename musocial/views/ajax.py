
from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user, get_jwt_identity

from musocial import models
from musocial.main import app, db, jwt_required

from musocial.parser import parse_feed

ajax_blueprint = Blueprint('ajax', __name__)

@ajax_blueprint.route('/like', methods=['POST'])
@jwt_required
def like():
    item_id = request.form['item_id']
    user_item = models.UserItem.query.filter_by(user=current_user, item_id=item_id).first()
    liked = bool(int(request.form['value']))
    if not user_item:
        if liked: # you could like an item that is not in your feed (if you see it in somebody else's feed)
            user_item = models.UserItem(user=current_user, item_id=item_id)
        else: # unliking a missing item should simply be ignored
            return jsonify(ok=True)
    user_item.liked = liked
    db.session.add(user_item)
    db.session.commit()
    return jsonify(ok=True)

@ajax_blueprint.route('/hide', methods=['POST'])
@jwt_required
def hide():
    item_id = request.form['item_id']
    user_item = models.UserItem.query.filter_by(user=current_user, item_id=item_id).first()
    user_item.read = bool(int(request.form['value']))
    db.session.add(user_item)
    db.session.commit()
    return jsonify(ok=True)

@ajax_blueprint.route('/follow', methods=['POST'])
@jwt_required
def follow():
    feed_id = request.form['feed_id']
    if not bool(int(request.form['value'])): # unfollow
        for fg in models.FeedGroup.query \
            .join(models.Group) \
            .filter(models.Group.user == current_user, models.FeedGroup.feed_id == feed_id):
            db.session.delete(fg)
        for ue in models.UserItem.query \
            .join(models.Item) \
            .filter(models.UserItem.user == current_user, models.UserItem.liked == False, models.Item.feed_id == feed_id):
            db.session.delete(ue)
    else:
        group = models.Group.query.filter(models.Group.user == current_user, models.Group.name == models.Group.DEFAULT_GROUP).one_or_none()
        if not group:
            group = models.Group(user=current_user, name=models.Group.DEFAULT_GROUP)
            db.session.add(group)
            db.session.commit()
        db.session.add(models.FeedGroup(group=group, feed_id=feed_id))
        existing_item_ids = {ue.item_id for ue in models.UserItem.query.join(models.Item).filter(models.UserItem.user == current_user, models.Item.feed_id == feed_id)}
        for item in models.Feed.query.filter_by(id=feed_id).first().items:
            if item.id not in existing_item_ids:
                db.session.add(models.UserItem(user=current_user, item=item))
    db.session.commit()
    return jsonify(ok=True)

@ajax_blueprint.route('/follow-podcast', methods=['POST'])
@jwt_required
def follow_podcast():
    feed = models.Feed.query.filter_by(url=request.form['url']).one_or_none()
    if not feed:
        feed = models.Feed(
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
    group = models.Group.query.filter(models.Group.user == current_user, models.Group.name == models.Group.PODCASTS_GROUP).one_or_none()
    if not group:
        group = models.Group(user=current_user, name=models.Group.PODCASTS_GROUP)
        db.session.add(group)
        db.session.commit()
    db.session.add(models.FeedGroup(group=group, feed_id=feed.id))
    db.session.commit()
    existing_item_ids = {ue.item_id for ue in models.UserItem.query.join(models.Item).filter(models.UserItem.user == current_user, models.Item.feed_id == feed.id)}
    for item in feed.items:
        if item.id not in existing_item_ids:
            db.session.add(models.UserItem(user=current_user, item=item))
    db.session.commit()
    return jsonify(ok=True)

@ajax_blueprint.route('/unfollow-podcast', methods=['POST'])
@jwt_required
def unfollow_podcast():
    feed = models.Feed.query.filter_by(url=request.form['url']).one_or_none()
    if feed:
        for fg in models.FeedGroup.query.join(models.Group).filter(models.Group.user == current_user, models.FeedGroup.feed == feed):
            db.session.delete(fg)
        db.session.commit()
    return jsonify(ok=True)
