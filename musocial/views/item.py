from flask import Blueprint, jsonify, render_template, request
from flask_jwt_extended import current_user

from musocial import models as m
from musocial.main import db, jwt_required

item_blueprint = Blueprint('item', __name__)

def get_items_feeds(q):
    items = []
    if 'feed_id' in request.args:
        items = [i for i in m.UserItem.query \
            .join(m.Item) \
            .filter(m.UserItem.user == current_user, m.Item.feed_id == int(request.args['feed_id'])) \
            .filter(q)]
    else:
        items = [i for i in m.UserItem.query \
            .join(m.Item) \
            .filter(m.UserItem.user == current_user) \
            .filter(q)]
    feeds = []
    for feed, feed_group in db.session.query(m.Feed, m.FeedGroup) \
        .select_from(m.Feed).join(m.FeedGroup).join(m.Group) \
        .filter(m.Group.user == current_user).all():
        feeds.append({
            'id': feed.id,
            'title': feed.title,
            'url': feed.url,
            'subscribed': 1,
            'active': int(request.args.get('feed_id') or 0) == feed.id,
        })
    return items, feeds

@item_blueprint.route('/items', methods=['GET'])
@jwt_required
def index():
    items, feeds = get_items_feeds(m.UserItem.read == False)
    show_player = items and all(i.item.enclosure_url for i in items)
    return render_template('items.html', feeds=feeds, items=items, show_player=show_player, user=current_user)

@item_blueprint.route('/items/liked', methods=['GET'])
@jwt_required
def liked():
    items, feeds = get_items_feeds(m.UserItem.liked == True)
    show_player = items and all(i.item.enclosure_url for i in items)
    return render_template('items.html', feeds=feeds, items=items, liked=True, show_player=show_player, user=current_user)

@item_blueprint.route('/items/<int:item_id>/like', methods=['POST'])
@jwt_required
def like(item_id):
    user_item = m.UserItem.query.filter_by(user=current_user, item_id=item_id).first()
    liked = bool(int(request.form['value']))
    if not user_item:
        if liked: # you could like an item that is not in your feed (if you see it in somebody else's feed)
            user_item = m.UserItem(user=current_user, item_id=item_id)
        else: # unliking a missing item should simply be ignored
            return jsonify(ok=True)
    user_item.liked = liked
    db.session.add(user_item)
    db.session.commit()
    return jsonify(ok=True)

@item_blueprint.route('/items/<int:item_id>/hide', methods=['POST'])
@jwt_required
def hide(item_id):
    user_item = m.UserItem.query.filter_by(user=current_user, item_id=item_id).first()
    user_item.read = bool(int(request.form['value']))
    db.session.add(user_item)
    db.session.commit()
    return jsonify(ok=True)
