from flask import Blueprint, jsonify, request

from usocial import models
from usocial.main import db, csrf

api_blueprint = Blueprint('api', __name__)

@csrf.exempt
@api_blueprint.route('/api', methods=['POST'])
def api():
    res = {'api_version': "1"}

    if request.form.get('api_key'):
        user = models.User.query.filter_by(fever_api_key=request.form['api_key']).one_or_none()
    else:
        user = models.User.query.filter_by(username=models.User.DEFAULT_USERNAME, password=None).one_or_none()
    if not user:
        res['auth'] = 0
        return jsonify(res)
    res['auth'] = 1

    if 'feeds' in request.args:
        group_ids = [g.id for g in models.Group.query.filter_by(user_id=user.id).all()]
        feed_ids = [fg.feed_id for fg in models.FeedGroup.query.filter(models.FeedGroup.group_id.in_(group_ids)).all()]
        res['feeds'] = [{
            'id': f.id,
            'title': f.title,
            'url': f.url,
            'site_url': f.homepage_url,
            'last_updated_on_time': int(f.updated_at.timestamp()) if f.updated_at else 0
            }
            for f in models.Feed.query.filter(models.Feed.id.in_(feed_ids)).all()]
    if 'items' in request.args:
        res['items'] = [{
            'id': i.id,
            'feed_id': i.feed_id,
            'title': i.title,
            'url': i.url,
            'html': i.content_from_feed,
            'created_on_time': int(i.updated_at.timestamp()),
            'is_read': int(ui.read),
            'is_saved': int(ui.liked)
            }
            for i, ui in db.session.query(models.Item, models.UserItem).select_from(models.Item).join(models.UserItem).filter(models.UserItem.user == user).all()]

    return jsonify(res)
