import datetime

DEBUG = False
BCRYPT_LOG_ROUNDS = 13
PROPAGATE_EXCEPTIONS = False
SQLALCHEMY_TRACK_MODIFICATIONS = False
JWT_TOKEN_LOCATION = 'cookies'
JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(days=1)
JWT_CSRF_CHECK_FORM = True
JWT_ACCESS_CSRF_FIELD_NAME = 'jwt_csrf_token'
MAIL_DEFAULT_SENDER = 'hello@musocial.me'

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:80.0) Gecko/20100101 Firefox/80.0"
