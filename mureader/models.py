import base64
from datetime import datetime
import os
from urllib.parse import urlparse

from babel.dates import format_timedelta
import onetimepass

from mureader.main import db, bcrypt

def get_config():
    import app
    return app.config

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    email_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    username = db.Column(db.String(255), unique=True)
    public_profile = db.Column(db.Boolean, nullable=False, default=False)
    otp_secret = db.Column(db.String(16))
    password = db.Column(db.String(255))
    registered_on = db.Column(db.DateTime, nullable=False)
    is_pro = db.Column(db.Boolean, nullable=False, default=False)

    subscriptions = db.relationship('Subscription')

    def __init__(self, email):
        self.email = email
        self.otp_secret = base64.b32encode(os.urandom(10)).decode('utf-8')
        self.registered_on = datetime.now()

    @property
    def display_name(self):
        return self.username or self.email

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password, get_config().get('BCRYPT_LOG_ROUNDS')).decode()

    def get_totp_uri(self):
        return 'otpauth://totp/mureader:{0}?secret={1}&issuer=mureader'.format(self.email, self.otp_secret)

    def verify_totp(self, token):
        return onetimepass.valid_totp(token, self.otp_secret)

    def verify_password(self, password):
        if not self.password:
            return False
        return bcrypt.check_password_hash(self.password, password)

class Feed(db.Model):
    __tablename__ = 'feeds'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    url = db.Column(db.String(1000), unique=True, nullable=False)
    title = db.Column(db.String(1000), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=True)
    fetched_at = db.Column(db.DateTime, nullable=True)

    entries = db.relationship('Entry')

class Subscription(db.Model):
    __tablename__ = 'subscriptions'

    user_id = db.Column(db.Integer, db.ForeignKey(User.id), primary_key=True)
    user = db.relationship(User)
    feed_id = db.Column(db.Integer, db.ForeignKey(Feed.id), primary_key=True)
    feed = db.relationship(Feed)

class Entry(db.Model):
    __tablename__ = 'entries'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    feed_id = db.Column(db.Integer, db.ForeignKey(Feed.id))
    url = db.Column(db.String(1000), unique=True, nullable=False)
    title = db.Column(db.String(1000))
    updated_at = db.Column(db.DateTime)

    @property
    def domain_name(self):
        return urlparse(self.url).netloc

    @property
    def relative_date(self):
        return format_timedelta(self.updated_at - datetime.now(), add_direction=True)

class UserEntry(db.Model):
    __tablename__ = 'user_entries'

    user_id = db.Column(db.Integer, db.ForeignKey(User.id), primary_key=True)
    user = db.relationship(User)
    entry_id = db.Column(db.Integer, db.ForeignKey(Entry.id), primary_key=True)
    entry = db.relationship(Entry)
    liked = db.Column(db.Boolean, nullable=False, default=False)
