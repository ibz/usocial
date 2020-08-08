from datetime import datetime
from urllib.parse import urlparse

from babel.dates import format_timedelta

from ureader import app, db, bcrypt

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    registered_on = db.Column(db.DateTime, nullable=False)

    subscriptions = db.relationship('Subscription')

    def __init__(self, email, password):
        self.email = email
        self.password = bcrypt.generate_password_hash(password, app.config.get('BCRYPT_LOG_ROUNDS')).decode()
        self.registered_on = datetime.now()

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