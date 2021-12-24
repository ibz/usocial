
from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user, get_jwt_identity

from musocial import models
from musocial.main import app, db, jwt_required

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

@ajax_blueprint.route('/delete', methods=['POST'])
@jwt_required
def delete():
    item_id = request.form['item_id']
    if bool(int(request.form['value'])):
        models.UserItem.query.filter_by(user=current_user, item_id=item_id).delete()
    else:
        db.session.add(models.UserItem(user=current_user, item_id=item_id))
    db.session.commit()
    return jsonify(ok=True)

@ajax_blueprint.route('/follow', methods=['POST'])
@jwt_required
def follow():
    feed_id = request.form['feed_id']
    affect_news = bool(int(request.form['affect_news']))
    if not bool(int(request.form['value'])):
        models.Subscription.query.filter_by(user=current_user, feed_id=feed_id).delete()
        if affect_news:
            for ue in models.UserItem.query \
                .join(models.Item) \
                .filter(models.UserItem.user==current_user, models.UserItem.liked==False, models.Item.feed_id==feed_id):
                db.session.delete(ue)
    else:
        db.session.add(models.Subscription(user=current_user, feed_id=feed_id))
        if affect_news:
            existing_item_ids = {ue.item_id for ue in models.UserItem.query.join(models.Item).filter(models.UserItem.user==current_user, models.Item.feed_id==feed_id)}
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
            title=request.form['title'],
            feed_type=models.Feed.FEED_TYPE_PODCAST)
        db.session.add(feed)
        db.session.commit()
    db.session.add(models.Subscription(user=current_user, feed_id=feed.id))
    db.session.commit()
    return jsonify(ok=True)

@ajax_blueprint.route('/unfollow-podcast', methods=['POST'])
@jwt_required
def unfollow_podcast():
    feed = models.Feed.query.filter_by(url=request.form['url']).one_or_none()
    if feed:
        models.Subscription.query.filter_by(user=current_user, feed=feed).delete()
        db.session.commit()
    return jsonify(ok=True)
