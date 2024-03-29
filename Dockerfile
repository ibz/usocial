FROM python:3.8-buster

ARG version

RUN apt-get update && apt-get install -y cron sudo

COPY requirements.txt /
ENV PYTHONPATH "${PYTHONPATH}:/"
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r /requirements.txt

COPY ./usocial /usocial
COPY ./migrations /usocial/migrations
COPY config.py start.sh /
RUN chmod +x /start.sh

RUN echo "VERSION = '${version}'" >> /config.py \
 && echo "BUILD = '"`date +%Y%m%d`"'" >> /config.py

ENV INSTANCE_PATH=/instance
VOLUME ["/instance"]

RUN groupadd -r usocial --gid=1000 && useradd -r -g usocial --uid=1000 --create-home --shell /bin/bash usocial

RUN touch /var/log/cron.log \
 && chown usocial:usocial /var/log/cron.log \
 && echo 'usocial ALL=NOPASSWD: /usr/sbin/cron' >> /etc/sudoers

USER usocial

WORKDIR /usocial

EXPOSE 5000

CMD [ "/start.sh" ]
