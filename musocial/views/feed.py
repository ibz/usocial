from flask import Blueprint, render_template
from flask_jwt_extended import current_user
from flask_jwt_extended.exceptions import NoAuthorizationError

from musocial import models
from musocial.main import jwt_required

feed_blueprint = Blueprint('feed', __name__)

@feed_blueprint.route('/news', methods=['GET'])
@jwt_required
def news():
    items = models.UserItem.query \
        .join(models.Item) \
        .filter(models.UserItem.user==current_user, models.UserItem.liked==False)
    items = items.order_by(models.Item.updated_at.desc())
    return render_template('news.html', items=items, user=current_user)

@feed_blueprint.route('/liked', methods=['GET'])
@jwt_required
def liked():
    items = models.UserItem.query \
        .join(models.Item) \
        .filter(models.UserItem.user==current_user, models.UserItem.liked==True) \
        .order_by(models.Item.updated_at.desc())
    return render_template('news.html', items=items, user=current_user)
