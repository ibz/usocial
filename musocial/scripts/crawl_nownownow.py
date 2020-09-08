from bs4 import BeautifulSoup
from datetime import datetime
import requests
import sys
from urllib.parse import urlparse

from musocial import models
from musocial.main import db
from musocial.parser import parse_feed, extract_feed_links

import config

HEADERS = {'User-Agent': config.USER_AGENT}

def get_links():
    r = requests.get('https://nownownow.com/', headers=HEADERS)
    soup = BeautifulSoup(r.text, 'html.parser')
    links = []
    for li in soup.find_all('li'):
        link = None
        url = li.find('div', attrs={'class': 'url'})
        if url:
            link = url.find('a')
        else:
            name = li.find('div', attrs={'class': 'name'})
            if name:
                link = name.find('a')
        links.append(link.attrs['href'])
    return links

def parse_now_page(url, content):
    alt_links = extract_feed_links(url, content)

    print("Found %s alt links: %s" % (len(alt_links), ', '.join([l[0] for l in alt_links])))

    for alt_url, _ in alt_links:
        feed = models.Feed.query.filter_by(url=alt_url).first()
        if feed:
            print("SKIP")
            return
        feed = models.Feed(url=alt_url)
        parsed_feed = parse_feed(alt_url)
        if not parsed_feed:
            print("FEED FAIL")
            continue
        if not parsed_feed['entries']:
            print("EMPTY FEED")
            continue
        feed.update(parsed_feed)
        db.session.add(feed)
        db.session.commit()
        new_entries, updated_entries = feed.update_entries(parsed_feed)
        for entry in new_entries + updated_entries:
            db.session.add(entry)
        db.session.commit()
        return # NOTE: we only save the 1st valid feed

def main():
    start_at = 0
    if len(sys.argv) > 1:
        start_at = int(sys.argv[1])

    links = get_links()
    print(f"Found {len(links)} now links")

    for i, link in enumerate(links):
        if i < start_at:
            print("SKIP")
            continue

        print(f"Processing link {i}: {link}")
        now_page = None
        try:
            now_page = requests.get(link, headers=HEADERS)
            if now_page.status_code != 200:
                print("FAIL")
                continue
        except requests.exceptions.RequestException as e:
            print("ERR")
            continue

        parse_now_page(link, now_page.text)

if __name__ == '__main__':
    main()
