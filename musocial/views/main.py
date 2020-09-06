from flask import Blueprint, redirect, render_template, url_for
from flask_jwt_extended import current_user, verify_jwt_in_request
from flask_jwt_extended.exceptions import NoAuthorizationError

main_blueprint = Blueprint('main', __name__)

@main_blueprint.route('/', methods=['GET'])
def index():
    return redirect(url_for('feed.news'))

@main_blueprint.route('/about', methods=['GET'])
def about():
    try:
        verify_jwt_in_request()
    except NoAuthorizationError:
        pass
    return render_template('about.html', user=current_user)
