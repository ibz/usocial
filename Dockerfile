FROM python:3.8-buster

COPY ./usocial /usocial
COPY requirements.txt /
COPY config.py /
COPY start.sh /
RUN chmod +x /start.sh

ENV PYTHONPATH "${PYTHONPATH}:/"

RUN pip install --upgrade pip && pip install --no-cache-dir -r /requirements.txt

ENV INSTANCE_PATH=/instance
VOLUME ["/instance"]

RUN groupadd -r usocial --gid=1000 && useradd -r -g usocial --uid=1000 --create-home --shell /bin/bash usocial

USER usocial

WORKDIR /usocial

EXPOSE 5000

CMD [ "/start.sh" ]
