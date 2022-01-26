from datetime import datetime
import hashlib
import os
import os.path
from urllib.parse import urlparse

from babel.dates import format_timedelta

from usocial.main import app, db, bcrypt
from usocial.parser import strip_protocol


class User(db.Model):
    __tablename__ = 'users'

    DEFAULT_USERNAME = 'me'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255))
    fever_api_key = db.Column(db.String(255))
    registered_on = db.Column(db.DateTime, nullable=False)
    public = db.Column(db.Boolean, nullable=False, default=False)

    groups = db.relationship('Group', backref='user')

    def __init__(self, username):
        self.username = username
        self.fever_api_key = hashlib.md5(("%s:" % username).encode('utf-8')).hexdigest()
        self.registered_on = datetime.now()

    def set_password(self, password):
        if password:
            self.password = bcrypt.generate_password_hash(password, app.config.get('BCRYPT_LOG_ROUNDS')).decode()
        else:
            self.password = None
        self.fever_api_key = hashlib.md5(("%s:%s" % (username, password or "")).encode('utf-8')).hexdigest()

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
    title = db.Column(db.String(1000))
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
        return value_specs[0] if value_specs else None

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
        self.parser = parsed_feed['parser']

        self.update_value_spec(parsed_feed['value_spec'], parsed_feed['value_recipients'])

    def update_value_spec(self, p_value_spec, p_value_recipients):
        value_spec = self.value_spec

        if not p_value_spec:
            if value_spec:
                db.session.delete(value_spec)
        else: # got a value spec from the feed
            if value_spec:
                value_spec_changed = False
                if value_spec.protocol != p_value_spec['protocol'] or value_spec.method != p_value_spec['method'] or value_spec.suggested_amount != p_value_spec['suggested_amount']:
                    value_spec_changed = True
                    app.logger.info(f"ValueSpec changed for feed_id={self.id}: protocol {value_spec.protocol} -> {p_value_spec['protocol']}, method {value_spec.method} -> {p_value_spec['method']}, suggested_amount {value_spec.suggested_amount} -> {p_value_spec['suggested_amount']}")
                if len(value_spec.recipients) != len(p_value_recipients):
                    value_spec_changed = True
                    app.logger.info(f"ValueSpec changed for feed_id={self.id}: recipients {len(value_spec.recipients)} -> {len(p_value_recipients)}")
                recipients_by_address = {r.address: r for r in value_spec.recipients}
                p_recipients_by_address = {p_r['address']: p_r for p_r in p_value_recipients}
                if set(recipients_by_address.keys()) != set(p_recipients_by_address.keys()):
                    value_spec_changed = True
                    app.logger.info(f"ValueSpec changed for feed_id={self.id}: recipients {sorted(recipients_by_address.keys())} -> {sorted(p_recipients_by_address.keys())}")
                if not value_spec_changed:
                    for r_a, r in recipients_by_address.items():
                        if r.name != p_recipients_by_address[r_a]['name']:
                            value_spec_changed = True
                            app.logger.info(f"ValueSpec changed for feed_id={self.id}: recipient {r_a} name {r.name} -> {p_recipients_by_address[r_a]['name']}")
                        if r.address_type != p_recipients_by_address[r_a]['address_type']:
                            value_spec_changed = True
                            app.logger.info(f"ValueSpec changed for feed_id={self.id}: recipient {r_a} address type {r.address_type} -> {p_recipients_by_address[r_a]['address_type']}")
                        if r.split != p_recipients_by_address[r_a]['split']:
                            value_spec_changed = True
                            app.logger.info(f"ValueSpec changed for feed_id={self.id}: recipient {r_a} split {r.split} -> {p_recipients_by_address[r_a]['split']}")
                if not value_spec_changed:
                    return # nothing to do

                db.session.delete(value_spec) # delete the outdated value spec

            value_spec = ValueSpec(protocol=p_value_spec['protocol'], method=p_value_spec['method'], suggested_amount=p_value_spec['suggested_amount'])
            for p_recipient in p_value_recipients:
                recipient = ValueRecipient(name=p_recipient['name'], address_type=p_recipient['address_type'], address=p_recipient['address'], split=p_recipient['split'])
                value_spec.recipients.append(recipient)
            self.value_specs.append(value_spec)

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
                    if e['enclosure']:
                        item.enclosure_url = e['enclosure']['href']
                        item.enclosure_type = e['enclosure']['type']
                        item.enclosure_length = int(e['enclosure']['length'])
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
    def relative_date(self):
        return format_timedelta(self.updated_at - datetime.now(), add_direction=True)

class UserItem(db.Model):
    __tablename__ = 'user_items'

    user_id = db.Column(db.Integer, db.ForeignKey(User.id), primary_key=True)
    user = db.relationship(User)
    item_id = db.Column(db.Integer, db.ForeignKey(Item.id), primary_key=True)
    item = db.relationship(Item)
    liked = db.Column(db.Boolean, nullable=False, default=False)
    read = db.Column(db.Boolean, nullable=False, default=False)
    play_position = db.Column(db.Integer, nullable=False, default=0)
    played_value_count = db.Column(db.Integer, nullable=False, default=0)
    paid_value_count = db.Column(db.Integer, nullable=False, default=0)

    @property
    def value_spec(self):
        # TODO: check item value specs first, which can override feed value specs
        return self.item.feed.value_spec

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
        return {r_id: amount * (r_shares / total_shares) for r_id, r_shares in shares.items()}

class ValueRecipient(db.Model):
    __tablename__ = 'value_recipients'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    value_spec_id = db.Column(db.Integer, db.ForeignKey(ValueSpec.id))
    name = db.Column(db.String(100))
    address_type = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(100), nullable=False)
    split = db.Column(db.Integer, nullable=False)

class ValuePayment(db.Model):
    __tablename__ = 'value_payments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey(ValueRecipient.id))
    date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    amount = db.Column(db.Integer, nullable=False)

def create_all():
    db.create_all()

    # create the default user here
    db.session.add(User(User.DEFAULT_USERNAME))
    db.session.commit()