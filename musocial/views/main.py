from flask import Blueprint, redirect, render_template, Response, url_for
from flask_jwt_extended import create_access_token, create_refresh_token, current_user, set_access_cookies, set_refresh_cookies, verify_jwt_in_request
from flask_jwt_extended.exceptions import NoAuthorizationError

from musocial import models

import config

main_blueprint = Blueprint('main', __name__)

@main_blueprint.route('/sitemap.xml', methods=['GET'])
def sitemap_xml():
    return Response("""<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        </urlset>""", mimetype='application/xml')

@main_blueprint.route('/robots.txt', methods=['GET'])
def robots_txt():
    return Response("""User-agent: *
Disallow: /
""", mimetype='text/plain')

@main_blueprint.route('/', methods=['GET'])
def index():
    try:
        verify_jwt_in_request()
    except NoAuthorizationError:
        default_user = models.User.query.filter_by(id=config.DEFAULT_USER_ID).first()
        if default_user and not default_user.password:
            response = redirect(url_for('feed.news'))
            set_access_cookies(response, create_access_token(identity=default_user.username))
            set_refresh_cookies(response, create_refresh_token(identity=default_user.username))
            return response
        else:
            return redirect(url_for('user.login'))
    return redirect(url_for('feed.news'))
