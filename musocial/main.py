from functools import wraps
import os
from flask import Flask, redirect, url_for
from flask.cli import with_appcontext
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import create_access_token, JWTManager, set_access_cookies, verify_jwt_in_request
from flask_jwt_extended.exceptions import NoAuthorizationError
from flask_sqlalchemy import SQLAlchemy
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
            from musocial.views.account import account_blueprint
            app.register_blueprint(account_blueprint)
            from musocial.views.api import api_blueprint
            app.register_blueprint(api_blueprint)
            from musocial.views.feed import feed_blueprint
            app.register_blueprint(feed_blueprint)
            from musocial.views.main import main_blueprint
            app.register_blueprint(main_blueprint)
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

@app.cli.command("create-db")
@with_appcontext
def create_db():
    from musocial import models
    models.create_all()

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
    from musocial import models
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
