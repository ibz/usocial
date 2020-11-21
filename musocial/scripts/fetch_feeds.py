from datetime import datetime
import sys

from flask_mail import Message

from musocial import models
from musocial.main import app, db, mail
from musocial.parser import parse_feed

def fetch_feed(feed):
    print("Fetching %s" % feed.url)
    parsed_feed = parse_feed(feed.url)
    feed.update(parsed_feed)
    new_entries_count = 0
    users_count = 0
    if parsed_feed:
        new_entries, updated_entries = feed.update_entries(parsed_feed)
        for entry in new_entries + updated_entries:
            db.session.add(entry)
        if new_entries:
            new_entries_count = len(new_entries)
            for user in models.User.query.join(models.Subscription).join(models.Feed).filter(models.Subscription.feed == feed):
                users_count += 1
                print("Adding %s new entries to %s" % (new_entries_count, user.email))
                for entry in new_entries:
                    db.session.add(models.UserEntry(user=user, entry=entry))
    db.session.add(feed)
    db.session.commit()
    return new_entries_count, users_count

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

    stats = []
    for feed in feeds:
        new_entries, users = fetch_feed(feed)
        stats.append((feed.url, new_entries, users))

    stats_body = ""
    for url, new_entries, users in stats:
        stats_body += f"{url} - New Entries: {new_entries} - Users: {users}\n"
    m = Message("Fetch Feeds DONE", recipients=[app.config['LOG_EMAIL']], body=stats_body, sender=app.config['MAIL_DEFAULT_SENDER'])

    with app.app_context():
        mail.send(m)

if __name__ == '__main__':
    main()
