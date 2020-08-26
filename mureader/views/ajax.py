
from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user, get_jwt_identity

from mureader import models
from mureader.main import app, db
from mureader.views.utils import jwt_required

ajax_blueprint = Blueprint('ajax', __name__)

@ajax_blueprint.route('/like', methods=['POST'])
@jwt_required
def like():
    entry_id = request.form['entry_id']
    user_entry = models.UserEntry.query.filter_by(user=current_user, entry_id=entry_id).first()
    liked = bool(int(request.form['value']))
    if not user_entry:
        if liked: # you could like an entry that is not in your feed (if you see it in somebody else's feed)
            user_entry = models.UserEntry(user=current_user, entry_id=entry_id)
        else: # unliking a missing item should simply be ignored
            return jsonify(ok=True)
    user_entry.liked = liked
    db.session.add(user_entry)
    db.session.commit()
    return jsonify(ok=True)

@ajax_blueprint.route('/delete', methods=['POST'])
@jwt_required
def delete():
    entry_id = request.form['entry_id']
    if bool(int(request.form['value'])):
        models.UserEntry.query.filter_by(user=current_user, entry_id=entry_id).delete()
    else:
        db.session.add(models.UserEntry(user=current_user, entry_id=entry_id))
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
            for ue in models.UserEntry.query \
                .join(models.Entry) \
                .filter(models.UserEntry.user==current_user, models.UserEntry.liked==False, models.Entry.feed_id==feed_id):
                db.session.delete(ue)
    else:
        db.session.add(models.Subscription(user=current_user, feed_id=feed_id))
        if affect_news:
            existing_entry_ids = {ue.entry_id for ue in models.UserEntry.query.join(models.Entry).filter(models.UserEntry.user==current_user, models.Entry.feed_id==feed_id)}
            for entry in models.Feed.query.filter_by(id=feed_id).first().entries:
                if entry.id not in existing_entry_ids:
                    db.session.add(models.UserEntry(user=current_user, entry=entry))
    db.session.commit()
    return jsonify(ok=True)
