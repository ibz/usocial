from flask import Blueprint, redirect, url_for

main_blueprint = Blueprint('main', __name__)

@main_blueprint.route('/', methods=['GET'])
def index():
    return redirect(url_for('feed.news'))
