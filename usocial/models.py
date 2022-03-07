from datetime import datetime
import enum
import hashlib
import os
import os.path
import pytz
from urllib.parse import urljoin, urlparse

from babel.dates import format_timedelta

from usocial.main import app, db, bcrypt

import config

def strip_protocol(url):
    return url.replace('http://', '').replace('https://', '')

class User(db.Model):
    __tablename__ = 'users'

    DEFAULT_USERNAME = 'me'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255))
    fever_api_key = db.Column(db.String(255))
    registered_on = db.Column(db.DateTime, nullable=False)
    public = db.Column(db.Boolean, nullable=False, default=False)

    timezone = db.Column(db.String(100))
    audio_volume = db.Column(db.Float, nullable=False, default=1.0)

    groups = db.relationship('Group', backref='user')

    @classmethod
    def create_default_user(cls):
        app.logger.info("Creating the default user.")
        user = cls(cls.DEFAULT_USERNAME)
        if config.DEFAULT_USER_PASSWORD:
            app.logger.info("Setting password for the default user.")
            user.set_password(config.DEFAULT_USER_PASSWORD)
        return user

    def __init__(self, username):
        self.username = username
        self.fever_api_key = hashlib.md5(("%s:" % username).encode('utf-8')).hexdigest()
        self.registered_on = datetime.utcnow()

    def set_password(self, password):
        if password:
            self.password = bcrypt.generate_password_hash(password, config.BCRYPT_LOG_ROUNDS).decode()
        else:
            self.password = None
        self.fever_api_key = hashlib.md5(("%s:%s" % (self.username, password or "")).encode('utf-8')).hexdigest()

    def verify_password(self, password):
        if not self.password:
            return False
        return bcrypt.check_password_hash(self.password, password)

    def localize(self, d):
        if not d:
            return None
        else:
            if self.timezone:
                return d.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(self.timezone))
            else:
                return d

class Group(db.Model):
    __tablename__ = 'groups'

    DEFAULT_GROUP = 'Default'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    name = db.Column(db.String(1000))
    public = db.Column(db.Boolean, nullable=False, default=False)

