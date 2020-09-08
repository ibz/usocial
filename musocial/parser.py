from bs4 import BeautifulSoup
from datetime import datetime
import dateutil.parser
import feedparser
from http.client import IncompleteRead
from time import mktime
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from xml.etree.ElementTree import fromstring, ElementTree, ParseError

import config

HEADERS = {'User-Agent': config.USER_AGENT}

def parse_feed_datetime(dt):
    if not dt:
        return None
    try:
        return datetime.fromtimestamp(mktime(dt))
    except OverflowError:
        return None

def parse_datetime(dt):
    return dateutil.parser.parse(dt)

def parse_feed(url):
    try:
        response = urlopen(Request(url, headers=HEADERS))
    except (HTTPError, URLError):
        return
    try:
        content = response.read()
    except IncompleteRead:
        return
    if len(content) < 10:
        return

    try:
        f = feedparser.parse(content)
    except RuntimeError:
        f = None

    if f and f['feed'] and f['feed'].get('title'):
        return {'title': f['feed']['title'],
                'homepage_url': f['feed'].get('link'),
                'updated_at': parse_feed_datetime(f['feed'].get('updated_parsed')),
                'entries': [{'title': e['title'], 'url': e['link'], 'updated_at': parse_feed_datetime(e.get('updated_parsed'))}
                              for e in f['entries'] if e and e.get('link') and e.get('title')]}

    try:
        root = fromstring(content)
    except ParseError:
        return

    title_el = root.find('channel/title')
    if not title_el:
        return
    date_el = root.find('channel/lastBuildDate')
    return {'title': title_el.text,
            'updated_at': parse_datetime(date_el.text) if date_el else None,
            'entries': [{'title': item.find('title').text, 'url': item.find('link').text,
                         'updated_at': parse_datetime(item.find('pubDate').text)}
                         for item in root.findall('channel/item')]}

def extract_feed_links(url, content):
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    soup = BeautifulSoup(content, 'html.parser')
    alt_links = []
    for link in soup.find_all('link', rel='alternate'):
        if link.attrs.get('type') in ['application/atom+xml', 'application/rss+xml']:
            href = (link.attrs['href'] or "").strip()
            if not href:
                continue
            title = link.attrs.get('title')
            if href.startswith('/'):
                href = f"{base_url}{href}"
            elif href.startswith('../') or '/' not in href:
                href = f"{base_url}/{href}"
            if "://" not in href:
                href = f"http://{href}"

            alt_links.append((href, title))

    presumably_comment_feed_urls = {l[0] for l in alt_links
        if l[1] and any(c in l[1].lower() for c in ["comments", "commentaires", "kommentar", "comentarios"])
        or "/comments/" in l[0]}

    alt_links_without_presumably_comment_feeds = [l for l in alt_links if l[0] not in presumably_comment_feed_urls]

    return alt_links_without_presumably_comment_feeds or alt_links
