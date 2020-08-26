from flask import Flask, redirect, url_for
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import JWTManager
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
    def __init__(self, import_name, instance_relative_config):
        super().__init__(import_name, instance_relative_config=instance_relative_config)
        self.initialized = False

    def __call__(self, environ, start_response):
        if not self.initialized:
            from mureader.views.ajax import ajax_blueprint
            from mureader.views.feed import feed_blueprint
            from mureader.views.main import main_blueprint
            from mureader.views.user import user_blueprint
            app.register_blueprint(ajax_blueprint)
            app.register_blueprint(feed_blueprint)
            app.register_blueprint(main_blueprint)
            app.register_blueprint(user_blueprint)
            self.initialized = True
        return super().__call__(environ, start_response)

app = MyFlask(__name__, instance_relative_config=True)
app.config.from_object('config')
app.config.from_pyfile('config.py', silent=True)

CORS(app)
CSRFProtect(app)

bcrypt = Bcrypt(app)
db = SQLAlchemy(app)
jwt = JWTManager(app)
mail = Mail(app)
