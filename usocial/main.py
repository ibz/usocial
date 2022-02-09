from functools import wraps
import os
import sys

import click
from flask import Flask, redirect, url_for
from flask.cli import with_appcontext
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import create_access_token, JWTManager, set_access_cookies, verify_jwt_in_request
from flask_jwt_extended.exceptions import NoAuthorizationError
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from flask_wtf.csrf import CSRFProtect

from logging.config import dictConfig

dictConfig({
    'version': 1,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
        }
    },
    'root': {
        'level': 'DEBUG',
    }
})

class MyFlask(Flask):
    def __init__(self, import_name):
        instance_path = os.environ.get('INSTANCE_PATH')

        super().__init__(import_name, instance_path=instance_path, instance_relative_config=True)

        self.initialized = False

    def __call__(self, environ, start_response):
        if not self.initialized:
            from usocial.controllers.account import account_blueprint
            app.register_blueprint(account_blueprint)
            from usocial.controllers.api import api_blueprint
            app.register_blueprint(api_blueprint)
            from usocial.controllers.feed import feed_blueprint
            app.register_blueprint(feed_blueprint)
            self.initialized = True
        return super().__call__(environ, start_response)

app = MyFlask(__name__)
app.config.from_object('config')
app.config.from_pyfile('config.py')

CORS(app)
csrf = CSRFProtect(app)

bcrypt = Bcrypt(app)
db = SQLAlchemy(app)
jwt = JWTManager(app)
migrate = Migrate(app, db)

@app.cli.command("create-db")
@with_appcontext
def create_db():
    from usocial import models as m
    m.create_all()

@app.cli.command("create-user")
@click.argument("username")
@with_appcontext
def create_user(username):
    try:
        from usocial import models as m
        db.session.add(m.User(username))
        db.session.commit()
    except IntegrityError:
        print("User already exists.")
        sys.exit(1)

@app.cli.command("fetch-feeds")
@with_appcontext
def fetch_feeds():
    from usocial import models
    from usocial.parser import parse_feed
    for feed in models.Feed.query.all():
        parsed_feed = parse_feed(feed.url)
        feed.update(parsed_feed)
        new_items_count = 0
        users_count = 0
        if parsed_feed:
            new_items, updated_items = feed.update_items(parsed_feed)
            for item in new_items + updated_items:
                db.session.add(item)
            if new_items:
                new_items_count = len(new_items)
                for user in models.User.query.join(models.Group).join(models.FeedGroup).join(models.Feed).filter(models.FeedGroup.feed == feed):
                    users_count += 1
                    for item in new_items:
                        db.session.add(models.UserItem(user=user, item=item))
        db.session.add(feed)
        db.session.commit()

        app.logger.info(f"Feed fetched: {feed.url}. New items: {new_items_count}. Affected users: {users_count}.")

@jwt.token_verification_failed_loader
def no_jwt():
    return redirect(url_for('account.login'))

@jwt.expired_token_loader
def jwt_token_expired(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    response = redirect(url_for('feed.items'))
    set_access_cookies(response, create_access_token(identity=identity))
    return response

@jwt.user_lookup_loader
def load_user(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    from usocial import models
    return models.User.query.filter_by(username=identity).one_or_none()

def jwt_required_wrapper(refresh):
    def jwt_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request(refresh)
            except NoAuthorizationError:
                return no_jwt()
            return fn(*args, **kwargs)
        return wrapper
    return jwt_required

jwt_required = jwt_required_wrapper(False)
refresh_jwt_required = jwt_required_wrapper(True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
