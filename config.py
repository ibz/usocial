import datetime
import os

DEBUG = False
BCRYPT_LOG_ROUNDS = 13
PROPAGATE_EXCEPTIONS = False
SQLALCHEMY_TRACK_MODIFICATIONS = False
JWT_TOKEN_LOCATION = 'cookies'
JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(days=1)
JWT_CSRF_CHECK_FORM = True
JWT_ACCESS_CSRF_FIELD_NAME = 'jwt_csrf_token'

PODCASTINDEX_API_KEY = 'ZBJFW42QYWT6C8PWB7EZ'
PODCASTINDEX_API_SECRET = 'dyHyKXSpJjn4J4rXYpj^DPsWNLjJ2j#VjJ38st9Q'

SQLALCHEMY_DATABASE_URI = 'sqlite:///../instance/usocial.db'

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:80.0) Gecko/20100101 Firefox/80.0"

LND_IP = os.environ.get("LND_IP")
LND_GRPC_PORT = os.environ.get("LND_GRPC_PORT")
LND_DIR = os.environ.get("LND_DIR")

DEFAULT_USER_PASSWORD = os.environ.get("DEFAULT_USER_PASSWORD")

VERSION = 'dev'
BUILD = '?'
