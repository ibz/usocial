from datetime import datetime
import sys

from musocial import models
from musocial.main import db
from musocial.parser import parse_feed

def fetch_feed(feed):
    print("Fetching %s" % feed.url)
    parsed_feed = parse_feed(feed.url)
    feed.update(parsed_feed)
    new_entries, updated_entries = feed.update_entries(parsed_feed)
    for entry in new_entries + updated_entries:
        db.session.add(entry)
    db.session.add(feed)
    if new_entries:
        for user in models.User.query.join(models.Subscription).join(models.Feed).filter(models.Subscription.feed == feed):
            print("Adding %s new entries to %s" % (len(new_entries), user.email))
            for entry in new_entries:
                db.session.add(models.UserEntry(user=user, entry=entry))
    db.session.commit()

def main():
    feed_id = None
    url_contains = None
    if len(sys.argv) > 1:
        try:
            feed_id = int(sys.argv[1])
        except ValueError:
            url_contains = sys.argv[1]

    feeds = models.Feed.query
    if feed_id:
        feeds = feeds.filter_by(id=feed_id)
    if url_contains:
        feeds = feeds.filter(models.Feed.url.contains(url_contains))

    for feed in feeds:
        fetch_feed(feed)

if __name__ == '__main__':
    main()
