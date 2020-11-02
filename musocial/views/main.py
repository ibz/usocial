from flask import Blueprint, redirect, render_template, Response, url_for
from flask_jwt_extended import current_user, verify_jwt_in_request
from flask_jwt_extended.exceptions import NoAuthorizationError

main_blueprint = Blueprint('main', __name__)

@main_blueprint.route('/sitemap.xml', methods=['GET'])
def sitemap_xml():
    return Response("""<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>http://musocial.me/about</loc></url>
        </urlset>""", mimetype='application/xml')

@main_blueprint.route('/robots.txt', methods=['GET'])
def robots_txt():
    return Response("""User-agent: *
Allow: /about
Disallow: /
""", mimetype='text/plain')

@main_blueprint.route('/', methods=['GET'])
def index():
    try:
        verify_jwt_in_request()
    except NoAuthorizationError:
        return redirect(url_for('main.about'))

    return redirect(url_for('feed.news'))

@main_blueprint.route('/about', methods=['GET'])
def about():
    try:
        verify_jwt_in_request()
    except NoAuthorizationError:
        pass
    return render_template('about.html', user=current_user)
