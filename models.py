from datetime import datetime
from time import mktime

import feedparser

from pony.orm import *

db = Database()


class Feed(db.Entity):
  id = PrimaryKey(int, auto=True)
  url = Required(str)
  feed_id = Optional(str)
  name = Optional(str)
  updated = Optional(datetime)
  last_refresh = Optional(datetime)
  items = Set('Item')

  def refresh(self):
    f = feedparser.parse(self.url)
    if self.feed_id:
      assert self.feed_id == f['feed']['id'], 'feed id changed'
    else:
      self.feed_id = f['feed']['id']
    self.name = f['feed']['title']
    feed_updated = datetime.fromtimestamp(mktime(f['feed']['updated_parsed']))
    if not self.updated or feed_updated > self.updated:
      self.updated = feed_updated
      for entry in f['entries']:
        item = Item.get(feed_id=self.id, item_id=entry['id'])
        updated = datetime.fromtimestamp(mktime(entry['updated_parsed']))
        if not item:
          item = Item(feed_id=self.id, item_id=entry['id'], url=entry['link'], title=entry['title'], summary=entry['summary'], content=entry['content'][0]['value'], updated=updated)
        elif updated > item.updated:
          item.url = entry['link']
          item.title = entry['title']
          item.content = entry['content']['value']
          if entry['summary'] != item.content:
            item.summary = entry['summary']
          else:
            item.summary = ''
          item.updated = updated
    self.last_refresh = datetime.now()


class Item(db.Entity):
  id = PrimaryKey(int, auto=True)
  feed_id = Required(Feed)
  item_id = Required(str)
  url = Required(str)
  title = Required(str)
  summary = Optional(str)
  content = Required(str)
  updated = Required(datetime)

db.bind(provider='postgres', user='postgres', password='', host='127.0.0.1', database='mureader')
db.generate_mapping()
