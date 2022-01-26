from flask import Blueprint, redirect, render_template, Response, url_for
from flask_jwt_extended import create_access_token, create_refresh_token, current_user, set_access_cookies, set_refresh_cookies, verify_jwt_in_request
from flask_jwt_extended.exceptions import NoAuthorizationError

from usocial import models

import config

main_blueprint = Blueprint('main', __name__)

@main_blueprint.route('/', methods=['GET'])
def index():
    try:
        verify_jwt_in_request()
    except NoAuthorizationError:
        default_user = models.User.query.filter_by(id=config.DEFAULT_USER_ID).first()
        if default_user and not default_user.password:
            response = redirect(url_for('feed.items'))
            set_access_cookies(response, create_access_token(identity=default_user.username))
            set_refresh_cookies(response, create_refresh_token(identity=default_user.username))
            return response
        else:
            return redirect(url_for('account.login'))
    return redirect(url_for('feed.items'))