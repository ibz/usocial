from datetime import datetime
import sys

from usocial import models
from usocial.main import db
from usocial.parser import parse_feed

def fetch_feed(feed):
    print("Fetching %s" % feed.url)
    parsed_feed = parse_feed(feed.url)
    feed.update(parsed_feed)
    new_items_count = 0
    users_count = 0
    if parsed_feed:
        new_items, updated_items = feed.update_items(parsed_feed)
        for item in new_items + updated_items:
            db.session.add(item)
        if new_items:
            new_items_count = len(new_items)
            for user in models.User.query.join(models.Group).join(models.FeedGroup).join(models.Feed).filter(models.FeedGroup.feed == feed):
                users_count += 1
                print("Adding %s new items to %s" % (new_items_count, user.username))
                for item in new_items:
                    db.session.add(models.UserItem(user=user, item=item))
    db.session.add(feed)
    db.session.commit()
    return new_items_count, users_count

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
        new_items, users = fetch_feed(feed)
        print(f"{feed.url} - New items: {new_items} - Users: {users}")
    print("Fetch Feeds DONE")

if __name__ == '__main__':
    main()