class Feed(db.Model):
    __tablename__ = 'feeds'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    url = db.Column(db.String(1000), unique=True, nullable=False)
    homepage_url = db.Column(db.String(1000), nullable=False)
    title = db.Column(db.String(1000))
    is_podcast = db.Column(db.Boolean, nullable=False, default=False)
    updated_at = db.Column(db.DateTime)
    fetched_at = db.Column(db.DateTime)
    fetch_failed = db.Column(db.Boolean, default=False)
    parser = db.Column(db.Integer, nullable=False)

    items = db.relationship('Item', back_populates='feed')
    value_specs = db.relationship('ValueSpec')

    @property
    def domain_name(self):
        return urlparse(self.homepage_url).netloc

    @property
    def value_spec(self):
        # get value_spec for the feed (item_id is None)
        value_specs = [s for s in self.value_specs if s.item_id is None]
        assert len(value_specs) in (0, 1)
        return value_specs[0] if value_specs else None

    def update(self, parsed_feed):
        self.fetched_at = datetime.utcnow()
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
        common_prefix = os.path.commonprefix(list(urls)).strip('#?')
        self.homepage_url = f'http://{common_prefix}'
        self.title = parsed_feed['title']
        self.updated_at = parsed_feed['updated_at']
        self.parser = parsed_feed['parser']

        self.update_value_spec(parsed_feed['value_spec'], parsed_feed['value_recipients'])

    def update_value_spec(self, p_value_spec, p_value_recipients):
        value_spec = self.value_spec

        if not p_value_spec:
            if value_spec:
                db.session.delete(value_spec)
                app.logger.info(f"ValueSpec deleted for feed_id={self.id}")
        else: # got a value spec from the feed
            if value_spec:
                if value_spec.protocol != p_value_spec['protocol'] or value_spec.method != p_value_spec['method'] or value_spec.suggested_amount != p_value_spec['suggested_amount']:
                    value_spec.protocol = p_value_spec['protocol']
                    value_spec.method = p_value_spec['method']
                    value_spec.suggested_amount = p_value_spec['suggested_amount']
                    db.session.add(value_spec)
                    app.logger.info(f"ValueSpec changed for feed_id={self.id}: protocol {value_spec.protocol} -> {p_value_spec['protocol']}, method {value_spec.method} -> {p_value_spec['method']}, suggested_amount {value_spec.suggested_amount} -> {p_value_spec['suggested_amount']}")

                recipients_by_address = {r.address: r for r in value_spec.recipients}
                p_recipients_by_address = {p_r['address']: p_r for p_r in p_value_recipients}
                for deleted_a in set(recipients_by_address.keys()) - set(p_recipients_by_address.keys()):
                    db.session.delete(recipients_by_address[deleted_a])
                    del recipients_by_address[deleted_a]
                    app.logger.info(f"ValueSpec changed for feed_id={self.id}: recipient {deleted_a} removed")
                for added_a in set(p_recipients_by_address.keys()) - set(recipients_by_address.keys()):
                    p_recipient = p_recipients_by_address[added_a]
                    recipient = ValueRecipient(
                        value_spec_id=value_spec.id,
                        name=p_recipient['name'],
                        address_type=p_recipient['address_type'], address=p_recipient['address'],
                        custom_key=p_recipient['custom_key'], custom_value=p_recipient['custom_value'],
                        split=p_recipient['split'])
                    db.session.add(recipient)
                    recipients_by_address[added_a] = recipient
                    app.logger.info(f"ValueSpec changed for feed_id={self.id}: recipient {added_a} added. name: {recipient.name} split: {recipient.split}")

                for r_a, r in recipients_by_address.items():
                    p_r = p_recipients_by_address[r_a]
                    if r.name != p_r['name']:
                        r.name = p_r['name']
                        db.session.add(r)
                        app.logger.info(f"ValueSpec changed for feed_id={self.id}: recipient {r_a} name {r.name} -> {p_r['name']}")
                    if r.address_type != p_r['address_type']:
                        r.address_type = p_r['address_type']
                        db.session.add(r)
                        app.logger.info(f"ValueSpec changed for feed_id={self.id}: recipient {r_a} address type {r.address_type} -> {p_r['address_type']}")
                    if r.split != p_r['split']:
                        r.split = p_r['split']
                        db.session.add(r)
                        app.logger.info(f"ValueSpec changed for feed_id={self.id}: recipient {r_a} split {r.split} -> {p_r['split']}")
            else: # this is new, we didn't have ValueSpec yet, so just add
                value_spec = ValueSpec(feed_id=self.id, protocol=p_value_spec['protocol'], method=p_value_spec['method'], suggested_amount=p_value_spec['suggested_amount'])
                db.session.add(value_spec)
                for p_recipient in p_value_recipients:
                    recipient = ValueRecipient(
                        value_spec=value_spec,
                        name=p_recipient['name'],
                        address_type=p_recipient['address_type'], address=p_recipient['address'],
                        custom_key=p_recipient['custom_key'], custom_value=p_recipient['custom_value'],
                        split=p_recipient['split'])
                    db.session.add(recipient)
                    value_spec.recipients.append(recipient)
                self.value_specs.append(value_spec)
                app.logger.info(f"ValueSpec added to feed_id={self.id} with suggested_amount={value_spec.suggested_amount} and {len(p_value_recipients)} recipients")

    def update_items(self, parsed_feed):
        new_item_urls = set()
        new_items = []
        updated_items = []
        for e in parsed_feed['items']:
            item_url = e['url']
            if item_url.startswith('/'):
                item_url = urljoin(self.homepage_url, item_url)
            item = Item.query.filter_by(url=item_url).first()
            if not item:
                if item_url not in new_item_urls:
                    item = Item(feed_id=self.id, url=item_url, title=e['title'],
                        content_from_feed=e['content'],
                        updated_at=e['updated_at'])
                    if e['enclosure']:
                        item.enclosure_url = e['enclosure']['href']
                        item.enclosure_type = e['enclosure']['type']
                        try:
                            item.enclosure_length = int(e['enclosure']['length'])
                        except ValueError:
                            item.enclosure_length = 0
                        self.is_podcast = True
                    new_items.append(item)
                    new_item_urls.add(item_url)
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
    feed = db.relationship(Feed, back_populates='items')
    url = db.Column(db.String(1000), unique=True, nullable=False)
    title = db.Column(db.String(1000))
    content_from_feed = db.deferred(db.Column(db.String(10000)))
    enclosure_url = db.Column(db.String(1000))
    enclosure_type = db.Column(db.String(100))
    enclosure_length = db.Column(db.Integer)
    updated_at = db.Column(db.DateTime)

    @property
    def domain_name(self):
        return urlparse(self.url).netloc

    @property
    def value_spec(self):
        # TODO: check item value specs first, which can override feed value specs
        return self.feed.value_spec

