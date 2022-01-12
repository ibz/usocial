FROM python:3.8-buster

COPY ./musocial /musocial
COPY requirements.txt /
COPY config.py /
COPY start.sh /
RUN chmod +x /start.sh

ENV PYTHONPATH "${PYTHONPATH}:/"

RUN pip install --upgrade pip && pip install --no-cache-dir -r /requirements.txt

ENV INSTANCE_PATH=/instance
VOLUME ["/instance"]

RUN groupadd -r musocial --gid=1000 && useradd -r -g musocial --uid=1000 --create-home --shell /bin/bash musocial

USER musocial

WORKDIR /musocial

EXPOSE 5000

CMD [ "/start.sh" ]
