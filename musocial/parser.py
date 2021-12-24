from bs4 import BeautifulSoup
from datetime import datetime
import dateutil.parser
import feedparser
from http.client import IncompleteRead
import requests
from socket import timeout
from time import mktime
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from xml.etree.ElementTree import fromstring, ElementTree, ParseError

import config

from musocial.main import app

HEADERS = {'User-Agent': config.USER_AGENT}

def strip_protocol(url):
    return url.replace('http://', '').replace('https://', '')

def parse_feed_datetime(dt):
    if not dt:
        return None
    try:
        return datetime.fromtimestamp(mktime(dt))
    except OverflowError:
        return None

def parse_datetime(dt):
    return dateutil.parser.parse(dt)

def parse_rss_item(item):
    description_el = item.find('description')
    return {'title': item.find('title').text,
            'url': item.find('link').text,
            'content': description_el.text if description_el else None,
            'updated_at': parse_datetime(item.find('pubDate').text)}

def parse_feed_item(item):
    return {'title': item['title'],
            'url': item['link'],
            'content': item['content'][0]['value'] if item.get('content') else item.get('summary'),
            'updated_at': parse_feed_datetime(item.get('updated_parsed'))}

def parse_feed(url):
    try:
        content = requests.get(url, headers=HEADERS, timeout=10).text
    except Exception as e:
        app.log_exception(e)
        return
    if len(content) < 10:
        app.logger.warn("Content too short.")
        return

    try:
        f = feedparser.parse(content)
    except RuntimeError:
        f = None

    if f and f['feed'] and f['feed'].get('title') and f['feed'].get('link'):
        return {'title': f['feed']['title'],
                'updated_at': parse_feed_datetime(f['feed'].get('updated_parsed')),
                'items': [parse_feed_item(e) for e in f['entries'] if e and e.get('link') and e.get('title')]}

    try:
        root = fromstring(content)
    except ParseError as e:
        app.log_exception(e)
        return

    title_el = root.find('channel/title')
    if not title_el:
        app.logger.warn("No channel/title element found.")
        return
    link_el = root.find('channel/link')
    if not link_el:
        app.logger.warn("No channel/link element found.")
        return
    date_el = root.find('channel/lastBuildDate')
    return {'title': title_el.text,
            'updated_at': parse_datetime(date_el.text) if date_el else None,
            'items': [parse_rss_item(item) for item in root.findall('channel/item')]}

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