class UserItem(db.Model):
    __tablename__ = 'user_items'

    user_id = db.Column(db.Integer, db.ForeignKey(User.id), primary_key=True)
    user = db.relationship(User)
    item_id = db.Column(db.Integer, db.ForeignKey(Item.id), primary_key=True)
    item = db.relationship(Item)
    liked = db.Column(db.Boolean, nullable=False, default=False)
    read = db.Column(db.Boolean, nullable=False, default=False)
    play_position = db.Column(db.Integer, nullable=False, default=0)
    stream_value_played = db.Column(db.Integer, nullable=False, default=0)
    stream_value_paid = db.Column(db.Integer, nullable=False, default=0)

class ValueSpec(db.Model):
    __tablename__ = 'value_specs'

    SUPPORTED_PROTOCOLS = [
        ('lightning', 'keysend'),
    ]

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    protocol = db.Column(db.String(20), nullable=False)
    method = db.Column(db.String(20), nullable=False)
    suggested_amount = db.Column(db.Float)
    feed_id = db.Column(db.Integer, db.ForeignKey(Feed.id))
    item_id = db.Column(db.Integer, db.ForeignKey(Item.id), nullable=True)

    recipients = db.relationship('ValueRecipient', cascade="all,delete", backref='value_spec')

    @property
    def is_supported(self):
        return (self.protocol, self.method) in ValueSpec.SUPPORTED_PROTOCOLS

    @property
    def sats_amount(self):
        sats = round(self.suggested_amount * 100000000, 3)
        return int(sats) if sats == int(sats) else sats

    def split_amount(self, amount):
        shares = {r.id: r.split for r in self.recipients}
        total_shares = sum(shares.values())
        return {r_id: int(amount * (r_shares / total_shares)) for r_id, r_shares in shares.items()}

class ValueRecipient(db.Model):
    __tablename__ = 'value_recipients'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    value_spec_id = db.Column(db.Integer, db.ForeignKey(ValueSpec.id))
    name = db.Column(db.String(100))
    address_type = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(100), nullable=False)
    custom_key = db.Column(db.String(100))
    custom_value = db.Column(db.String(100))
    split = db.Column(db.Integer, nullable=False)

class Action(db.Model):
    __tablename__ = 'actions'

    class Actions(str, enum.Enum):
        stream = 'stream'
        boost = 'boost'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    feed_id = db.Column(db.Integer, db.ForeignKey(Feed.id))
    action = db.Column(db.Enum(Actions), nullable=False)
    amount_msat = db.Column(db.Integer, nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey(Item.id), nullable=True)
    ts = db.Column(db.Integer, nullable=True)
    message = db.Column(db.String(100), nullable=True)

    user = db.relationship(User)
    feed = db.relationship(Feed)
    item = db.relationship(Item)
    errors = db.relationship('Error', backref='action')

    __table_args__ = (
        db.ForeignKeyConstraint(
            [user_id, item_id],
            [UserItem.user_id, UserItem.item_id],
        ),
    )

    @classmethod
    def get_total_amounts(cls, user, feed_id=None):
        q = Action.query \
            .with_entities(Action.action, db.func.sum(Action.amount_msat)) \
            .group_by(Action.action) \
            .filter_by(user_id=user.id)
        if feed_id:
            q = q.filter_by(feed_id=feed_id)
        total_amounts = [(a.value, amount_msat // 1000) for a, amount_msat in q.all()]
        missing_actions = {a.value for a in Action.Actions} - {a for a, _ in total_amounts}
        for a in missing_actions:
            total_amounts.append((a, 0))
        total_amounts.sort()
        return total_amounts

class Error(db.Model):
    __tablename__ = 'errors'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    action_id = db.Column(db.Integer, db.ForeignKey(Action.id))
    address = db.Column(db.String(100), nullable=False)
    amount_msat = db.Column(db.Integer, nullable=False)
    item_ids = db.Column(db.String(1000), nullable=True)
    custom_records = db.Column(db.String(1000), nullable=False)
    message = db.Column(db.String(1000), nullable=False)
