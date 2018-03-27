import models


@models.db_session()
def update_feeds():
  for f in models.Feed.select():
    print 'Refreshing: %s' % f.url
    f.refresh()


def main():
  update_feeds()


if __name__ == '__main__':
  main()
