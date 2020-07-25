import datetime
import os

class BaseConfig:
    SECRET_KEY = os.getenv('SECRET_KEY', 'my_precious')
    DEBUG = True
    BCRYPT_LOG_ROUNDS = 13
    PROPAGATE_EXCEPTIONS = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///db/app.db')
    JWT_TOKEN_LOCATION = 'cookies'
    JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(days=1)
    JWT_CSRF_CHECK_FORM = True
    JWT_ACCESS_CSRF_FIELD_NAME = 'jwt_csrf_token'
