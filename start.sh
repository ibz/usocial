#! /usr/bin/env bash

set -e

setup_web () {
    if [ ! -f /instance/config.py ]; then
        echo "SECRET_KEY = '"`python -c 'import os;print(os.urandom(12).hex())'`"'" > /instance/config.py
    fi
    if [ ! -f /instance/usocial.db ]; then
        FLASK_APP=main DEFAULT_USER_PASSWORD=${APP_PASSWORD} flask create-db
    fi

    FLASK_APP=main flask db upgrade
}

do_job_web () {
    setup_web
    python ./main.py
}

setup_fetch_feeds () {
    if ! crontab -l ; then
        echo "*/10 * * * * cd /usocial && FLASK_APP=main /usr/local/bin/flask fetch-feeds >> /var/log/cron.log 2>&1" > /home/usocial/usocial-cron
        chmod 0644 /home/usocial/usocial-cron
        crontab /home/usocial/usocial-cron
    fi
}

do_job_fetch_feeds () {
    setup_fetch_feeds
    sudo cron && tail -f /var/log/cron.log
}

case "$USOCIAL_JOB" in
  "WEB") do_job_web ;;
  "FETCH_FEEDS") do_job_fetch_feeds ;;
esac
