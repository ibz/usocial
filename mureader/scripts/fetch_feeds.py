from datetime import datetime
import dateutil.parser
import feedparser
from time import mktime
from urllib.request import urlopen
import xml.etree.ElementTree as ET

from mureader import db
from mureader import models

def parse_feed(url):
    f = feedparser.parse(url)
    if f['feed']:
        return {'title': f['feed']['title'],
                'updated_at': datetime.fromtimestamp(mktime(f['feed']['updated_parsed'])),
                'entries': [{'title': e['title'],
                             'url': e['link'],
                             'updated_at': datetime.fromtimestamp(mktime(e['updated_parsed']))}
                            for e in f['entries']]}
    else:
        root = ET.ElementTree(file=urlopen(url))
        title = root.find('channel/title').text
        updated_at = dateutil.parser.parse(root.find('channel/lastBuildDate').text)
        entries = []
        for item in root.findall('channel/item'):
            entry = {'title': item.find('title').text,
                     'url': item.find('link').text,
                     'updated_at': dateutil.parser.parse(item.find('pubDate').text)}
            entries.append(entry)
        return {'title': title,
                'updated_at': updated_at,
                'entries': entries}

def fetch_feed(feed):
    print("Fetching %s" % feed.url)
    f = parse_feed(feed.url)
    feed.title = f['title']
    feed.updated_at = f['updated_at']
    feed.fetched_at = datetime.now()
    new_entries = []
    for e in f['entries']:
        entry = models.Entry.query.filter_by(url=e['url']).first()
        if not entry:
            entry = models.Entry(feed_id=feed.id, url=e['url'])
            new_entries.append(entry)
        entry.title = e['title']
        entry.updated_at = e['updated_at']
        db.session.add(entry)
    db.session.add(feed)
    if new_entries:
        for user in models.User.query.join(models.Subscription).join(models.Feed).filter(models.Subscription.feed == feed):
            print("Adding %s new entries to %s" % (len(new_entries), user.email))
            for entry in new_entries:
                db.session.add(models.UserEntry(user=user, entry=entry))
    db.session.commit()

def main():
    for feed in models.Feed.query.all():
        fetch_feed(feed)

if __name__ == '__main__':
    main()
