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

PODCAST_NAMESPACE_URI = 'https://github.com/Podcastindex-org/podcast-namespace/blob/main/docs/1.0.md'
HEADERS = {'User-Agent': config.USER_AGENT}

PARSER_FEEDPARSER = 1
PARSER_ELEMENTTREE = 2

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
    enclosure = None
    enclosure_el = item.find('enclosure')
    if enclosure_el:
        enclosure = {'href': enclosure_el.get('url'), 'type': enclosure_el.get('type'), 'length': enclosure_el.get('length')}
    return {'title': item.find('title').text,
            'url': item.find('link').text,
            'content': description_el.text if description_el else None,
            'enclosure': enclosure,
            'updated_at': parse_datetime(item.find('pubDate').text)}

def parse_feed_item(item):
    enclosure_links = [l for l in item['links'] if l['rel'] == 'enclosure']
    return {'title': item['title'],
            'url': item['link'],
            'content': item['content'][0]['value'] if item.get('content') else item.get('summary'),
            'enclosure': enclosure_links[0] if enclosure_links else None,
            'updated_at': parse_feed_datetime(item.get('updated_parsed'))}

def parse_valuespec(root):
    value_spec = None
    value_recipients = []

    value_el = root.find('channel/{%s}value' % PODCAST_NAMESPACE_URI)
    if value_el:
        value_spec = {}
        value_spec['protocol'] = value_el.attrib['type']
        value_spec['method'] = value_el.attrib['method']
        value_spec['suggested_amount'] = float(value_el.attrib.get('suggested', 0))
        for value_recipient_el in value_el.findall('{%s}valueRecipient' % PODCAST_NAMESPACE_URI):
            value_recipient = {}
            value_recipient['name'] = value_recipient_el.attrib.get('name')
            value_recipient['address_type'] = value_recipient_el.attrib['type']
            value_recipient['address'] = value_recipient_el.attrib['address']
            value_recipient['split'] = int(value_recipient_el.attrib['split'])
            value_recipients.append(value_recipient)

    return value_spec, value_recipients

def parse_feed(url):
    app.logger.debug(f'Parsing feed {url}...')

    try:
        content = requests.get(url, headers=HEADERS, timeout=10).text
    except Exception as e:
        app.log_exception(e)
        return
    if len(content) < 10:
        app.logger.warn("Content too short.")
        return

    parsed_feed = None

    try:
        f = feedparser.parse(content)
        app.logger.debug(f'Parsed feed {url} using PARSER_FEEDPARSER')
    except RuntimeError:
        f = None

    if f and f['feed'] and f['feed'].get('title') and f['feed'].get('link'):
        value_spec = None
        value_recipients = []
        # HACK: feedparser doesn't yet parse the "podcast" namespace properly
        # (see https://github.com/kurtmckee/feedparser/issues/301)
        # so we should parse this part separately
        if 'podcast' in f['namespaces']:
            root = None
            try:
                root = fromstring(content)
            except ParseError as e:
                app.log_exception(e)
            if root:
                value_spec, value_recipients = parse_valuespec(root)
                app.logger.debug(f'Parsed ValueSpec: {value_spec is not None} {len(value_recipients)}')
        return {'title': f['feed']['title'],
                'updated_at': parse_feed_datetime(f['feed'].get('updated_parsed')),
                'items': [parse_feed_item(e) for e in f['entries'] if e and e.get('link') and e.get('title')],
                'value_spec': value_spec, 'value_recipients': value_recipients,
                'parser': PARSER_FEEDPARSER}

    try:
        root = fromstring(content)
        app.logger.debug(f'Parsed feed {url} using PARSER_ELEMENTTREE')
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

    value_spec, value_recipients = parse_valuespec(root)

    return {'title': title_el.text,
            'updated_at': parse_datetime(date_el.text) if date_el else None,
            'items': [parse_rss_item(item) for item in root.findall('channel/item')],
            'value_spec': value_spec, 'value_recipients': value_recipients,
            'parser': PARSER_ELEMENTTREE}

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
