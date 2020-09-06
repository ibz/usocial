from functools import wraps
import os
from flask import Flask, redirect, url_for
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import JWTManager, verify_jwt_in_request
from flask_jwt_extended.exceptions import NoAuthorizationError
from flask_mail import Mail
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
        'level': 'INFO',
    }
})

class MyFlask(Flask):
    def __init__(self, import_name, instance_path):
        super().__init__(import_name, instance_path=instance_path, instance_relative_config=True)
        self.initialized = False

    def __call__(self, environ, start_response):
        if not self.initialized:
            from musocial.views.ajax import ajax_blueprint
            from musocial.views.feed import feed_blueprint
            from musocial.views.main import main_blueprint
            from musocial.views.user import user_blueprint
            app.register_blueprint(ajax_blueprint)
            app.register_blueprint(feed_blueprint)
            app.register_blueprint(main_blueprint)
            app.register_blueprint(user_blueprint)
            self.initialized = True
        return super().__call__(environ, start_response)

app = MyFlask(__name__, instance_path=os.environ.get('INSTANCE_PATH'))
app.config.from_object('config')
app.config.from_pyfile('config.py')

CORS(app)
CSRFProtect(app)

bcrypt = Bcrypt(app)
db = SQLAlchemy(app)
jwt = JWTManager(app)
mail = Mail(app)

@jwt.claims_verification_failed_loader
def no_jwt():
    return redirect(url_for('user.login'))

@jwt.expired_token_loader
def jwt_token_expired():
    return redirect(url_for('user.refresh_jwt'))

@jwt.user_loader_callback_loader
def load_user(email):
    from musocial import models
    return models.User.query.filter_by(email=email).first()

def jwt_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except NoAuthorizationError:
            return no_jwt()
        return fn(*args, **kwargs)
    return wrapper
