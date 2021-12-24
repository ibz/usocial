from datetime import datetime
import os
import os.path
from urllib.parse import urlparse

from babel.dates import format_timedelta

from musocial.main import app, db, bcrypt
from musocial.parser import strip_protocol


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255))
    registered_on = db.Column(db.DateTime, nullable=False)
    public = db.Column(db.Boolean, nullable=False, default=False)

    groups = db.relationship('Group', backref='user')

    def __init__(self, username):
        self.username = username
        self.registered_on = datetime.now()

    def set_password(self, password):
        if password:
            self.password = bcrypt.generate_password_hash(password, app.config.get('BCRYPT_LOG_ROUNDS')).decode()
        else:
            self.password = None

    def verify_password(self, password):
        if not self.password:
            return False
        return bcrypt.check_password_hash(self.password, password)

class Group(db.Model):
    __tablename__ = 'groups'

    DEFAULT_GROUP = 'Default'
    PODCASTS_GROUP = 'Podcasts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    name = db.Column(db.String(1000))
    public = db.Column(db.Boolean, nullable=False, default=False)

class Feed(db.Model):
    __tablename__ = 'feeds'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    url = db.Column(db.String(1000), unique=True, nullable=False)
    homepage_url = db.Column(db.String(1000), nullable=False)
    title = db.Column(db.String(1000), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=True)
    fetched_at = db.Column(db.DateTime, nullable=True)
    fetch_failed = db.Column(db.Boolean, default=False)

    items = db.relationship('Item')

    @property
    def domain_name(self):
        return urlparse(self.homepage_url).netloc

    def update(self, parsed_feed):
        self.fetched_at = datetime.now()
        if not parsed_feed:
            self.fetch_failed = True
            return
        self.fetch_failed = False
        feed_domain = urlparse(self.url).netloc
        urls = {strip_protocol(self.url)}
        for e in parsed_feed['items']:
            url = strip_protocol(e['url'])
            if url.startswith(feed_domain):
                urls.add(url)
        common_prefix = os.path.commonprefix(list(urls))
        self.homepage_url = f'http://{common_prefix}'
        self.title = parsed_feed['title']
        self.updated_at = parsed_feed['updated_at']

    def update_items(self, parsed_feed):
        new_item_urls = set()
        new_items = []
        updated_items = []
        for e in parsed_feed['items']:
            item = Item.query.filter_by(url=e['url']).first()
            if not item:
                if e['url'] not in new_item_urls:
                    item = Item(feed_id=self.id, url=e['url'], title=e['title'],
                        content_from_feed=e['content'],
                        updated_at=e['updated_at'])
                    new_items.append(item)
                    new_item_urls.add(e['url'])
            elif item.title != e['title'] or item.updated_at != e['updated_at']:
                item.title = e['title']
                item.content_from_feed = e['content']
                item.updated_at = e['updated_at']
                updated_items.append(item)
        return new_items, updated_items

class FeedGroup(db.Model):
    __tablename__ = 'feed_groups'

    feed_id = db.Column(db.Integer, db.ForeignKey(Feed.id), primary_key=True)
    feed = db.relationship(Feed)
    group_id = db.Column(db.Integer, db.ForeignKey(Group.id), primary_key=True)
    group = db.relationship(Group)

class Item(db.Model):
    __tablename__ = 'items'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    feed_id = db.Column(db.Integer, db.ForeignKey(Feed.id))
    url = db.Column(db.String(1000), unique=True, nullable=False)
    title = db.Column(db.String(1000))
    content_from_feed = db.Column(db.String(10000))
    updated_at = db.Column(db.DateTime)

    @property
    def domain_name(self):
        return urlparse(self.url).netloc

    @property
    def relative_date(self):
        return format_timedelta(self.updated_at - datetime.now(), add_direction=True)

class UserItem(db.Model):
    __tablename__ = 'user_items'

    user_id = db.Column(db.Integer, db.ForeignKey(User.id), primary_key=True)
    user = db.relationship(User)
    item_id = db.Column(db.Integer, db.ForeignKey(Item.id), primary_key=True)
    item = db.relationship(Item)
    liked = db.Column(db.Boolean, nullable=False, default=False)
