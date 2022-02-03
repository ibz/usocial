FROM python:3.8-buster

ARG version

RUN apt-get update && apt-get install -y cron sudo

COPY ./usocial /usocial
COPY requirements.txt /

COPY config.py /
RUN echo "VERSION = '${version}'" >> /config.py
RUN echo "BUILD = '"`date +%Y%m%d`"'" >> /config.py

COPY start.sh /
RUN chmod +x /start.sh

ENV PYTHONPATH "${PYTHONPATH}:/"

RUN pip install --upgrade pip && pip install --no-cache-dir -r /requirements.txt

ENV INSTANCE_PATH=/instance
VOLUME ["/instance"]

RUN groupadd -r usocial --gid=1000 && useradd -r -g usocial --uid=1000 --create-home --shell /bin/bash usocial

RUN touch /var/log/cron.log && chown usocial:usocial /var/log/cron.log
RUN echo 'usocial ALL=NOPASSWD: /usr/sbin/cron' >> /etc/sudoers

USER usocial

WORKDIR /usocial

EXPOSE 5000

CMD [ "/start.sh" ]
